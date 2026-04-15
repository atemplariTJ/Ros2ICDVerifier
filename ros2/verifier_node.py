import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSDurabilityPolicy, QoSHistoryPolicy
from rclpy.qos_event import SubscriptionEventCallbacks
import time
import json
from rosidl_runtime_py.utilities import get_message

from core.models import TopicInfo
from config.settings import ValidationStatus

class VerifierNode(Node):
    def __init__(self):
        super().__init__('icd_verifier_node')
        self.subscriptions_dict = {}
        self.topic_states = {} # {topic_name: {"count": 0, "first_time": 0, "last_time": 0, "actual_hz": 0, "raw": "", "missing_dst": []}}
        self.hz_margin = 0.2 # Default 20%
        
    def set_hz_margin(self, margin_fraction):
        """Updates the tolerance margin for HZ validation (e.g., 0.1 for 10%)"""
        self.hz_margin = margin_fraction
        self.get_logger().info(f"Hz Margin updated to {self.hz_margin * 100}%")

    def update_topics_to_verify(self, topics: list[TopicInfo]):
        # Remove old subscriptions
        for topic_name, sub in self.subscriptions_dict.items():
            self.destroy_subscription(sub)
        self.subscriptions_dict.clear()
        self.topic_states.clear()
        
        # Subscribe to new ones
        for topic in topics:
            self.topic_states[topic.name] = {
                "count": 0, "first_time": None, "last_time": None, 
                "actual_hz": 0.0, "raw": "수신 대기중...", "missing_dst": [],
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
                
                # Determine QoS
                qos_profile = 10 # Default history depth
                if topic.target_qos.lower() == "besteffort":
                    qos_profile = QoSProfile(
                        reliability=QoSReliabilityPolicy.BEST_EFFORT,
                        depth=10
                    )
                elif topic.target_qos.lower() == "reliable":
                    qos_profile = QoSProfile(
                        reliability=QoSReliabilityPolicy.RELIABLE,
                        depth=10
                    )
                
                # We need a closure/lambda that captures the topic name
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
        target = state["target"]
        
        current_time = time.time()
        
        if state["first_time"] is None:
            state["first_time"] = current_time
            state["last_time"] = current_time
            state["count"] = 1
            state["actual_hz"] = 0.0
        else:
            state["count"] += 1
            elapsed = current_time - state["first_time"]
            if elapsed > 0:
                state["actual_hz"] = state["count"] / elapsed
            state["last_time"] = current_time
            
            # Reset moving average window every 5 seconds to reflect current hz
            if elapsed > 5.0:
                state["first_time"] = current_time
                state["count"] = 1
                
        # Parse message content for raw view
        try:
            # simple dict conversion for raw view
            import yaml
            import copy
            # PyYAML is better for dumping ROS messages than JSON due to bytes/arrays
            raw_str = yaml.dump(self.msg_to_dict(msg), allow_unicode=True)
            state["raw"] = raw_str
        except Exception as e:
            state["raw"] = f"Raw data parsing error: {e}"
            
        # Check Custom Header for Src/Dst validation
        if hasattr(msg, 'header') or hasattr(msg, 'communication_header'):
            hdr = getattr(msg, 'header', None)
            if not hdr:
                hdr = getattr(msg, 'communication_header', None)
                
            if hasattr(hdr, 'src') and hasattr(hdr, 'dst'):
                # Extract actual src and dst
                actual_src = str(hdr.src)
                actual_dst_list = [str(d) for d in hdr.dst]
                
                # Check Missing Dst
                target_dst_ids = [d.name for d in target.dst if d.node_type == "ID"]
                missing = []
                for tgt_dst in target_dst_ids:
                    if tgt_dst not in actual_dst_list:
                        missing.append(tgt_dst)
                state["missing_dst"] = missing

    def msg_to_dict(self, msg):
        """Recursively convert ROS message to dictionary."""
        if not hasattr(msg, 'get_fields_and_field_types'):
            if isinstance(msg, bytes):
                return "<bytes>"
            if isinstance(msg, list) or hasattr(msg, '__iter__'):
                if len(msg) > 100:
                    return f"<array of length {len(msg)}>"
                return [self.msg_to_dict(m) for m in msg]
            return msg
        
        d = {}
        for field, _ in msg.get_fields_and_field_types().items():
            val = getattr(msg, field)
            d[field] = self.msg_to_dict(val)
        return d
        
    def get_validation_results(self):
        """Returns the updated states for the GUI thread."""
        results = {}
        for t_name, state in self.topic_states.items():
            # Actual QoS validation requires getting publishers info
            actual_qos = "Unknown"
            status = ValidationStatus.PENDING
            
            pubs = self.get_publishers_info_by_topic(t_name)
            if len(pubs) == 0 and state["actual_hz"] == 0:
                status = ValidationStatus.NOT_RECEIVED
                actual_qos = "-"
            else:
                if len(pubs) > 0:
                    # Look at the first publisher's QoS
                    rel = pubs[0].qos_profile.reliability
                    if rel == QoSReliabilityPolicy.RELIABLE:
                        actual_qos = "Reliable"
                    elif rel == QoSReliabilityPolicy.BEST_EFFORT:
                        actual_qos = "BestEffort"
                    
                target = state["target"]
                hz_diff = abs(state["actual_hz"] - target.target_hz)
                
                if actual_qos != "Unknown" and actual_qos.lower() != target.target_qos.lower():
                    status = ValidationStatus.QOS_MISMATCH
                elif state["missing_dst"]:
                    status = ValidationStatus.MISSING_DST
                elif state["actual_hz"] > 0 and (hz_diff / target.target_hz) > self.hz_margin:
                    status = ValidationStatus.HZ_MISMATCH
                elif state["actual_hz"] > 0:
                    status = ValidationStatus.NORMAL
                
                # Check Node-based missing dst (if no custom header ID check was done)
                if not state["missing_dst"] and status == ValidationStatus.NORMAL:
                    subs = self.get_subscriptions_info_by_topic(t_name)
                    actual_sub_names = [s.node_name for s in subs]
                    missing_nodes = [d.name for d in target.dst if d.node_type == "Node" and d.name not in actual_sub_names]
                    if missing_nodes:
                        state["missing_dst"] = missing_nodes
                        status = ValidationStatus.MISSING_DST
            
            results[t_name] = {
                "actual_hz": state["actual_hz"],
                "actual_qos": actual_qos,
                "status": status,
                "missing_dst": state["missing_dst"],
                "raw": state["raw"]
            }
        return results