from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core.device_manager import DeviceManager


class ScannerWorker(QThread):
    device_found = pyqtSignal(dict)
    finished_scan = pyqtSignal(list)

    def __init__(self, subnet="192.168.0", parent=None):
        super().__init__(parent)
        self.subnet = subnet

    def run(self):
        results = DeviceManager.scan_local_subnet(self.subnet)
        self.finished_scan.emit(results)


class ScannerDialog(QDialog):
    """
    Local network scanner for ONVIF and RTSP surveillance cameras.
    """
    camera_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Network Camera Scanner")
        self.resize(600, 450)
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
                color: #f8fafc;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 11px;
            }
            QLineEdit {
                background: #0f172a;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
            }
            QTableWidget {
                background: #0f172a;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 4px;
                gridline-color: #1e293b;
            }
            QHeaderView::section {
                background: #1e293b;
                color: #38bdf8;
                padding: 5px;
                border: none;
                font-weight: 600;
            }
            QPushButton {
                background: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #334155;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Local Network IP Camera Discovery")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #38bdf8;")
        layout.addWidget(title)

        # Subnet config row
        sub_row = QHBoxLayout()
        sub_row.addWidget(QLabel("Subnet Prefix:"))
        self.txt_subnet = QLineEdit(DeviceManager.get_local_subnet())
        self.txt_subnet.setFixedWidth(120)
        sub_row.addWidget(self.txt_subnet)

        self.btn_scan = QPushButton("Start Scan")
        self.btn_scan.setStyleSheet("background: #2563eb; color: #ffffff; border: 1px solid #3b82f6; font-weight: 600;")
        self.btn_scan.clicked.connect(self._start_scan)
        sub_row.addWidget(self.btn_scan)
        sub_row.addStretch()
        layout.addLayout(sub_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setStyleSheet("QProgressBar { border: 1px solid #334155; border-radius: 4px; height: 12px; background: #0f172a; } QProgressBar::chunk { background: #2563eb; border-radius: 3px; }")
        self.progress.hide()
        layout.addWidget(self.progress)

        # Results Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["IP Address", "Port", "Service", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # Footer
        footer = QHBoxLayout()
        self.lbl_status = QLabel("Click 'Start Scan' to search for cameras on the local network.")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        footer.addWidget(self.lbl_status)
        footer.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        layout.addLayout(footer)

    def _start_scan(self):
        subnet = self.txt_subnet.text().strip()
        if not subnet:
            QMessageBox.warning(self, "Invalid Subnet", "Please specify a valid subnet prefix (e.g. 192.168.0)")
            return

        self.table.setRowCount(0)
        self.btn_scan.setEnabled(False)
        self.progress.show()
        self.lbl_status.setText(f"Scanning {subnet}.1 - 254 for RTSP/ONVIF ports...")

        self.worker = ScannerWorker(subnet, self)
        self.worker.finished_scan.connect(self._on_scan_finished)
        self.worker.start()

    def _on_scan_finished(self, results):
        self.btn_scan.setEnabled(True)
        self.progress.hide()
        self.lbl_status.setText(f"Scan completed. Found {len(results)} active camera port(s).")

        self.table.setRowCount(len(results))
        for row, item in enumerate(results):
            ip = item["ip"]
            port = str(item["port"])
            proto = item["protocol"]

            self.table.setItem(row, 0, QTableWidgetItem(ip))
            self.table.setItem(row, 1, QTableWidgetItem(port))
            self.table.setItem(row, 2, QTableWidgetItem(proto))

            btn_add = QPushButton("+ Add")
            btn_add.setStyleSheet("background-color: #2563eb; color: white; font-weight: 600; padding: 4px 8px; border-radius: 4px;")
            btn_add.clicked.connect(lambda ch, dev=item: self._on_add_device(dev))
            self.table.setCellWidget(row, 3, btn_add)

    def _on_add_device(self, dev):
        self.camera_selected.emit(dev)
        self.accept()
