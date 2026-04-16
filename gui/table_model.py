import sys
import os
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSize, QRectF
from PyQt6.QtGui import QColor, QFont, QTextDocument, QAbstractTextDocumentLayout
from PyQt6.QtWidgets import (
    QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle
)
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.models import TopicInfo
from config.settings import ValidationStatus, STATUS_COLORS

# ---------------------------------------------------------------------------
# HTML Delegate — renders HTML content inside table cells
# ---------------------------------------------------------------------------
class HtmlDelegate(QStyledItemDelegate):
    """Renders cells that contain HTML markup (those starting with '<')."""

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        html_text = options.text
        if not html_text or not html_text.startswith('<'):
            super().paint(painter, option, index)
            return

        doc = QTextDocument()
        doc.setDocumentMargin(4)
        doc.setHtml(html_text)
        options.text = ""

        style = options.widget.style() if options.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()
        text_rect = style.subElementRect(
            QStyle.SubElement.SE_ItemViewItemText, options
        )

        painter.save()
        painter.translate(text_rect.topLeft())
        clip = QRectF(text_rect.translated(-text_rect.topLeft()))
        painter.setClipRect(clip)
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        html_text = options.text
        if not html_text or not html_text.startswith('<'):
            return super().sizeHint(option, index)

        doc = QTextDocument()
        doc.setHtml(html_text)
        doc.setTextWidth(max(option.rect.width(), 180))
        return QSize(int(doc.idealWidth()), int(doc.size().height()) + 8)


# ---------------------------------------------------------------------------
# HTML builders for each cell type
# ---------------------------------------------------------------------------
_CHECK = "&#10003;"   # ✓
_CROSS = "&#10007;"   # ✗
_GREEN = "#15803d"
_RED   = "#b91c1c"
_GRAY  = "#6b7280"
_FONT  = "font-size:12px; font-family:Arial; line-height:1.5;"


def _span(color: str, text: str) -> str:
    return f'<span style="color:{color};">{text}</span>'


def build_connected_nodes_html(topic: TopicInfo) -> str:
    """Build HTML for the 연결 노드 column."""
    lines = []

    # Publishers
    if topic.connected_publishers:
        pub_list = ", ".join(topic.connected_publishers)
        lines.append(f'<b style="color:#1d4ed8;">송신:</b> {pub_list}')
    else:
        lines.append(f'<b style="color:{_GRAY};">송신:</b> <i style="color:{_GRAY};">없음</i>')

    # Subscribers
    if topic.connected_subscribers:
        sub_list = ", ".join(topic.connected_subscribers)
        lines.append(f'<b style="color:#7c3aed;">수신:</b> {sub_list}')
    else:
        lines.append(f'<b style="color:{_GRAY};">수신:</b> <i style="color:{_GRAY};">없음</i>')

    # Robot IDs from communication_header
    if topic.header_src_id is not None:
        lines.append(
            f'<span style="color:#0369a1;">RobotID</span> '
            f'송신:{topic.header_src_id} / '
            f'수신:{", ".join(topic.header_dst_ids) if topic.header_dst_ids else "-"}'
        )

    body = "<br/>".join(lines)
    return f'<div style="{_FONT} padding:5px;">{body}</div>'


def build_qos_html(topic: TopicInfo) -> str:
    """Build HTML for the QoS 검증 column."""
    target = topic.target_qos
    pub_qos = topic.actual_pub_qos or "-"
    sub_qos = topic.actual_sub_qos or "-"

    # Publisher check: pub matches target?
    if pub_qos in ("-", "Unknown"):
        pub_line = f'송신 QoS: <span style="color:{_GRAY};">-</span>'
    elif pub_qos.lower() == target.lower():
        pub_line = f'송신 QoS: {_span(_GREEN, _CHECK + " " + pub_qos)}'
    else:
        pub_line = f'송신 QoS: {_span(_RED, _CROSS + " " + pub_qos)}'

    # Subscriber check: sub matches target AND compatible with pub?
    if sub_qos in ("-", "Unknown"):
        sub_line = f'수신 QoS: <span style="color:{_GRAY};">-</span>'
    else:
        sub_ok = sub_qos.lower() == target.lower()
        incompatible = (pub_qos == "BestEffort" and sub_qos == "Reliable")
        if incompatible:
            sub_line = f'수신 QoS: {_span(_RED, _CROSS + " " + sub_qos + " (비호환)")}'
        elif sub_ok:
            sub_line = f'수신 QoS: {_span(_GREEN, _CHECK + " " + sub_qos)}'
        else:
            sub_line = f'수신 QoS: {_span(_RED, _CROSS + " " + sub_qos)}'

    target_line = f'목표: <b>{target}</b>'
    body = "<br/>".join([target_line, pub_line, sub_line])
    return f'<div style="{_FONT} padding:5px;">{body}</div>'


