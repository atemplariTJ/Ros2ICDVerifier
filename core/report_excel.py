import pandas as pd
import os
from datetime import datetime
from typing import List
from core.models import TopicInfo


def export_to_excel(topics: List[TopicInfo], file_path: str):
    """
    Exports the current validation results to an Excel file.
    """
    data = []
    for t in topics:
        # Connected nodes
        pub_nodes = ", ".join(t.connected_publishers) if t.connected_publishers else "-"
        sub_nodes = ", ".join(t.connected_subscribers) if t.connected_subscribers else "-"

        # Robot IDs from communication_header
        robot_src = t.header_src_id if t.header_src_id is not None else "-"
        robot_dst = ", ".join(t.header_dst_ids) if t.header_dst_ids else "-"

        # Hz display
        if t.target_hz == 0:
            target_hz_str = "비주기"
        else:
            target_hz_str = str(t.target_hz)

        actual_hz_str = f"{t.actual_hz:.2f}" if t.actual_hz is not None else "-"

        data.append({
            "토픽명":       t.name,
            "타입":         t.topic_type,
            "송신 노드":    pub_nodes,
            "수신 노드":    sub_nodes,
            "RobotID 송신": robot_src,
            "RobotID 수신": robot_dst,
            "목표 QoS":     t.target_qos,
            "송신 QoS":     t.actual_pub_qos if t.actual_pub_qos else "-",
            "수신 QoS":     t.actual_sub_qos if t.actual_sub_qos else "-",
            "목표 Hz":      target_hz_str,
            "실제 Hz":      actual_hz_str,
            "검증 상태":    t.status.value,
        })

    df = pd.DataFrame(data)

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='ICD_Validation_Report')

        # Summary sheet
        summary_data = {
            "항목": ["전체 토픽 수", "정상(Pass)", "오류(Fail)", "미수신"],
            "건수": [
                len(topics),
                sum(1 for t in topics if t.status.name == "NORMAL"),
                sum(1 for t in topics
                    if t.status.name not in ("NORMAL", "PENDING", "NOT_RECEIVED")),
                sum(1 for t in topics if t.status.name == "NOT_RECEIVED")
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')

    return file_path
