from dataclasses import dataclass, field
from typing import List, Optional
from config.settings import ValidationStatus

@dataclass
class NodeInfo:
    """Represents a source or destination node/ID"""
    name: str
    node_type: str = "Node"  # 'Node' or 'ID'

@dataclass
class TopicInfo:
    """Data model representing a single ROS2 Topic and its validation state"""
    id: int
    name: str
    topic_type: str
    target_qos: str
    target_hz: float
    src: NodeInfo
    dst: List[NodeInfo]

    # Validation Results (Updated during runtime)
    actual_qos: Optional[str] = None        # Publisher QoS (backward compat)
    actual_pub_qos: Optional[str] = None    # Publisher QoS
    actual_sub_qos: Optional[str] = None    # Subscriber QoS
    actual_hz: Optional[float] = None
    status: ValidationStatus = ValidationStatus.PENDING
    missing_dst: List[str] = field(default_factory=list)  # kept for compat, not validated
    raw_data: str = "대기중..."

    # Connected node info (actual nodes from ROS2 graph)
    connected_publishers: List[str] = field(default_factory=list)
    connected_subscribers: List[str] = field(default_factory=list)

    # Robot IDs from communication_header (custom message header)
    header_src_id: Optional[str] = None
    header_dst_ids: List[str] = field(default_factory=list)

    def to_dict(self):
        """Converts to dictionary, useful for UI rendering or exporting"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.topic_type,
            "targetQos": self.target_qos,
            "targetHz": self.target_hz,
            "src": {"name": self.src.name, "type": self.src.node_type},
            "dst": [{"name": d.name, "type": d.node_type} for d in self.dst],
            "actualQos": self.actual_qos,
            "actualPubQos": self.actual_pub_qos,
            "actualSubQos": self.actual_sub_qos,
            "actualHz": self.actual_hz,
            "status": self.status.value,
            "missingDst": self.missing_dst,
            "connectedPublishers": self.connected_publishers,
            "connectedSubscribers": self.connected_subscribers,
            "headerSrcId": self.header_src_id,
            "headerDstIds": self.header_dst_ids,
            "raw": self.raw_data
        }