def build_hz_html(topic: TopicInfo) -> str:
    """Build HTML for the Hz 검증 column."""
    target_hz = topic.target_hz
    actual_hz = topic.actual_hz

    if target_hz == 0:
        target_line = '목표: <b>비주기</b>'
        if actual_hz is not None and actual_hz > 0:
            recv_line = _span(_GREEN, _CHECK + " 수신됨")
        elif topic.status == ValidationStatus.NOT_RECEIVED:
            recv_line = _span(_RED, _CROSS + " 미수신")
        else:
            recv_line = f'<span style="color:{_GRAY};">대기중...</span>'
        body = "<br/>".join([target_line, recv_line])
    else:
        target_line = f'목표: <b>{target_hz} Hz</b>'
        if actual_hz is None or actual_hz == 0:
            hz_line = f'<span style="color:{_GRAY};">실제: 대기중...</span>'
        else:
            # Check within margin
            hz_diff = abs(actual_hz - target_hz)
            within_margin = (hz_diff / target_hz) <= 0.2  # use 20% as visual default
            if topic.status == ValidationStatus.HZ_MISMATCH:
                within_margin = False
            elif topic.status == ValidationStatus.NORMAL:
                within_margin = True

            hz_text = f"{actual_hz:.1f} Hz"
            if within_margin:
                hz_line = f'실제: {_span(_GREEN, _CHECK + " " + hz_text)}'
            else:
                hz_line = f'실제: {_span(_RED, _CROSS + " " + hz_text)}'
        body = "<br/>".join([target_line, hz_line])

    return f'<div style="{_FONT} padding:5px;">{body}</div>'


# ---------------------------------------------------------------------------
# Status badge helpers  (text, bg_hex, fg_hex)
# ---------------------------------------------------------------------------
_B_GREEN  = ("#dcfce7", "#166534")
_B_ORANGE = ("#ffedd5", "#9a3412")
_B_YELLOW = ("#fef9c3", "#854d0e")
_B_PINK   = ("#fce7f3", "#9d174d")
_B_BLUE   = ("#eff6ff", "#1d4ed8")
_B_GRAY   = ("#f3f4f6", "#4b5563")
_B_RED    = ("#fee2e2", "#991b1b")


def _reception_badge(topic: "TopicInfo"):
    if topic.received:
        return ("수신됨", *_B_GREEN)
    return ("미수신", *_B_PINK)


def _qos_badge(topic: "TopicInfo"):
    pub    = topic.actual_pub_qos or "-"
    sub    = topic.actual_sub_qos or "-"
    target = topic.target_qos
    if pub in ("-", "Unknown"):
        return ("-", *_B_GRAY)
    if pub.lower() != target.lower():
        return ("불일치", *_B_ORANGE)
    if pub == "BestEffort" and sub == "Reliable":
        return ("비호환", *_B_ORANGE)
    if sub not in ("-", "Unknown") and sub.lower() != target.lower():
        return ("불일치", *_B_ORANGE)
    return ("정상", *_B_GREEN)


def _hz_badge(topic: "TopicInfo"):
    if topic.target_hz == 0:
        if topic.received:
            return ("비주기·정상", *_B_BLUE)
        return ("미수신", *_B_PINK)
    if topic.status == ValidationStatus.HZ_MISMATCH:
        return ("주기미달", *_B_YELLOW)
    if topic.actual_hz and topic.actual_hz > 0:
        return ("정상", *_B_GREEN)
    return ("대기중", *_B_GRAY)


def _summary_badge(topic: "TopicInfo"):
    s = topic.status
    if s == ValidationStatus.NORMAL:
        return ("정상", *_B_GREEN)
    if s == ValidationStatus.PENDING:
        return ("대기중", *_B_GRAY)
    if s == ValidationStatus.NOT_RECEIVED:
        return ("미수신", *_B_PINK)
    if s == ValidationStatus.QOS_MISMATCH:
        return ("QoS불일치", *_B_ORANGE)
    if s == ValidationStatus.HZ_MISMATCH:
        return ("주기미달", *_B_YELLOW)
    return ("오류", *_B_RED)


_BADGE_FN = [_reception_badge, _qos_badge, _hz_badge, _summary_badge]


# ---------------------------------------------------------------------------
# Table Model
# ---------------------------------------------------------------------------
class TopicTableModel(QAbstractTableModel):
    """
    Columns:
      0  토픽명   (topic name + type, 2-line)
      1  연결 노드 (actual publishers / subscribers, robot IDs)
      2  QoS 검증  (target / pub / sub with ✓/✗, HTML)
      3  Hz 검증   (target / actual with ✓/✗, HTML)
      4  수신      (status badge)
      5  QoS       (status badge)
      6  주기      (status badge)
      7  종합      (summary badge)
    """

    HEADERS = ["토픽명", "연결 노드", "QoS 검증", "Hz 검증", "수신", "QoS", "주기", "종합"]
    _BADGE_COLS = (4, 5, 6, 7)

    def __init__(self, data: List[TopicInfo] = None):
        super().__init__()
        self._data = data or []
        self._selected_row = -1

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
                return build_connected_nodes_html(topic)
            elif col == 2:
                return build_qos_html(topic)
            elif col == 3:
                return build_hz_html(topic)
            elif col in self._BADGE_COLS:
                text, _bg, _fg = _BADGE_FN[col - 4](topic)
                return text

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (2, 3) or col in self._BADGE_COLS:
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.BackgroundRole:
            if col in self._BADGE_COLS:
                _text, bg, _fg = _BADGE_FN[col - 4](topic)
                return QColor(bg)
            if row == self._selected_row:
                return QColor("#eff6ff")

        elif role == Qt.ItemDataRole.ForegroundRole:
            if col in self._BADGE_COLS:
                _text, _bg, fg = _BADGE_FN[col - 4](topic)
                return QColor(fg)
            return QColor("#000000")

        return None

    def rowCount(self, index: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, index: QModelIndex = QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def update_data(self, new_data: List[TopicInfo]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_topic(self, row: int) -> TopicInfo:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None
