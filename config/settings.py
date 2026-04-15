from enum import Enum

class ValidationStatus(Enum):
    PENDING = "대기중"
    NORMAL = "정상"
    QOS_MISMATCH = "QoS 불일치"
    MISSING_DST = "수신처 누락"
    NOT_RECEIVED = "미수신"
    HZ_MISMATCH = "주기 미달"
    ERROR = "오류"

# UI Settings for status badges
STATUS_COLORS = {
    ValidationStatus.NORMAL: {"bg": "#dcfce7", "text": "#166534", "border": "#bbf7d0"},       # green
    ValidationStatus.QOS_MISMATCH: {"bg": "#ffedd5", "text": "#9a3412", "border": "#fed7aa"}, # orange
    ValidationStatus.MISSING_DST: {"bg": "#f3e8ff", "text": "#6b21a8", "border": "#e9d5ff"},  # purple
    ValidationStatus.PENDING: {"bg": "#f3f4f6", "text": "#1f2937", "border": "#e5e7eb"},      # gray
    ValidationStatus.NOT_RECEIVED: {"bg": "#fce7f3", "text": "#9d174d", "border": "#fbcfe8"}, # pink
    ValidationStatus.HZ_MISMATCH: {"bg": "#fef9c3", "text": "#854d0e", "border": "#fef08a"},  # yellow
    ValidationStatus.ERROR: {"bg": "#fee2e2", "text": "#991b1b", "border": "#fecaca"},        # red
}