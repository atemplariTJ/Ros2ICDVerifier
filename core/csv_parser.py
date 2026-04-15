import pandas as pd
from typing import List
import os
import sys

# Add parent dir to path to allow importing when run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.models import TopicInfo, NodeInfo

def parse_node_string(node_str: str) -> NodeInfo:
    """Parse a single node string like 'camera_node' or 'ROBOT_01(ID)'"""
    if pd.isna(node_str) or not str(node_str).strip():
        return NodeInfo(name="Unknown", node_type="Node")
        
    node_str = str(node_str).strip()
    node_type = "Node"
    if "(ID)" in node_str:
        node_str = node_str.replace("(ID)", "").strip()
        node_type = "ID"
        
    return NodeInfo(name=node_str, node_type=node_type)

def parse_dst_string(dst_str: str) -> List[NodeInfo]:
    """Parse comma separated dst string into list of NodeInfo."""
    if pd.isna(dst_str) or not str(dst_str).strip():
        return []
    
    nodes = []
    # e.g., "perception, recorder" or "ROBOT_02(ID), ROBOT_03(ID)"
    for item in str(dst_str).split(','):
        item = item.strip()
        if not item:
            continue
        nodes.append(parse_node_string(item))
        
    return nodes

def load_icd_from_csv(file_path: str) -> List[TopicInfo]:
    """
    Load ICD CSV file and convert it to a list of TopicInfo models.
    Expected CSV columns: Topic, Src, Dst, Type, Qos, Hz
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")
        
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV: {e}")
        
    # Check required columns (case-insensitive mapping)
    required_cols = {'topic', 'type', 'qos', 'hz', 'src', 'dst'}
    actual_cols_lower = {col.lower(): col for col in df.columns}
    
    if not required_cols.issubset(set(actual_cols_lower.keys())):
        missing = required_cols - set(actual_cols_lower.keys())
        raise ValueError(f"CSV is missing required columns. Missing: {missing}")
        
    topics = []
    for idx, row in df.iterrows():
        try:
            topic = TopicInfo(
                id=idx + 1,
                name=str(row[actual_cols_lower['topic']]).strip(),
                topic_type=str(row[actual_cols_lower['type']]).strip(),
                target_qos=str(row[actual_cols_lower['qos']]).strip(),
                target_hz=float(row[actual_cols_lower['hz']]),
                src=parse_node_string(row[actual_cols_lower['src']]),
                dst=parse_dst_string(row[actual_cols_lower['dst']])
            )
            topics.append(topic)
        except Exception as e:
            print(f"Skipping row {idx} due to error: {e}")
            
    return topics

if __name__ == "__main__":
    # Simple test run
    test_file = "../sample_icd.csv"
    if os.path.exists(test_file):
        topics = load_icd_from_csv(test_file)
        for t in topics:
            print(f"Loaded: {t.name} -> Src: {t.src.name}, Dst: {[d.name for d in t.dst]}")