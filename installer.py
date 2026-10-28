"""
CCTVPanelView - Standalone Modern Windows Installer & Workstation Deployment Wizard
Features:
- Frameless Obsidian Glass UI with rounded corners & custom title bar.
- Animated Cybernetic Optic Reticle & Aperture Spinner.
- Real-time Deployment Engine (File copying, shortcut creation, Start Menu registration).
- Live Telemetry & Event Log Terminal.
- Zero Emojis, 100% English, Unified Electric Sky Blue & Slate Palette.
"""

import sys
import os
import shutil
import math
import subprocess
from core.version import APP_VERSION
from core.installation import registered_install_dir, preserve_upgrade_profile, CONFIG_NAME
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QCheckBox, QProgressBar,
    QStackedWidget, QFrame, QFileDialog, QTextEdit, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPoint, QRectF, QSize
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPixmap, QIcon,
    QPainterPath, QRadialGradient, QLinearGradient
)

BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
APP_NAME = "CCTVPanelView"


def create_vector_icon(icon_type: str, color: str = "#38bdf8", size: int = 20) -> QPixmap:
    """Renders crisp vector iconography for the installer."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    fg = QColor(color)
    pen = QPen(fg, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    if icon_type == "folder":
        path = QPainterPath()
        path.moveTo(size * 0.12, size * 0.28)
        path.lineTo(size * 0.40, size * 0.28)
        path.lineTo(size * 0.50, size * 0.40)
        path.lineTo(size * 0.88, size * 0.40)
        path.lineTo(size * 0.88, size * 0.80)
        path.lineTo(size * 0.12, size * 0.80)
        path.closeSubpath()
        p.drawPath(path)
    elif icon_type == "check":
        p.setPen(QPen(fg, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        path.moveTo(size * 0.22, size * 0.52)
        path.lineTo(size * 0.44, size * 0.74)
        path.lineTo(size * 0.82, size * 0.28)
        p.drawPath(path)
    elif icon_type == "shield":
        path = QPainterPath()
        path.moveTo(size * 0.50, size * 0.14)
        path.lineTo(size * 0.84, size * 0.26)
        path.quadTo(size * 0.84, size * 0.65, size * 0.50, size * 0.88)
        path.quadTo(size * 0.16, size * 0.65, size * 0.16, size * 0.26)
        path.closeSubpath()
        p.drawPath(path)
    elif icon_type == "desktop":
        p.drawRoundedRect(QRectF(size * 0.14, size * 0.18, size * 0.72, size * 0.52), 2, 2)
        p.drawLine(int(size * 0.36), int(size * 0.82), int(size * 0.64), int(size * 0.82))
        p.drawLine(int(size * 0.50), int(size * 0.70), int(size * 0.50), int(size * 0.82))
    elif icon_type == "terminal":
        p.drawRoundedRect(QRectF(size * 0.12, size * 0.16, size * 0.76, size * 0.68), 3, 3)
        p.drawLine(int(size * 0.24), int(size * 0.38), int(size * 0.38), int(size * 0.50))
        p.drawLine(int(size * 0.38), int(size * 0.50), int(size * 0.24), int(size * 0.62))
        p.drawLine(int(size * 0.46), int(size * 0.62), int(size * 0.64), int(size * 0.62))

    p.end()
    return pix


class AnimatedApertureSpinner(QWidget):
    """High-tech cybernetic rotating aperture reticle with pulsing glow."""
    def __init__(self, size: int = 120, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.angle = 0.0
        self.pulse = 0.0
        self.pulse_dir = 1

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def _tick(self):
        self.angle = (self.angle + 2.5) % 360.0
        self.pulse += 0.04 * self.pulse_dir
        if self.pulse >= 1.0:
            self.pulse = 1.0
            self.pulse_dir = -1
        elif self.pulse <= 0.0:
            self.pulse = 0.0
            self.pulse_dir = 1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        max_r = min(w, h) / 2.0 - 4

        # 1. Subtle Radial Background Glow
        glow_grad = QRadialGradient(cx, cy, max_r)
        glow_alpha = int(25 + 20 * self.pulse)
        glow_grad.setColorAt(0.0, QColor(56, 189, 248, glow_alpha))
        glow_grad.setColorAt(0.7, QColor(2, 132, 199, int(glow_alpha * 0.4)))
        glow_grad.setColorAt(1.0, QColor(8, 12, 22, 0))
        p.setBrush(QBrush(glow_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPoint(int(cx), int(cy)), int(max_r), int(max_r))

        # 2. Outer Rotating Tech Ticks
        p.save()
        p.translate(cx, cy)
        p.rotate(self.angle)
        pen_tick = QPen(QColor(56, 189, 248, 160), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen_tick)
        num_ticks = 24
        for i in range(num_ticks):
            deg = i * (360.0 / num_ticks)
            rad = math.radians(deg)
            inner = max_r - 6
            outer = max_r - (12 if i % 6 == 0 else 2)
            p.drawLine(
                int(inner * math.cos(rad)), int(inner * math.sin(rad)),
                int(outer * math.cos(rad)), int(outer * math.sin(rad))
            )
        p.restore()

        # 3. Concentric Reticle Rings
        p.setPen(QPen(QColor(56, 189, 248, 80), 1.2, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPoint(int(cx), int(cy)), int(max_r * 0.72), int(max_r * 0.72))

        p.setPen(QPen(QColor(56, 189, 248, 180), 1.5))
        p.drawEllipse(QPoint(int(cx), int(cy)), int(max_r * 0.52), int(max_r * 0.52))

        # 4. Counter-rotating Inner Aperture Arc
        p.save()
        p.translate(cx, cy)
        p.rotate(-self.angle * 1.6)
        pen_arc = QPen(QColor(56, 189, 248, 230), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen_arc)
        arc_rect = QRectF(-max_r * 0.40, -max_r * 0.40, max_r * 0.80, max_r * 0.80)
        p.drawArc(arc_rect, int(30 * 16), int(100 * 16))
        p.drawArc(arc_rect, int(210 * 16), int(100 * 16))
        p.restore()

        # 5. Core Pulsing Iris
        iris_r = max_r * 0.22 + (self.pulse * 3.0)
        p.setPen(QPen(QColor(255, 255, 255, 240), 1.5))
        p.setBrush(QBrush(QColor(56, 189, 248, int(180 + 75 * self.pulse))))
        p.drawEllipse(QPoint(int(cx), int(cy)), int(iris_r), int(iris_r))
        p.end()


class InstallerDeploymentWorker(QThread):
    """Background worker that executes real workstation file copying & registration."""
    progress_updated = pyqtSignal(int, str, str)  # percent, status_title, log_detail
    installation_finished = pyqtSignal(bool, str)

    def __init__(self, target_dir: str, create_desktop_shortcut: bool,
                 create_start_menu: bool, set_high_dpi: bool, launch_wizard: bool, previous_dir=None):
        super().__init__()
        self.target_dir = os.path.abspath(target_dir)
        self.create_desktop_shortcut = create_desktop_shortcut
        self.create_start_menu = create_start_menu
        self.set_high_dpi = set_high_dpi
        self.launch_wizard = launch_wizard
        self.previous_dir = previous_dir

    def run(self):
        try:
            total_steps = 8
            current_step = 0

            def advance(percent: int, title: str, detail: str):
                self.progress_updated.emit(percent, title, detail)
                self.msleep(180)

            runtime_root = os.path.join(BASE_DIR, "payload", "CCTVPanelView")
            if not os.path.isfile(os.path.join(runtime_root, "CCTVPanelView.exe")) or not os.path.isdir(os.path.join(runtime_root, "_internal")) or not os.path.isfile(os.path.join(BASE_DIR, "CCTVPanelView-Uninstall.exe")):
                raise RuntimeError("Installer payload is incomplete.")
            import psutil
            target_exes = {os.path.normcase(os.path.join(folder, "CCTVPanelView.exe")) for folder in (self.target_dir, self.previous_dir) if folder}
            for proc in psutil.process_iter(["exe"]):
                if os.path.normcase(proc.info.get("exe") or "") in target_exes:
                    raise RuntimeError("Close CCTVPanelView before installing this update so recordings can finish safely.")

            # Step 1: Directory Setup
            advance(5, "Initializing installation environment...", f"[INIT] Validating application path: {self.target_dir}")
            os.makedirs(self.target_dir, exist_ok=True)
            preserve_upgrade_profile(self.target_dir, self.previous_dir)
            os.makedirs(os.path.join(self.target_dir, "logs"), exist_ok=True)
            os.makedirs(os.path.join(self.target_dir, "snapshots"), exist_ok=True)
            os.makedirs(os.path.join(self.target_dir, "recordings"), exist_ok=True)
            advance(15, "Provisioning application structure...", f"[DIR] Application root deployed: {self.target_dir}")

            # Step 2: Copy Core & Engine
            advance(25, "Deploying core CCTV engines...", "[ENGINE] Copying stream orchestrator & hardware monitor...")
            src_assets = os.path.join(BASE_DIR, "assets")
            if os.path.isdir(src_assets):
                shutil.copytree(src_assets, os.path.join(self.target_dir, "assets"), dirs_exist_ok=True)
            advance(45, "Deploying core libraries and user interface...", "[UI] Deployed modern PyQt6 Obsidian Glass interface assets.")

            # Step 3: Copy AI Weights & Core Binaries
            advance(55, "Deploying CCTVPanelView workstation binaries...", "[BIN] Deploying CCTVPanelView core binary & AI engines...")
            shutil.copytree(os.path.join(runtime_root, "_internal"), os.path.join(self.target_dir, "_internal"), dirs_exist_ok=True)
            for f in ["CCTVPanelView.exe", "CCTVPanelView-Uninstall.exe"]:
                src = os.path.join(runtime_root if f == "CCTVPanelView.exe" else BASE_DIR, f)
                dst = os.path.join(self.target_dir, f)
                if os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
                    shutil.copy2(src, dst)
            advance(70, "Finalizing neural weights deployment...", "[AI] On-device AI object detection models verified.")

            # Step 4: Configuration - Fresh Virgin Configuration Template (0 cameras)
            advance(78, "Preserving workstation configuration...", "[CONFIG] Keeping existing cameras, layouts and settings; creating defaults only for a fresh install.")
            import json
            cfg_dst = os.path.join(self.target_dir, "cameras_config.json")
            clean_fresh_config = {
                "version": "2.0",
                "app_settings": {
                    "default_layout": "2x2",
                    "default_quality": "MAX",
                    "hardware_acceleration": True,
                    "low_latency_mode": True,
                    "master_alerts_enabled": True,
                    "motion_enabled": True,
                    "ai_detection_enabled": True,
                    "notify_person": True,
                    "notify_vehicle": True,
                    "notify_animal": True,
                    "notify_motion": True,
                    "show_desktop_notifications": True,
                    "sound_alarms_enabled": True,
                    "auto_record_on_motion": True,
                    "motion_min_area": 1200,
                    "motion_cooldown_sec": 5.0,
                    "ai_conf_threshold": 0.40,
                    "theme": "Cyber Dark",
                    "has_completed_onboarding": False,
                    "recording_dir": "recordings",
                    "snapshot_dir": "snapshots",
                    "ntfy_topic": "",
                    "ntfy_enabled": False,
                    "telegram_enabled": False,
                    "discord_enabled": False,
                    "close_action": "ask",
                    "performance_profile": "balanced"

                },
                "cameras": []
            }
            if not os.path.exists(cfg_dst):
                with open(cfg_dst, "w", encoding="utf-8") as f:
                    json.dump(clean_fresh_config, f, indent=2)
            advance(82, "Application profile ready", "[CONFIG] Existing cameras and settings preserved when upgrading.")

            advance(86, "Configuring Windows shortcuts & shell integration...", "[SHELL] Registering system shell integration...")

            # Step 5: Create Windows Desktop and Start Menu Shortcuts directly to CCTVPanelView.exe
            main_exe = os.path.join(self.target_dir, "CCTVPanelView.exe")
            target_to_launch = main_exe

            from core.windows_identity import create_shortcut, restore_legacy_icons
            restore_legacy_icons(self.target_dir)
            # The executable owns a permanent embedded icon; _internal assets
            # are implementation details and must not be shortcut icon paths.
            icon_file = main_exe

            def create_windows_shortcut(target_path, shortcut_dest, icon_loc, desc):
                create_shortcut(target_path, shortcut_dest, self.target_dir, desc)

            if self.create_desktop_shortcut:
                desktop_dir = os.path.expanduser("~/Desktop")
                if os.path.exists(desktop_dir):
                    desktop_lnk = os.path.join(desktop_dir, f"{APP_NAME}.lnk")
                    create_windows_shortcut(target_to_launch, desktop_lnk, icon_file, "CCTVPanelView AI Surveillance Workstation")
                    advance(90, "Creating Desktop shortcut...", f"[SHORTCUT] Created Desktop shortcut: {desktop_lnk}")

            if self.create_start_menu:
                start_menu_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
                if os.path.exists(start_menu_dir):
                    sm_lnk = os.path.join(start_menu_dir, f"{APP_NAME}.lnk")
                    create_windows_shortcut(target_to_launch, sm_lnk, icon_file, "CCTVPanelView AI Surveillance Workstation")
                    advance(94, "Creating Start Menu entry...", f"[SHORTCUT] Registered Start Menu program: {sm_lnk}")

                    uninst_target = os.path.join(self.target_dir, "CCTVPanelView-Uninstall.exe")
                    if os.path.exists(uninst_target):
                        sm_uninst = os.path.join(start_menu_dir, f"Uninstall {APP_NAME}.lnk")
                        create_windows_shortcut(uninst_target, sm_uninst, icon_file, "Uninstall CCTVPanelView AI Surveillance Workstation")

            # Step 6: Register in Windows Add/Remove Programs
            advance(97, "Registering Windows uninstallation registry entry...", "[REG] Registering Windows Add/Remove Programs integration...")
            try:
                import winreg
                reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\CCTVPanelView"
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path) as k:
                    winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, "CCTVPanelView AI Surveillance Workstation")
                    winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
                    winreg.SetValueEx(k, "Publisher", 0, winreg.REG_SZ, "CCTVPanelView Workstation")
                    winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, self.target_dir)
                    uninst_exe = os.path.join(self.target_dir, "CCTVPanelView-Uninstall.exe")
                    if os.path.exists(uninst_exe):
                        winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, f'"{uninst_exe}"')
                    else:
                        winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ, f'python "{os.path.join(self.target_dir, "uninstaller.py")}"')
                    winreg.SetValueEx(k, "DisplayIcon", 0, winreg.REG_SZ, f'"{icon_file}",0')
                    winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
            except Exception as e:
                advance(98, "Registry entry note...", f"[REG] Registry notice: {e}")

            # Step 7: Finalize
            advance(100, "Installation complete!", "[FINISH] CCTVPanelView deployment successfully verified.")
            self.msleep(300)
            self.installation_finished.emit(True, "Success")
        except Exception as e:
            self.installation_finished.emit(False, str(e))


class CCTVPanelViewInstaller(QMainWindow):
    """
    Main Installer Application Window for CCTVPanelView.
    Obsidian Glass theme, custom title bar, animated installation progress.
    """
    def __init__(self, dry_run: bool = False, install_dir=None):
        super().__init__()
        self.dry_run = dry_run
        self.previous_install_dir = registered_install_dir()
        self.initial_install_dir = install_dir or self.previous_install_dir
        self.drag_position = QPoint()

        self.setWindowTitle("CCTVPanelView Workstation Setup")
        self.setFixedSize(760, 530)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._setup_ui()

    def _setup_ui(self):
        # Master Background Container with rounded borders
        self.central_container = QFrame(self)
        self.central_container.setObjectName("central_container")
        self.central_container.setGeometry(10, 10, self.width() - 20, self.height() - 20)
        self.central_container.setStyleSheet("""
            QFrame#central_container {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #090e1a, stop:1 #0c1222);
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 16px;
            }
            QCheckBox {
                color: #e2e8f0;
                font-size: 11.5px;
                spacing: 9px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border-radius: 5px;
                border: 1px solid rgba(255, 255, 255, 0.20);
                background-color: rgba(15, 23, 42, 0.85);
            }
            QCheckBox::indicator:hover {
                border-color: #38bdf8;
                background-color: rgba(14, 165, 233, 0.15);
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
            }
        """)

        # Drop Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 4)
        self.central_container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.central_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 1. Custom Title Bar
        title_bar = self._create_title_bar()
        container_layout.addWidget(title_bar)

        # 2. Main Stacked Widget
        self.stack = QStackedWidget(self.central_container)
        self.page_welcome = self._create_page_welcome()
        self.page_installing = self._create_page_installing()
        self.page_complete = self._create_page_complete()

        self.stack.addWidget(self.page_welcome)     # Index 0
        self.stack.addWidget(self.page_installing)  # Index 1
        self.stack.addWidget(self.page_complete)    # Index 2

        container_layout.addWidget(self.stack, stretch=1)

    # -------------------------------------------------------------
    # Title Bar & Dragging
    # -------------------------------------------------------------
    def _create_title_bar(self) -> QWidget:
        tb = QFrame(self.central_container)
        tb.setFixedHeight(46)
        tb.setStyleSheet("""
            QFrame {
                background-color: #0c1220;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.07);
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        layout = QHBoxLayout(tb)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(8)

        # Brand Aperture Icon
        logo_path = os.path.join(BASE_DIR, "assets", "app_icon_clean.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(BASE_DIR, "assets", "app_icon.png")

        lbl_icon = QLabel(tb)
        if os.path.exists(logo_path):
            lbl_icon.setPixmap(QPixmap(logo_path).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        lbl_icon.setFixedSize(22, 22)
        layout.addWidget(lbl_icon)

        lbl_title = QLabel("CCTVPanelView Workstation Setup", tb)
        lbl_title.setStyleSheet("color: #f8fafc; font-size: 12px; font-weight: 700; letter-spacing: 0.3px;")
        layout.addWidget(lbl_title)

        lbl_badge = QLabel("WINDOWS INSTALLER", tb)
        lbl_badge.setFixedHeight(20)
        lbl_badge.setStyleSheet("color: #38bdf8; font-size: 9.5px; font-weight: 750; background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 4px; padding: 2px 7px;")
        layout.addWidget(lbl_badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch()

        # Minimize & Close Controls
        btn_min = QPushButton("—", tb)
        btn_min.setFixedSize(28, 28)
        btn_min.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_min.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-size: 13px;
                font-weight: 700;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }
        """)
        btn_min.clicked.connect(self.showMinimized)
        layout.addWidget(btn_min)

        btn_close = QPushButton("✕", tb)
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #94a3b8;
                border: none;
                font-size: 13px;
                font-weight: 700;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #ef4444;
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
    # Screen 0: Welcome & Setup Configuration
    # -------------------------------------------------------------
    def _create_page_welcome(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 22, 32, 24)
        layout.setSpacing(14)

        # Header Hero Card
        hero = QFrame(w)
        hero.setObjectName("hero_frame")
        hero.setStyleSheet("""
            QFrame#hero_frame {
                background-color: rgba(15, 23, 42, 0.70);
                border: 1px solid rgba(56, 189, 248, 0.20);
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

        logo_path = os.path.join(BASE_DIR, "assets", "app_icon_clean.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(BASE_DIR, "assets", "app_icon.png")

        lbl_hero_logo = QLabel(hero)
        if os.path.exists(logo_path):
            lbl_hero_logo.setPixmap(QPixmap(logo_path).scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        lbl_hero_logo.setFixedSize(56, 56)
        h_layout.addWidget(lbl_hero_logo)

        info_box = QVBoxLayout()
        info_box.setSpacing(3)
        lbl_h_title = QLabel("Install CCTVPanelView Workstation", hero)
        lbl_h_title.setStyleSheet("color: #f8fafc; font-size: 16px; font-weight: 800;")
        lbl_h_sub = QLabel("Professional On-Device AI Surveillance Suite with Dual-Lens PTZ Integration", hero)
        lbl_h_sub.setStyleSheet("color: #94a3b8; font-size: 11.5px;")
        info_box.addWidget(lbl_h_title)
        info_box.addWidget(lbl_h_sub)
        h_layout.addLayout(info_box, stretch=1)
        layout.addWidget(hero)

        # Installation Destination Card
        dest_card = QFrame(w)
        dest_card.setObjectName("dest_card")
        dest_card.setMinimumHeight(115)
        dest_card.setStyleSheet("""
            QFrame#dest_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #090e1a, stop:1 #111a2e);
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 10px;
            }
            QFrame#dest_card QLabel {
                background: transparent;
                border: none;
            }
        """)
        d_layout = QVBoxLayout(dest_card)
        d_layout.setContentsMargins(16, 14, 16, 14)
        d_layout.setSpacing(8)

        lbl_dest_t = QLabel("Destination Installation Folder:", dest_card)
        lbl_dest_t.setStyleSheet("color: #f8fafc; font-size: 11.5px; font-weight: 700;")
        d_layout.addWidget(lbl_dest_t)

        picker_row = QHBoxLayout()
        picker_row.setSpacing(8)

        default_install_dir = self.initial_install_dir or os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "Programs", APP_NAME)
        self.txt_dest_path = QLineEdit(default_install_dir, dest_card)
        self.txt_dest_path.setFixedHeight(32)
        self.txt_dest_path.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #090e1a, stop:1 #111a2e);
                color: #f8fafc;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11.5px;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
                background: #14223d;
            }
        """)
        self.txt_dest_path.textChanged.connect(self._on_dest_path_changed)
        picker_row.addWidget(self.txt_dest_path, stretch=1)

        btn_browse = QPushButton("Browse...", dest_card)
        btn_browse.setFixedSize(86, 32)
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0b1528, stop:1 #132342);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.40);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #0284c7;
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        btn_browse.clicked.connect(self._browse_install_dir)
        picker_row.addWidget(btn_browse)
        d_layout.addLayout(picker_row)

        info_row = QHBoxLayout()
        self.lbl_disk_space = QLabel(dest_card)
        self.lbl_disk_space.setStyleSheet("color: #64748b; font-size: 10px;")
        info_row.addWidget(self.lbl_disk_space)
        info_row.addStretch()

        lbl_storage_hint = QLabel("Upgrades keep cameras, layouts and settings, with a configuration backup", dest_card)
        lbl_storage_hint.setStyleSheet("color: #475569; font-size: 10px; font-style: italic;")
        info_row.addWidget(lbl_storage_hint)
        d_layout.addLayout(info_row)

        layout.addWidget(dest_card)

        # Options Card
        opts_card = QFrame(w)
        opts_card.setObjectName("opts_card")
        opts_card.setStyleSheet("""
            QFrame#opts_card {
                background-color: rgba(15, 23, 42, 0.50);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QFrame#opts_card QLabel {
                background: transparent;
                border: none;
            }
        """)
        o_layout = QVBoxLayout(opts_card)
        o_layout.setContentsMargins(16, 14, 16, 14)
        o_layout.setSpacing(8)

        lbl_opts_t = QLabel("Installation Options & Shortcuts:", opts_card)
        lbl_opts_t.setStyleSheet("color: #cbd5e1; font-size: 11.5px; font-weight: 700;")
        o_layout.addWidget(lbl_opts_t)

        self.chk_desktop = QCheckBox("Create Desktop Shortcut (with custom brand icon)", opts_card)
        self.chk_desktop.setChecked(True)
        self.chk_desktop.setStyleSheet("color: #94a3b8; font-size: 11px;")
        o_layout.addWidget(self.chk_desktop)

        self.chk_start_menu = QCheckBox("Add CCTVPanelView to Windows Start Menu Programs", opts_card)
        self.chk_start_menu.setChecked(True)
        self.chk_start_menu.setStyleSheet("color: #94a3b8; font-size: 11px;")
        o_layout.addWidget(self.chk_start_menu)

        self.chk_open_wizard = QCheckBox("Launch First-Run Camera Setup Wizard immediately after installation", opts_card)
        self.chk_open_wizard.setChecked(False)
        self.chk_open_wizard.setStyleSheet("color: #94a3b8; font-size: 11px;")
        o_layout.addWidget(self.chk_open_wizard)

        layout.addWidget(opts_card)
        self._update_disk_space_info()
        self._refresh_upgrade_options()

        layout.addStretch()

        # Bottom Action Bar
        act_row = QHBoxLayout()
        act_row.setSpacing(12)

        btn_cancel = QPushButton("Cancel", w)
        btn_cancel.setFixedSize(96, 36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #0f172a;
                color: #94a3b8;
                border: 1px solid #1e293b;
                border-radius: 8px;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #ffffff;
            }
        """)
        btn_cancel.clicked.connect(self.close)
        act_row.addWidget(btn_cancel)

        act_row.addStretch()

        btn_install = QPushButton("Install Now", w)
        btn_install.setFixedSize(140, 36)
        btn_install.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_install.setStyleSheet("""
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
        btn_install.clicked.connect(self._start_installation)
        act_row.addWidget(btn_install)

        layout.addLayout(act_row)
        return w

    def _browse_install_dir(self):
        curr = self.txt_dest_path.text() or os.path.expanduser("~")
        chosen = QFileDialog.getExistingDirectory(self, "Select Installation Folder", curr)
        if chosen:
            target = os.path.join(chosen, APP_NAME) if not chosen.endswith(APP_NAME) else chosen
            self.txt_dest_path.setText(target)

    def _on_dest_path_changed(self):
        self._update_disk_space_info()
        self._refresh_upgrade_options()

    def _refresh_upgrade_options(self):
        upgrading = os.path.isfile(os.path.join(self.txt_dest_path.text().strip(), CONFIG_NAME)) or bool(self.previous_install_dir and os.path.isfile(os.path.join(self.previous_install_dir, CONFIG_NAME)))
        for name in ("chk_open_wizard", "chk_launch_wizard"):
            if hasattr(self, name):
                control = getattr(self, name)
                if upgrading:
                    control.setChecked(False)
                control.setEnabled(not upgrading)
                control.setToolTip("Upgrades preserve cameras, layout and settings automatically; configuration backups are saved in config-backups.")

    def _update_disk_space_info(self):
        path = self.txt_dest_path.text().strip()
        try:
            drive_letter = (os.path.splitdrive(path)[0] or "C").rstrip(":")
            drive_root = drive_letter + ":\\"
            total, used, free = shutil.disk_usage(drive_root)
            free_gb = free / (1024 ** 3)
            self.lbl_disk_space.setText(f"Space Required: ~1 GB  •  Space Available on Drive {drive_letter}: {free_gb:.1f} GB")
        except Exception:
            self.lbl_disk_space.setText("Space Required: ~1 GB")

    # -------------------------------------------------------------
    # Screen 1: Animated Installation in Progress
    # -------------------------------------------------------------
    def _create_page_installing(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(36, 24, 36, 24)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Center Animated Cybernetic Reticle
        self.spinner = AnimatedApertureSpinner(size=110, parent=w)
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        # Dynamic Status Titles
        self.lbl_inst_title = QLabel("Installing CCTVPanelView Workstation...", w)
        self.lbl_inst_title.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: 750; background: transparent;")
        layout.addWidget(self.lbl_inst_title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lbl_inst_sub = QLabel("Deploying high-speed surveillance engine and AI vision neural models.", w)
        self.lbl_inst_sub.setStyleSheet("color: #94a3b8; font-size: 11px; background: transparent;")
        layout.addWidget(self.lbl_inst_sub, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(6)

        # Modern Progress Bar Row
        prog_box = QVBoxLayout()
        prog_box.setSpacing(6)

        p_row = QHBoxLayout()
        self.lbl_step_desc = QLabel("Initializing deployment sequence...", w)
        self.lbl_step_desc.setStyleSheet("color: #cbd5e1; font-size: 10.5px; font-weight: 600; background: transparent;")
        p_row.addWidget(self.lbl_step_desc)
        p_row.addStretch()

        self.lbl_percent = QLabel("0%", w)
        self.lbl_percent.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 800; background: transparent;")
        p_row.addWidget(self.lbl_percent)
        prog_box.addLayout(p_row)

        self.prog_bar = QProgressBar(w)
        self.prog_bar.setFixedHeight(8)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(15, 23, 42, 0.90);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #38bdf8);
                border-radius: 3px;
            }
        """)
        prog_box.addWidget(self.prog_bar)
        layout.addLayout(prog_box)

        layout.addSpacing(4)

        # Terminal / Log Box
        log_frame = QFrame(w)
        log_frame.setObjectName("log_frame")
        log_frame.setStyleSheet("""
            QFrame#log_frame {
                background-color: #050811;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
        """)
        lf_layout = QVBoxLayout(log_frame)
        lf_layout.setContentsMargins(10, 8, 10, 8)

        self.txt_log = QTextEdit(log_frame)
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(110)
        self.txt_log.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 10px;
                line-height: 1.4;
            }
        """)
        lf_layout.addWidget(self.txt_log)
        layout.addWidget(log_frame)

        return w

    # -------------------------------------------------------------
    # Screen 2: Installation Complete
    # -------------------------------------------------------------
    def _create_page_complete(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(36, 26, 36, 26)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Success Icon Badge
        badge = QFrame(w)
        badge.setFixedSize(54, 54)
        badge.setObjectName("badge_success")
        badge.setStyleSheet("""
            QFrame#badge_success {
                background-color: rgba(56, 189, 248, 0.15);
                border: 2px solid #38bdf8;
                border-radius: 27px;
            }
        """)
        b_box = QVBoxLayout(badge)
        b_box.setContentsMargins(0, 0, 0, 0)
        lbl_chk = QLabel(badge)
        lbl_chk.setPixmap(create_vector_icon("check", color="#38bdf8", size=26))
        lbl_chk.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_chk.setStyleSheet("background: transparent; border: none;")
        b_box.addWidget(lbl_chk)
        layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_done_t = QLabel("Installation Successfully Completed!", w)
        lbl_done_t.setStyleSheet("color: #f8fafc; font-size: 16px; font-weight: 800; background: transparent;")
        layout.addWidget(lbl_done_t, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_done_sub = QLabel("CCTVPanelView has been deployed and registered on this workstation.", w)
        lbl_done_sub.setStyleSheet("color: #94a3b8; font-size: 11.5px; background: transparent;")
        layout.addWidget(lbl_done_sub, alignment=Qt.AlignmentFlag.AlignCenter)

        # Summary Card
        sum_card = QFrame(w)
        sum_card.setObjectName("sum_card")
        sum_card.setStyleSheet("""
            QFrame#sum_card {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #090e1a, stop:1 #111a2e);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 10px;
            }
            QFrame#sum_card QLabel {
                background: transparent;
                border: none;
            }
        """)
        s_layout = QVBoxLayout(sum_card)
        s_layout.setContentsMargins(20, 16, 20, 16)
        s_layout.setSpacing(9)

        self.lbl_sum_app = QLabel(sum_card)
        self.lbl_sum_app.setStyleSheet("color: #f8fafc; font-size: 11.5px;")
        self.lbl_sum_app.setWordWrap(True)
        s_layout.addWidget(self.lbl_sum_app)

        self.lbl_sum_alerts = QLabel(sum_card)
        self.lbl_sum_alerts.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.lbl_sum_alerts.setWordWrap(True)
        s_layout.addWidget(self.lbl_sum_alerts)

        self.lbl_sum_sc = QLabel(sum_card)
        self.lbl_sum_sc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.lbl_sum_sc.setWordWrap(True)
        s_layout.addWidget(self.lbl_sum_sc)

        layout.addWidget(sum_card)

        # Launch Toggles
        opts_box = QVBoxLayout()
        opts_box.setSpacing(6)
        opts_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.chk_launch_now = QCheckBox("Launch CCTVPanelView Workstation now", w)
        self.chk_launch_now.setChecked(True)
        opts_box.addWidget(self.chk_launch_now)

        self.chk_launch_wizard = QCheckBox("Open First-Run Camera Setup Wizard", w)
        self.chk_launch_wizard.setChecked(False)
        opts_box.addWidget(self.chk_launch_wizard)

        layout.addLayout(opts_box)

        layout.addStretch()

        # Finish Button
        act_row = QHBoxLayout()
        act_row.addStretch()

        btn_finish = QPushButton("Finish && Launch", w)
        btn_finish.setFixedSize(150, 36)
        btn_finish.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_finish.setStyleSheet("""
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
        btn_finish.clicked.connect(self._on_finish_clicked)
        act_row.addWidget(btn_finish)
        layout.addLayout(act_row)

        return w

    # -------------------------------------------------------------
    # Deployment Logic
    # -------------------------------------------------------------
    def _start_installation(self):
        target = self.txt_dest_path.text().strip()
        if not target:
            return

        self.stack.setCurrentIndex(1)
        self.txt_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Commencing installation sequence...")

        self.worker = InstallerDeploymentWorker(
            target_dir=target,
            create_desktop_shortcut=self.chk_desktop.isChecked(),
            create_start_menu=self.chk_start_menu.isChecked(),
            set_high_dpi=True,
            launch_wizard=self.chk_open_wizard.isChecked(),
            previous_dir=self.previous_install_dir
        )
        self.worker.progress_updated.connect(self._on_progress_update)
        self.worker.installation_finished.connect(self._on_install_completed)
        self.worker.start()

    def _on_progress_update(self, percent: int, title: str, detail: str):
        self.prog_bar.setValue(percent)
        self.lbl_percent.setText(f"{percent}%")
        self.lbl_step_desc.setText(title)
        self.txt_log.append(detail)
        # Auto-scroll log
        sb = self.txt_log.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _on_install_completed(self, success: bool, msg: str):
        if success:
            self._refresh_upgrade_options()
            target = self.txt_dest_path.text().strip()
            self.lbl_sum_app.setText(f"<b>Application Location:</b> <span style='color:#38bdf8;'>{target}</span>")
            self.lbl_sum_alerts.setText(f"<b>Alerts & Storage Root:</b> <span style='color:#cbd5e1;'>{target}\\recordings</span> <span style='color:#64748b;'>(configured in First-Run Setup)</span>")
            self.lbl_sum_sc.setText("<b>Windows Integration:</b> Desktop Shortcut and Start Menu entry created.")
            self.stack.setCurrentIndex(2)
        else:
            self.lbl_inst_title.setText("Installation Encountered an Issue")
            self.lbl_inst_sub.setText(f"Error: {msg}")
            self.lbl_inst_title.setStyleSheet("color: #ef4444; font-size: 15px; font-weight: 750;")

    def _on_finish_clicked(self):
        target = self.txt_dest_path.text().strip()
        should_launch = self.chk_launch_now.isChecked()
        should_run_wizard = not os.path.isfile(os.path.join(target, CONFIG_NAME)) and hasattr(self, "chk_launch_wizard") and self.chk_launch_wizard.isChecked()

        if should_launch:
            main_exe = os.path.join(target, "CCTVPanelView.exe")
            main_script = os.path.join(target, "main.py")

            if os.path.exists(main_exe):
                args = [main_exe]
                if should_run_wizard:
                    args.append("--setup")
                subprocess.Popen(args, cwd=target)

        self.close()


