import sys
import os
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor, QFont
from typing import List

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.models import TopicInfo
from config.settings import STATUS_COLORS

class TopicTableModel(QAbstractTableModel):
    def __init__(self, data: List[TopicInfo] = None):
        super().__init__()
        self._data = data or []
        self._headers = ["토픽명 & 타입", "Src (송신) / Dst (수신) 목록", "QoS (목표/실제)", "Hz (목표/실제)", "상태"]

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        topic = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return f"{topic.name}\n{topic.topic_type}"
            elif col == 1:
                src_str = f"S: {topic.src.name} ({topic.src.node_type})"
                dst_list = [f"{d.name} ({d.node_type})" for d in topic.dst]
                dst_str = "D: " + ", ".join(dst_list)
                if topic.missing_dst:
                    dst_str += f"\n누락: {', '.join(topic.missing_dst)}"
                return f"{src_str}\n{dst_str}"
            elif col == 2:
                actual_qos = topic.actual_qos if topic.actual_qos else "-"
                return f"{topic.target_qos}\n{actual_qos}"
            elif col == 3:
                actual_hz = f"{topic.actual_hz:.1f}" if topic.actual_hz is not None else "-"
                return f"{topic.target_hz} Hz\n{actual_hz} Hz"
            elif col == 4:
                return topic.status.value

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [2, 3, 4]:
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Highlight missing dst
            if col == 1 and topic.missing_dst:
                return QColor("#fee2e2") # light red
            # Highlight QoS mismatch
            if col == 2 and topic.actual_qos and topic.actual_qos != topic.target_qos:
                return QColor("#ffedd5") # light orange
                
            if col == 4:
                color_hex = STATUS_COLORS.get(topic.status, {}).get("bg", "#ffffff")
                return QColor(color_hex)
            
            if row == getattr(self, '_selected_row', -1):
                return QColor("#eff6ff") # light blue for selection

        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == 4:
                color_hex = STATUS_COLORS.get(topic.status, {}).get("text", "#000000")
                return QColor(color_hex)
            return QColor("#000000") # Force black text for other columns

        return None

    def rowCount(self, index: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, index: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]
        return None

    def update_data(self, new_data: List[TopicInfo]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_topic(self, row: int) -> TopicInfo:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None