import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy
import time
import yaml
from collections import deque
from rosidl_runtime_py.utilities import get_message

from core.models import TopicInfo
from config.settings import ValidationStatus

class VerifierNode(Node):
    def __init__(self):
        super().__init__('icd_verifier_node')
        self.subscriptions_dict = {}
        self.topic_states = {}
        self.hz_margin = 0.2   # Default 20%
        self.hz_window = 5.0   # Default measurement window: 5 seconds

    def set_hz_margin(self, margin_fraction):
        """Updates the tolerance margin for HZ validation (e.g., 0.1 for 10%)"""
        self.hz_margin = margin_fraction
        self.get_logger().info(f"Hz Margin updated to {self.hz_margin * 100}%")

    def set_hz_window(self, window_sec: float):
        """Updates the rolling measurement window size in seconds."""
        self.hz_window = max(1.0, window_sec)
        self.get_logger().info(f"Hz Window updated to {self.hz_window}s")

    def update_topics_to_verify(self, topics: list[TopicInfo]):
        # Remove old subscriptions
        for topic_name, sub in self.subscriptions_dict.items():
            self.destroy_subscription(sub)
        self.subscriptions_dict.clear()
        self.topic_states.clear()

        # Subscribe to new ones
        for topic in topics:
            self.topic_states[topic.name] = {
                "count": 0,          # total received (non-periodic 판단용)
                "timestamps": deque(),  # rolling window timestamps
                "actual_hz": 0.0,
                "raw": "수신 대기중...",
                "missing_dst": [],
                "header_src": None,
                "header_dst": [],
                "target": topic
            }

            try:
                # Convert "std_msgs/String" to "std_msgs/msg/String" if needed
                msg_type_str = topic.topic_type
                if "/msg/" not in msg_type_str:
                    parts = msg_type_str.split('/')
                    if len(parts) == 2:
                        msg_type_str = f"{parts[0]}/msg/{parts[1]}"

                msg_class = get_message(msg_type_str)

                # Use BestEffort to avoid blocking reception when publisher is BestEffort
                # This way we can always receive messages regardless of publisher QoS
                qos_profile = QoSProfile(
                    reliability=QoSReliabilityPolicy.BEST_EFFORT,
                    depth=10
                )

                def make_callback(t_name):
                    def cb(msg):
                        self.message_callback(t_name, msg)
                    return cb

                sub = self.create_subscription(
                    msg_class,
                    topic.name,
                    make_callback(topic.name),
                    qos_profile
                )
                self.subscriptions_dict[topic.name] = sub
                self.get_logger().info(f"Subscribed to {topic.name} ({msg_type_str})")
            except Exception as e:
                self.get_logger().error(f"Failed to subscribe to {topic.name}: {e}")
                self.topic_states[topic.name]["raw"] = f"구독 실패: {e}"

    def message_callback(self, topic_name, msg):
        state = self.topic_states[topic_name]

        now = time.time()
        state["count"] += 1

        # Rolling window: 타임스탬프 추가 후 윈도우 밖의 오래된 것 제거
        ts: deque = state["timestamps"]
        ts.append(now)
        while ts and (now - ts[0]) > self.hz_window:
            ts.popleft()

        # 윈도우 안에 샘플이 2개 이상이면 Hz 계산
        # Hz = (샘플 수 - 1) / (최신 - 최초)  ← 간격(interval) 기반으로 정확
        if len(ts) >= 2:
            window_elapsed = ts[-1] - ts[0]
            if window_elapsed > 0:
                state["actual_hz"] = (len(ts) - 1) / window_elapsed

        # Parse message content for raw view
        try:
            raw_str = yaml.dump(self.msg_to_dict(msg), allow_unicode=True)
            state["raw"] = raw_str
        except Exception as e:
            state["raw"] = f"Raw data parsing error: {e}"

        # Check for communication_header (custom messages with robot IDs)
        # Supports: msg.header (icd_custom_msgs/CommunicationHeader) or msg.communication_header
        hdr = getattr(msg, 'header', None)
        if hdr is None:
            hdr = getattr(msg, 'communication_header', None)

        if hdr is not None and hasattr(hdr, 'src') and hasattr(hdr, 'dst'):
            state["header_src"] = str(hdr.src)
            state["header_dst"] = [str(d) for d in hdr.dst]

    def msg_to_dict(self, msg, _depth: int = 0):
        """Recursively convert ROS message to dictionary (max depth 20)."""
        if _depth > 20:
            return "<max depth reached>"

        if not hasattr(msg, 'get_fields_and_field_types'):
            if isinstance(msg, bytes):
                return "<bytes>"
            if isinstance(msg, (list, tuple)):
                if len(msg) > 100:
                    return f"<array of length {len(msg)}>"
                return [self.msg_to_dict(m, _depth + 1) for m in msg]
            # numpy arrays and other iterables
            if hasattr(msg, '__iter__') and not isinstance(msg, str):
                try:
                    items = list(msg)
                    if len(items) > 100:
                        return f"<array of length {len(items)}>"
                    return [self.msg_to_dict(m, _depth + 1) for m in items]
                except Exception:
                    pass
            return msg

        d = {}
        for field_name, _ in msg.get_fields_and_field_types().items():
            try:
                val = getattr(msg, field_name)
                d[field_name] = self.msg_to_dict(val, _depth + 1)
            except Exception as e:
                d[field_name] = f"<error: {e}>"
        return d

    def _get_qos_str(self, reliability) -> str:
        if reliability == QoSReliabilityPolicy.RELIABLE:
            return "Reliable"
        elif reliability == QoSReliabilityPolicy.BEST_EFFORT:
            return "BestEffort"
        return "Unknown"

    def get_validation_results(self):
        """Returns the updated states for the GUI thread."""
        results = {}
        my_node_name = self.get_name()  # 'icd_verifier_node'

        for t_name, state in self.topic_states.items():
            target = state["target"]
            actual_hz = state["actual_hz"]
            count = state["count"]

            # Get actual publishers and subscribers from ROS2 graph
            pubs = self.get_publishers_info_by_topic(t_name)
            subs = self.get_subscriptions_info_by_topic(t_name)

            # Filter out our own verifier subscription from the subscriber list
            external_subs = [s for s in subs if s.node_name != my_node_name]

            # Connected node names
            pub_nodes = list(set(p.node_name for p in pubs))
            sub_nodes = list(set(s.node_name for s in external_subs))

            # Publisher QoS (first publisher's QoS)
            pub_qos = "-"
            if pubs:
                pub_qos = self._get_qos_str(pubs[0].qos_profile.reliability)

            # Subscriber QoS (first external subscriber's QoS)
            sub_qos = "-"
            if external_subs:
                sub_qos = self._get_qos_str(external_subs[0].qos_profile.reliability)

            # --- Validation Logic ---
            status = ValidationStatus.PENDING

            if len(pubs) == 0 and count == 0:
                # No publisher and no messages received at all
                status = ValidationStatus.NOT_RECEIVED
            else:
                # 1. Check publisher QoS vs target QoS
                pub_qos_ok = True
                if pub_qos not in ("-", "Unknown"):
                    if pub_qos.lower() != target.target_qos.lower():
                        pub_qos_ok = False

                # 2. Check pub/sub QoS compatibility:
                #    BestEffort publisher + Reliable subscriber = INCOMPATIBLE in ROS2
                pub_sub_compatible = True
                if pub_qos == "BestEffort" and sub_qos == "Reliable":
                    pub_sub_compatible = False

                qos_ok = pub_qos_ok and pub_sub_compatible

                if not qos_ok:
                    status = ValidationStatus.QOS_MISMATCH
                elif target.target_hz == 0:
                    # Non-periodic topic: NORMAL as soon as at least one message received
                    if count > 0:
                        status = ValidationStatus.NORMAL
                    # else: remain PENDING until first message
                else:
                    # Periodic topic: check Hz
                    if actual_hz > 0:
                        hz_diff = abs(actual_hz - target.target_hz)
                        if (hz_diff / target.target_hz) > self.hz_margin:
                            status = ValidationStatus.HZ_MISMATCH
                        else:
                            status = ValidationStatus.NORMAL
                    # else: remain PENDING until enough messages to calculate Hz

            results[t_name] = {
                "actual_hz": actual_hz,
                "actual_qos": pub_qos,          # backward compat
                "actual_pub_qos": pub_qos,
                "actual_sub_qos": sub_qos,
                "status": status,
                "received": count > 0,
                "missing_dst": [],              # src/dst validation removed
                "connected_publishers": pub_nodes,
                "connected_subscribers": sub_nodes,
                "header_src": state["header_src"],
                "header_dst": state["header_dst"],
                "raw": state["raw"]
            }
        return results