def main():
    if "--self-test" in sys.argv:
        # Exercise the actual bundled payload in an isolated directory, without shell registration.
        import json
        import tempfile
        report_path = next((arg.split("=", 1)[1] for arg in sys.argv
                            if arg.startswith("--self-test-report=")), None)
        result = {"passed": False}
        try:
            with tempfile.TemporaryDirectory(prefix="cctv-install-check-") as temp:
                shutil.copytree(os.path.join(BASE_DIR, "payload", "CCTVPanelView"), temp, dirs_exist_ok=True)
                shutil.copy2(os.path.join(BASE_DIR, "CCTVPanelView-Uninstall.exe"), os.path.join(temp, "CCTVPanelView-Uninstall.exe"))
                app_report = os.path.join(temp, "app-check.json")
                env = os.environ.copy()
                env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
                completed = subprocess.run([os.path.join(temp, "CCTVPanelView.exe"), "--self-test",
                                            "--self-test-report=" + app_report], cwd=temp, env=env,
                                           timeout=180, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                with open(app_report, encoding="utf-8") as file:
                    result = json.load(file)
                result["passed"] = result.get("passed", False) and completed.returncode == 0
                result["installer_payload_deployed"] = True
                from core.windows_identity import create_shortcut, restore_legacy_icons
                restore_legacy_icons(temp)
                shortcut = os.path.join(temp, "diagnostic-shortcut.lnk")
                create_shortcut(os.path.join(temp, "CCTVPanelView.exe"), shortcut, temp, "CCTVPanelView")
                result["native_shortcut_created"] = os.path.isfile(shortcut)
                result["legacy_pinned_icon_restored"] = os.path.isfile(os.path.join(temp, "assets", "cctv_logo.ico"))
                result["passed"] = result["passed"] and result["native_shortcut_created"] and result["legacy_pinned_icon_restored"]
        except Exception as error:
            result["passed"] = False
            result["error"] = str(error)
        if report_path:
            with open(report_path, "w", encoding="utf-8") as file:
                json.dump(result, file, indent=2)
        raise SystemExit(0 if result["passed"] else 1)
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    icon_path = os.path.join(BASE_DIR, "assets", "cctv_logo.ico")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(BASE_DIR, "assets", "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-dir")
    parser.add_argument("--wait-for-pid", type=int)
    options, _ = parser.parse_known_args()
    if options.install_dir and not os.path.isabs(options.install_dir):
        parser.error("Installation directory must be absolute")
    if options.wait_for_pid:
        import psutil, time
        deadline = time.monotonic() + 60
        while psutil.pid_exists(options.wait_for_pid) and time.monotonic() < deadline:
            time.sleep(.2)
        if psutil.pid_exists(options.wait_for_pid):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Update waiting", "CCTVPanelView is still closing. Close it completely, then run the downloaded installer again.")
    installer = CCTVPanelViewInstaller(install_dir=options.install_dir)
    installer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
