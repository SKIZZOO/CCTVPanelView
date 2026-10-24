import os
import sys
import shutil
import tempfile
import subprocess
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QProgressBar, QTextEdit,
    QFrame, QCheckBox
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QIcon, QPainterPath

APP_NAME = "CCTVPanelView"
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_vector_icon(icon_type: str, color: str = "#ef4444", size: int = 24) -> QPixmap:
    """Renders crisp vector iconography for the Uninstaller without emojis."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if icon_type == "trash":
        # Can body
        p.drawRoundedRect(int(size * 0.22), int(size * 0.32), int(size * 0.56), int(size * 0.54), 2, 2)
        # Lid & handle
        p.drawLine(int(size * 0.16), int(size * 0.32), int(size * 0.84), int(size * 0.32))
        p.drawRoundedRect(int(size * 0.38), int(size * 0.20), int(size * 0.24), int(size * 0.12), 1, 1)
        # Slits
        p.drawLine(int(size * 0.38), int(size * 0.44), int(size * 0.38), int(size * 0.74))
        p.drawLine(int(size * 0.50), int(size * 0.44), int(size * 0.50), int(size * 0.74))
        p.drawLine(int(size * 0.62), int(size * 0.44), int(size * 0.62), int(size * 0.74))
    elif icon_type == "warning":
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.14)
        path.lineTo(size * 0.88, size * 0.84)
        path.lineTo(size * 0.12, size * 0.84)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(int(size * 0.50), int(size * 0.40), int(size * 0.50), int(size * 0.62))
        p.drawPoint(int(size * 0.50), int(size * 0.74))
    elif icon_type == "check":
        p.drawLine(int(size * 0.28), int(size * 0.50), int(size * 0.44), int(size * 0.66))
        p.drawLine(int(size * 0.44), int(size * 0.66), int(size * 0.74), int(size * 0.34))
    elif icon_type == "close":
        p.drawLine(int(size * 0.30), int(size * 0.30), int(size * 0.70), int(size * 0.70))
        p.drawLine(int(size * 0.70), int(size * 0.30), int(size * 0.30), int(size * 0.70))

    p.end()
    return pix


class UninstallerWorker(QThread):
    """Background worker executing clean workstation removal."""
    progress_updated = pyqtSignal(int, str, str)  # percent, status_title, detail_log
    uninstall_finished = pyqtSignal(bool, str)

    def __init__(self, target_dir: str, keep_recordings: bool, remove_config: bool):
        super().__init__()
        self.target_dir = os.path.abspath(target_dir)
        self.keep_recordings = keep_recordings
        self.remove_config = remove_config

    def run(self):
        try:
            def advance(percent: int, title: str, detail: str):
                self.progress_updated.emit(percent, title, detail)
                self.msleep(160)

            # Step 1: Terminate running processes
            advance(10, "Closing active CCTVPanelView processes...", "[PROC] Checking for active surveillance engine instances...")
            import psutil
            target_exe = os.path.normcase(os.path.join(self.target_dir, "CCTVPanelView.exe"))
            for proc in psutil.process_iter(["exe"]):
                if os.path.normcase(proc.info.get("exe") or "") == target_exe:
                    raise RuntimeError("Close CCTVPanelView before uninstalling so recordings can finish safely.")
            advance(20, "Process inspection completed.", "[PROC] Active workstation processes halted.")

            # Step 2: Remove Windows Desktop & Start Menu Shortcuts
            advance(35, "Removing Windows shell shortcuts...", "[SHELL] Locating user desktop and Start Menu shortcuts...")
            desktop_dir = os.path.expanduser("~/Desktop")
            desktop_lnk = os.path.join(desktop_dir, f"{APP_NAME}.lnk")
            if os.path.exists(desktop_lnk):
                try:
                    os.remove(desktop_lnk)
                    advance(45, "Removing Desktop shortcut...", f"[SHORTCUT] Removed: {desktop_lnk}")
                except Exception as e:
                    advance(45, "Removing Desktop shortcut...", f"[SHORTCUT] Could not remove {desktop_lnk}: {e}")

            start_menu_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
            sm_lnk = os.path.join(start_menu_dir, f"{APP_NAME}.lnk")
            if os.path.exists(sm_lnk):
                try:
                    os.remove(sm_lnk)
                    advance(55, "Removing Start Menu program...", f"[SHORTCUT] Removed: {sm_lnk}")
                except Exception as e:
                    advance(55, "Removing Start Menu program...", f"[SHORTCUT] Could not remove {sm_lnk}: {e}")

            sm_uninst_lnk = os.path.join(start_menu_dir, f"Uninstall {APP_NAME}.lnk")
            if os.path.exists(sm_uninst_lnk):
                try:
                    os.remove(sm_uninst_lnk)
                except Exception:
                    pass

            # Step 3: Remove Windows Registry Registration
            advance(65, "Unregistering system components...", "[REG] Removing Windows Add/Remove Programs registry entry...")
            try:
                import winreg
                reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\CCTVPanelView"
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, reg_path)
                advance(72, "System registry cleaned.", "[REG] Registry entries removed successfully.")
            except Exception as e:
                advance(72, "Registry check complete.", f"[REG] Registry key cleanup notice: {e}")

            # Step 4: Remove Application Binaries & Assets
            advance(80, "Removing core binaries & UI libraries...", "[FS] Deleting application core engine and neural models...")
            items_to_remove = [
                "core", "ui", "assets", "sounds",
                "CCTVPanelView.exe", "mobilenet.caffemodel", "yolov5n.onnx", "deploy.prototxt",
                "main.py", "cctv_server.py", "CCTVPanelView.vbs", "crash.log"
            ]
            for item in items_to_remove:
                p = os.path.join(self.target_dir, item)
                if os.path.exists(p):
                    try:
                        if os.path.isdir(p):
                            shutil.rmtree(p, ignore_errors=True)
                        else:
                            os.remove(p)
                    except Exception:
                        pass

            # Step 5: Configuration & Recordings
            if self.remove_config:
                advance(88, "Removing configuration profiles...", "[CONFIG] Deleting cameras_config.json...")
                cfg = os.path.join(self.target_dir, "cameras_config.json")
                if os.path.exists(cfg):
                    try:
                        os.remove(cfg)
                    except Exception:
                        pass
            else:
                advance(88, "Preserving configuration...", "[CONFIG] Preserving configuration file for future installs.")

            if not self.keep_recordings:
                advance(94, "Purging surveillance recordings...", "[MEDIA] Removing snapshots and recordings folders...")
                for fld in ["snapshots", "recordings", "logs"]:
                    p = os.path.join(self.target_dir, fld)
                    if os.path.exists(p):
                        shutil.rmtree(p, ignore_errors=True)
            else:
                advance(94, "Preserving recordings archive...", "[MEDIA] User recordings and snapshots safely preserved.")

            # Finalize
            advance(100, "Uninstallation completed successfully!", "[FINISH] CCTVPanelView deployment removed.")
            self.msleep(300)
            self.uninstall_finished.emit(True, "Success")
        except Exception as e:
            self.uninstall_finished.emit(False, str(e))


class CCTVPanelViewUninstaller(QMainWindow):
    """
    Obsidian Glass Workstation Uninstaller for CCTVPanelView.
    - Draggable frameless geometry with subtle warning rose/amber border
    - Clear confirmation with option to preserve footage archives
    - Terminal progress log and clean final summary
    """

    def __init__(self, target_dir: Optional[str] = None):
        super().__init__()
        self.drag_position = QPoint()

        # Determine target directory
        if not target_dir:
            if getattr(sys, "frozen", False):
                parent = os.path.dirname(os.path.abspath(sys.executable))
            else:
                parent = os.path.dirname(os.path.abspath(__file__))
            # Safety guard: Never target the development source repository!
            is_dev_repo = os.path.exists(os.path.join(parent, "installer.py")) or "cam720" in parent.lower()
            if not is_dev_repo and (os.path.exists(os.path.join(parent, "CCTVPanelView.exe")) or os.path.exists(os.path.join(parent, "cameras_config.json"))):
                self.target_dir = parent
            else:
                self.target_dir = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "Programs", APP_NAME)
        else:
            self.target_dir = os.path.abspath(target_dir)

        self.setWindowTitle(f"Uninstall {APP_NAME}")
        self.setFixedSize(740, 510)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._setup_ui()

    def _setup_ui(self):
        self.central_container = QFrame(self)
        self.central_container.setObjectName("central_container")
        self.central_container.setGeometry(10, 10, 720, 490)
        self.central_container.setStyleSheet("""
            QFrame#central_container {
                background-color: #080c16;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 16px;
            }
            QCheckBox {
                color: #f1f5f9;
                font-size: 11.5px;
                spacing: 8px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.20);
                background-color: rgba(15, 23, 42, 0.85);
            }
            QCheckBox::indicator:hover {
                border-color: #ef4444;
            }
            QCheckBox::indicator:checked {
                background-color: #dc2626;
                border-color: #ef4444;
            }
        """)

        master_layout = QVBoxLayout(self.central_container)
        master_layout.setContentsMargins(0, 0, 0, 0)
        master_layout.setSpacing(0)

        # Title bar
        tb = self._create_title_bar()
        master_layout.addWidget(tb)

        # Stacked Pages
        self.stack = QStackedWidget(self.central_container)
        self.page_confirm = self._create_page_confirm()
        self.page_progress = self._create_page_progress()
        self.page_complete = self._create_page_complete()

        self.stack.addWidget(self.page_confirm)
        self.stack.addWidget(self.page_progress)
        self.stack.addWidget(self.page_complete)

        master_layout.addWidget(self.stack, stretch=1)

    def _create_title_bar(self) -> QWidget:
        tb = QFrame(self.central_container)
        tb.setFixedHeight(46)
        tb.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 23, 42, 0.85);
                border-top-left-radius: 15px;
                border-top-right-radius: 15px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        layout = QHBoxLayout(tb)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        lbl_logo = QLabel(tb)
        lbl_logo.setPixmap(create_vector_icon("trash", color="#ef4444", size=20))
        lbl_logo.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(lbl_logo)

        lbl_title = QLabel(f"{APP_NAME} Workstation Uninstaller", tb)
        lbl_title.setStyleSheet("color: #f8fafc; font-weight: 750; font-size: 13px; background: transparent; border: none;")
        layout.addWidget(lbl_title)

        layout.addStretch()

        btn_close = QPushButton("✕", tb)
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-size: 13px;
                font-weight: 700;
                border-radius: 13px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.25);
                color: #ffffff;
            }
        """)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        return tb

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.pos().y() <= 46:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = QPoint()

    # -------------------------------------------------------------
    # Page 0: Confirm Screen
    # -------------------------------------------------------------
    def _create_page_confirm(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 22, 32, 24)
        layout.setSpacing(14)

        # Hero Banner
        hero = QFrame(w)
        hero.setObjectName("hero_frame")
        hero.setStyleSheet("""
            QFrame#hero_frame {
                background-color: rgba(15, 23, 42, 0.70);
                border: 1px solid rgba(239, 68, 68, 0.30);
                border-radius: 12px;
            }
            QFrame#hero_frame QLabel {
                background: transparent;
                border: none;
            }
        """)
        h_layout = QHBoxLayout(hero)
        h_layout.setContentsMargins(18, 16, 18, 16)
        h_layout.setSpacing(16)

        lbl_hero_ico = QLabel(hero)
        lbl_hero_ico.setPixmap(create_vector_icon("warning", color="#ef4444", size=48))
        lbl_hero_ico.setFixedSize(48, 48)
        h_layout.addWidget(lbl_hero_ico)

        info_box = QVBoxLayout()
        info_box.setSpacing(3)
        lbl_h_title = QLabel("Uninstall CCTVPanelView Workstation?", hero)
        lbl_h_title.setStyleSheet("color: #f8fafc; font-size: 16px; font-weight: 800;")
        lbl_h_sub = QLabel("This will remove CCTVPanelView workstation binaries, shell shortcuts, and registry integrations.", hero)
        lbl_h_sub.setStyleSheet("color: #94a3b8; font-size: 11.5px;")
        info_box.addWidget(lbl_h_title)
        info_box.addWidget(lbl_h_sub)
        h_layout.addLayout(info_box, stretch=1)
        layout.addWidget(hero)

        # Target Installation Folder Card
        loc_card = QFrame(w)
        loc_card.setObjectName("loc_card")
        loc_card.setStyleSheet("""
            QFrame#loc_card {
                background-color: rgba(15, 23, 42, 0.50);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QFrame#loc_card QLabel {
                background: transparent;
                border: none;
            }
        """)
        l_box = QVBoxLayout(loc_card)
        l_box.setContentsMargins(16, 12, 16, 12)
        l_box.setSpacing(4)
        lbl_loc_t = QLabel("Workstation Target Directory:", loc_card)
        lbl_loc_t.setStyleSheet("color: #cbd5e1; font-size: 11px; font-weight: 700;")
        self.lbl_target_path = QLabel(self.target_dir, loc_card)
        self.lbl_target_path.setStyleSheet("color: #38bdf8; font-size: 12px; font-family: 'Consolas', monospace;")
        l_box.addWidget(lbl_loc_t)
        l_box.addWidget(self.lbl_target_path)
        layout.addWidget(loc_card)

        # Options Card
        opts_card = QFrame(w)
        opts_card.setObjectName("opts_card")
        opts_card.setStyleSheet("""
            QFrame#opts_card {
                background-color: rgba(15, 23, 42, 0.50);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        o_box = QVBoxLayout(opts_card)
        o_box.setContentsMargins(16, 12, 16, 12)
        o_box.setSpacing(8)

        self.chk_keep_footage = QCheckBox("Keep surveillance video recordings and snapshot archives (Recommended)", opts_card)
        self.chk_keep_footage.setChecked(True)
        o_box.addWidget(self.chk_keep_footage)

        self.chk_del_config = QCheckBox("Remove user settings, layout presets, and camera configurations", opts_card)
        self.chk_del_config.setChecked(False)
        o_box.addWidget(self.chk_del_config)

        layout.addWidget(opts_card)
        layout.addStretch()

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_cancel = QPushButton("Cancel", w)
        btn_cancel.setFixedSize(110, 36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        btn_cancel.clicked.connect(self.close)
        btn_row.addWidget(btn_cancel)

        btn_row.addStretch()

        self.btn_uninstall = QPushButton("Uninstall CCTVPanelView", w)
        self.btn_uninstall.setFixedSize(190, 36)
        self.btn_uninstall.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_uninstall.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: #ffffff;
                border: 1px solid #ef4444;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 750;
            }
            QPushButton:hover {
                background-color: #b91c1c;
                border-color: #f87171;
            }
            QPushButton:pressed {
                background-color: #991b1b;
            }
        """)
        self.btn_uninstall.clicked.connect(self._start_uninstall)
        btn_row.addWidget(self.btn_uninstall)

        layout.addLayout(btn_row)
        return w

    # -------------------------------------------------------------
    # Page 1: Progress Screen
    # -------------------------------------------------------------
    def _create_page_progress(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 22, 32, 24)
        layout.setSpacing(12)

        p_hdr = QHBoxLayout()
        self.lbl_uninst_title = QLabel("Uninstalling CCTVPanelView...", w)
        self.lbl_uninst_title.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: 750; background: transparent;")
        p_hdr.addWidget(self.lbl_uninst_title)
        p_hdr.addStretch()
        self.lbl_percent = QLabel("0%", w)
        self.lbl_percent.setStyleSheet("color: #ef4444; font-size: 14px; font-weight: 800; background: transparent;")
        p_hdr.addWidget(self.lbl_percent)
        layout.addLayout(p_hdr)

        self.lbl_step_desc = QLabel("Initializing uninstallation worker...", w)
        self.lbl_step_desc.setStyleSheet("color: #94a3b8; font-size: 11px; background: transparent;")
        layout.addWidget(self.lbl_step_desc)

        self.prog_bar = QProgressBar(w)
        self.prog_bar.setFixedHeight(8)
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(15, 23, 42, 0.90);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b91c1c, stop:1 #ef4444);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.prog_bar)

        # Console Activity Log
        lbl_log_t = QLabel("ACTIVITY LOG", w)
        lbl_log_t.setStyleSheet("color: #ef4444; font-size: 9.5px; font-weight: 800; letter-spacing: 0.8px; margin-top: 6px; background: transparent;")
        layout.addWidget(lbl_log_t)

        self.txt_log = QTextEdit(w)
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("""
            QTextEdit {
                background-color: #04070d;
                color: #94a3b8;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10.5px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 10px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.txt_log, stretch=1)
        return w

    # -------------------------------------------------------------
    # Page 2: Complete Screen
    # -------------------------------------------------------------
    def _create_page_complete(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(36, 26, 36, 26)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Success badge
        badge = QFrame(w)
        badge.setFixedSize(54, 54)
        badge.setObjectName("badge_success")
        badge.setStyleSheet("""
            QFrame#badge_success {
                background-color: rgba(16, 185, 129, 0.15);
                border: 2px solid #10b981;
                border-radius: 27px;
            }
        """)
        b_box = QVBoxLayout(badge)
        b_box.setContentsMargins(0, 0, 0, 0)
        lbl_chk = QLabel(badge)
        lbl_chk.setPixmap(create_vector_icon("check", color="#10b981", size=26))
        lbl_chk.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_chk.setStyleSheet("background: transparent; border: none;")
        b_box.addWidget(lbl_chk)
        layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_done_t = QLabel("CCTVPanelView Successfully Uninstalled", w)
        lbl_done_t.setStyleSheet("color: #f8fafc; font-size: 16px; font-weight: 800; background: transparent;")
        layout.addWidget(lbl_done_t, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_done_sub = QLabel("All application binaries, shell shortcuts, and system registrations have been removed.", w)
        lbl_done_sub.setStyleSheet("color: #94a3b8; font-size: 11.5px; background: transparent;")
        layout.addWidget(lbl_done_sub, alignment=Qt.AlignmentFlag.AlignCenter)

        # Summary Card
        sum_card = QFrame(w)
        sum_card.setObjectName("sum_card")
        sum_card.setStyleSheet("""
            QFrame#sum_card {
                background-color: rgba(15, 23, 42, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QFrame#sum_card QLabel {
                background: transparent;
                border: none;
            }
        """)
        s_layout = QVBoxLayout(sum_card)
        s_layout.setContentsMargins(16, 12, 16, 12)
        s_layout.setSpacing(6)

        self.lbl_sum_status = QLabel(f"Directory: {self.target_dir}", sum_card)
        self.lbl_sum_status.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        s_layout.addWidget(self.lbl_sum_status)

        self.lbl_sum_note = QLabel("Surveillance footage and snapshot folders were preserved.", sum_card)
        self.lbl_sum_note.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 600;")
        s_layout.addWidget(self.lbl_sum_note)

        layout.addWidget(sum_card)
        layout.addStretch()

        # Close Button
        btn_close = QPushButton("Close", w)
        btn_close.setFixedSize(130, 36)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 750;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

        return w

    # -------------------------------------------------------------
    # Execution Logic
    # -------------------------------------------------------------
    def _start_uninstall(self):
        self.stack.setCurrentIndex(1)
        self.txt_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Commencing uninstallation sequence...")

        self.worker = UninstallerWorker(
            target_dir=self.target_dir,
            keep_recordings=self.chk_keep_footage.isChecked(),
            remove_config=self.chk_del_config.isChecked()
        )
        self.worker.progress_updated.connect(self._on_progress_update)
        self.worker.uninstall_finished.connect(self._on_uninstall_completed)
        self.worker.start()

    def _on_progress_update(self, percent: int, title: str, detail: str):
        self.prog_bar.setValue(percent)
        self.lbl_percent.setText(f"{percent}%")
        self.lbl_step_desc.setText(title)
        self.txt_log.append(detail)
        sb = self.txt_log.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _on_uninstall_completed(self, success: bool, msg: str):
        if success:
            if not self.chk_keep_footage.isChecked():
                self.lbl_sum_note.setText("Surveillance footage and snapshot folders were purged.")
                self.lbl_sum_note.setStyleSheet("color: #94a3b8; font-size: 11px;")
            self.stack.setCurrentIndex(2)
        else:
            self.lbl_uninst_title.setText("Uninstallation Encountered an Issue")
            self.lbl_uninst_title.setStyleSheet("color: #ef4444; font-size: 15px; font-weight: 750;")
            self.lbl_step_desc.setText(f"Error: {msg}")


def main():
    # If running from inside target_dir and not already spawned in temp, spawn self from temp so we don't lock files
    is_temp_runner = "--temp-runner" in sys.argv
    target_arg = None
    for arg in sys.argv[1:]:
        if arg.startswith("--target-dir="):
            target_arg = arg.split("=", 1)[1]

    if getattr(sys, 'frozen', False) and not is_temp_runner:
        exe_path = os.path.abspath(sys.executable)
        temp_dir = tempfile.gettempdir()
        temp_uninstaller = os.path.join(temp_dir, "cctvpanelview_uninstall_runner.exe")
        try:
            shutil.copy2(exe_path, temp_uninstaller)
            target = target_arg or os.path.dirname(exe_path)
            subprocess.Popen([temp_uninstaller, "--temp-runner", f"--target-dir={target}"])
            sys.exit(0)
        except Exception:
            pass

    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    icon_path = os.path.join(BASE_DIR, "assets", "cctv_logo.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    uninstaller = CCTVPanelViewUninstaller(target_dir=target_arg)
    uninstaller.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
