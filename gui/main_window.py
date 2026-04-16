import sys
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableView, QHeaderView, QTextEdit, QFileDialog, QFrame,
    QAbstractItemView, QDoubleSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gui.table_model import TopicTableModel, HtmlDelegate
from core.csv_parser import load_icd_from_csv
from core.report_excel import export_to_excel
from config.settings import ValidationStatus
from ros2.worker import Ros2Worker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROS2 ICD 검증 대시보드")
        self.resize(1100, 800)

        self.topics = []
        self.selected_topic_id = None
        self.worker = None
        self.hz_margin = 0.2  # Default 20%

        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ── 1. Header ──────────────────────────────────────────────────────
        header_layout = QHBoxLayout()

        title_label = QLabel("ROS2 ICD 검증 대시보드")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        margin_label = QLabel("주기 오차 허용 (%):")
        self.spin_margin = QDoubleSpinBox()
        self.spin_margin.setRange(0, 100)
        self.spin_margin.setValue(20.0)
        self.spin_margin.setSuffix("%")
        self.spin_margin.valueChanged.connect(self.on_margin_changed)
        header_layout.addWidget(margin_label)
        header_layout.addWidget(self.spin_margin)
        header_layout.addSpacing(20)

        self.btn_load_csv = QPushButton("CSV 불러오기")
        self.btn_start    = QPushButton("검증 시작")
        self.btn_stop     = QPushButton("검증 중지")
        self.btn_report   = QPushButton("보고서 저장")

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_report.setEnabled(False)

        self.btn_load_csv.clicked.connect(self.load_csv)
        self.btn_start.clicked.connect(self.start_validation)
        self.btn_stop.clicked.connect(self.stop_validation)
        self.btn_report.clicked.connect(self.save_report)

        for btn in [self.btn_load_csv, self.btn_start, self.btn_stop, self.btn_report]:
            btn.setMinimumHeight(35)
            header_layout.addWidget(btn)

        main_layout.addLayout(header_layout)

        # ── 2. Summary Panel ───────────────────────────────────────────────
        summary_layout = QHBoxLayout()
        self.lbl_total = self.create_summary_card("전체 토픽", "0개", "#eff6ff", "#1d4ed8")
        self.lbl_pass  = self.create_summary_card("정상 (Pass)", "0개", "#dcfce7", "#15803d")
        self.lbl_fail  = self.create_summary_card("오류 (Fail)", "0개", "#fee2e2", "#b91c1c")

        summary_layout.addWidget(self.lbl_total)
        summary_layout.addWidget(self.lbl_pass)
        summary_layout.addWidget(self.lbl_fail)
        main_layout.addLayout(summary_layout)

        # ── 3. Main Table ──────────────────────────────────────────────────
        self.table_view  = QTableView()
        self.table_model = TopicTableModel()
        self.table_view.setModel(self.table_model)

        # Apply HTML delegate to all columns (it handles non-HTML cells normally)
        html_delegate = HtmlDelegate(self.table_view)
        for col in range(len(TopicTableModel.HEADERS)):
            self.table_view.setItemDelegateForColumn(col, html_delegate)

        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setStyleSheet(
            "alternate-background-color: #f9fafb; background-color: #ffffff; color: #000000;"
        )

        header = self.table_view.horizontalHeader()
        header.setMinimumSectionSize(80)

        # Col 0: 토픽명 — stretch
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        # Col 1: 연결 노드 — stretch
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Col 2: QoS 검증 — interactive (user can resize), initial width 200px
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(2, 200)
        # Col 3: Hz 검증 — interactive, initial width 170px
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.resizeSection(3, 170)
        # Col 4: 상태 — compact badge
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.table_view.verticalHeader().setDefaultSectionSize(80)

        self.table_view.clicked.connect(self.on_table_click)
        main_layout.addWidget(self.table_view, stretch=2)

        # ── 4. Detail View ─────────────────────────────────────────────────
        detail_layout = QVBoxLayout()
        self.lbl_detail_title = QLabel("수신 데이터 상세보기 (Raw Data)")
        self.lbl_detail_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        detail_layout.addWidget(self.lbl_detail_title)

        self.text_raw_data = QTextEdit()
        self.text_raw_data.setReadOnly(True)
        self.text_raw_data.setFont(QFont("Courier New", 12))
        self.text_raw_data.setStyleSheet("background-color: #1e293b; color: #a7f3d0;")
        self.text_raw_data.setText("표에서 토픽을 클릭하면 상세 데이터가 표시됩니다.")
        detail_layout.addWidget(self.text_raw_data)

        main_layout.addLayout(detail_layout, stretch=1)

    # ── Helpers ────────────────────────────────────────────────────────────

    def create_summary_card(self, title, value, bg_color, text_color):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {bg_color}; border-radius: 8px;"
            f" border: 1px solid #e5e7eb; }}"
        )
        layout = QVBoxLayout(card)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #6b7280; font-size: 12px; font-weight: bold;")
        layout.addWidget(lbl_title)

        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {text_color}; font-size: 24px; font-weight: bold;")
        lbl_val.setObjectName("value_label")
        layout.addWidget(lbl_val)

        return card

    def update_summary(self):
        total  = len(self.topics)
        passed = sum(1 for t in self.topics if t.status == ValidationStatus.NORMAL)
        failed = sum(1 for t in self.topics
                     if t.status not in (ValidationStatus.NORMAL, ValidationStatus.PENDING))

        self.lbl_total.findChild(QLabel, "value_label").setText(f"{total}개")
        self.lbl_pass.findChild(QLabel,  "value_label").setText(f"{passed}개")
        self.lbl_fail.findChild(QLabel,  "value_label").setText(f"{failed}개")

    # ── Slot Handlers ──────────────────────────────────────────────────────

    @pyqtSlot(float)
    def on_margin_changed(self, value):
        self.hz_margin = value / 100.0
        if self.worker and self.worker.node:
            self.worker.node.set_hz_margin(self.hz_margin)

    @pyqtSlot()
    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "CSV 파일 선택", "", "CSV Files (*.csv)")
        if file_path:
            try:
                self.topics = load_icd_from_csv(file_path)
                self.table_model.update_data(self.topics)
                self.update_summary()

                self.btn_start.setEnabled(True)
                self.btn_start.setStyleSheet("background-color: #16a34a; color: white;")
                self.text_raw_data.setText("표에서 토픽을 클릭하면 상세 데이터가 표시됩니다.")
                self.lbl_detail_title.setText("수신 데이터 상세보기 (Raw Data)")
                self.selected_topic_id = None

            except Exception as e:
                self.text_raw_data.setText(f"CSV 로드 오류: {str(e)}")

    @pyqtSlot()
    def start_validation(self):
        if not self.topics:
            return

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_stop.setStyleSheet("background-color: #dc2626; color: white;")
        self.text_raw_data.setText("검증 시작됨... 데이터를 기다리는 중입니다.")

        self.worker = Ros2Worker(self.topics, self.hz_margin)
        self.worker.update_signal.connect(self.on_validation_update)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.start()

    @pyqtSlot()
    def stop_validation(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("")
        self.btn_report.setEnabled(True)

        if self.worker:
            self.worker.stop()
            self.worker = None

    @pyqtSlot(dict)
    def on_validation_update(self, results):
        for topic in self.topics:
            if topic.name in results:
                res = results[topic.name]
                topic.actual_hz          = res["actual_hz"]
                topic.actual_qos         = res["actual_qos"]          # backward compat
                topic.actual_pub_qos     = res["actual_pub_qos"]
                topic.actual_sub_qos     = res["actual_sub_qos"]
                topic.status             = res["status"]
                topic.missing_dst        = res["missing_dst"]
                topic.connected_publishers  = res["connected_publishers"]
                topic.connected_subscribers = res["connected_subscribers"]
                topic.header_src_id      = res["header_src"]
                topic.header_dst_ids     = res["header_dst"]
                topic.raw_data           = res["raw"]

                if self.selected_topic_id == topic.id:
                    self.text_raw_data.setText(topic.raw_data)

        self.table_model.layoutChanged.emit()
        self.update_summary()

    @pyqtSlot(str)
    def on_worker_error(self, error_msg):
        QMessageBox.critical(self, "ROS2 Error", f"Worker Error: {error_msg}")
        self.stop_validation()

    @pyqtSlot('QModelIndex')
    def on_table_click(self, index):
        if not index.isValid():
            return

        row = index.row()
        topic = self.table_model.get_topic(row)
        if topic:
            self.selected_topic_id = topic.id
            self.lbl_detail_title.setText(
                f"수신 데이터 상세보기 (Raw Data) - {topic.name}"
            )

            if topic.status in (ValidationStatus.NOT_RECEIVED,):
                self.text_raw_data.setStyleSheet("background-color: #1e293b; color: #d8b4fe;")
            elif topic.status == ValidationStatus.QOS_MISMATCH:
                self.text_raw_data.setStyleSheet("background-color: #1e293b; color: #fb923c;")
            elif topic.status == ValidationStatus.HZ_MISMATCH:
                self.text_raw_data.setStyleSheet("background-color: #1e293b; color: #fde68a;")
            elif topic.status == ValidationStatus.ERROR:
                self.text_raw_data.setStyleSheet("background-color: #1e293b; color: #fca5a5;")
            else:
                self.text_raw_data.setStyleSheet("background-color: #1e293b; color: #6ee7b7;")

            self.text_raw_data.setText(topic.raw_data)

            self.table_model._selected_row = row
            self.table_model.layoutChanged.emit()

    @pyqtSlot()
    def save_report(self):
        if not self.topics:
            return

        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_filename = f"ICD_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        default_path = os.path.join(root_dir, default_filename)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "보고서 저장", default_path, "Excel Files (*.xlsx)"
        )

        if file_path:
            try:
                export_to_excel(self.topics, file_path)
                QMessageBox.information(self, "저장 완료", f"보고서가 저장되었습니다:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "저장 실패", f"보고서 저장 중 오류 발생: {e}")


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
