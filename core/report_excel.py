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
        dst_str = ", ".join([f"{d.name}({d.node_type})" for d in t.dst])
        missing_str = ", ".join(t.missing_dst) if t.missing_dst else "없음"
        
        data.append({
            "토픽명": t.name,
            "타입": t.topic_type,
            "송신(Src)": t.src.name,
            "수신(Dst)": dst_str,
            "목표 QoS": t.target_qos,
            "실제 QoS": t.actual_qos if t.actual_qos else "-",
            "목표 Hz": t.target_hz,
            "실제 Hz": f"{t.actual_hz:.2f}" if t.actual_hz is not None else "-",
            "검증 상태": t.status.value,
            "누락 수신처": missing_str
        })
    
    df = pd.DataFrame(data)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    
    # Save to Excel
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='ICD_Validation_Report')
        
        # Add summary sheet
        summary_data = {
            "항목": ["전체 토픽 수", "정상(Pass)", "오류(Fail)", "미수신"],
            "건수": [
                len(topics),
                sum(1 for t in topics if t.status.name == "NORMAL"),
                sum(1 for t in topics if t.status.name not in ["NORMAL", "PENDING", "NOT_RECEIVED"]),
                sum(1 for t in topics if t.status.name == "NOT_RECEIVED")
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, index=False, sheet_name='Summary')

    return file_path
