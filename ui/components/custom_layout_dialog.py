import os
import json
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QGridLayout, QGroupBox, QFrame, QScrollArea, QWidget, QMessageBox, QSpinBox,
    QSizePolicy, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QCursor


STARTER_TEMPLATES = {
    "Quad (2x2 Grid)": {
        "rows": 2, "cols": 2,
        "windows": [
            {"r": 0, "c": 0, "rspan": 1, "cspan": 1, "desc": "Top Left"},
            {"r": 0, "c": 1, "rspan": 1, "cspan": 1, "desc": "Top Right"},
            {"r": 1, "c": 0, "rspan": 1, "cspan": 1, "desc": "Bottom Left"},
            {"r": 1, "c": 1, "rspan": 1, "cspan": 1, "desc": "Bottom Right"},
        ]
    },
    "Hero Left + 2 Stacked Right": {
        "rows": 2, "cols": 2,
        "windows": [
            {"r": 0, "c": 0, "rspan": 2, "cspan": 1, "desc": "Hero Main (Left)"},
            {"r": 0, "c": 1, "rspan": 1, "cspan": 1, "desc": "Top Right"},
            {"r": 1, "c": 1, "rspan": 1, "cspan": 1, "desc": "Bottom Right"},
        ]
    },
    "Hero Left + 3 Stacked Right": {
        "rows": 3, "cols": 3,
        "windows": [
            {"r": 0, "c": 0, "rspan": 3, "cspan": 2, "desc": "Hero Large (Left)"},
            {"r": 0, "c": 2, "rspan": 1, "cspan": 1, "desc": "Top Right"},
            {"r": 1, "c": 2, "rspan": 1, "cspan": 1, "desc": "Middle Right"},
            {"r": 2, "c": 2, "rspan": 1, "cspan": 1, "desc": "Bottom Right"},
        ]
    },
    "Wide Top (Panoramic) + 3 Bottom": {
        "rows": 4, "cols": 3,
        "windows": [
            {"r": 0, "c": 0, "rspan": 2, "cspan": 3, "desc": "Wide Panoramic Top"},
            {"r": 2, "c": 0, "rspan": 2, "cspan": 1, "desc": "Bottom Left"},
            {"r": 2, "c": 1, "rspan": 2, "cspan": 1, "desc": "Bottom Center"},
            {"r": 2, "c": 2, "rspan": 2, "cspan": 1, "desc": "Bottom Right"},
        ]
    },
    "Surveillance Center (1 Large + 5 Small)": {
        "rows": 3, "cols": 3,
        "windows": [
            {"r": 0, "c": 0, "rspan": 2, "cspan": 2, "desc": "Hero Center"},
            {"r": 0, "c": 2, "rspan": 1, "cspan": 1, "desc": "Top Right"},
            {"r": 1, "c": 2, "rspan": 1, "cspan": 1, "desc": "Center Right"},
            {"r": 2, "c": 0, "rspan": 1, "cspan": 1, "desc": "Bottom Left"},
            {"r": 2, "c": 1, "rspan": 1, "cspan": 1, "desc": "Bottom Mid"},
            {"r": 2, "c": 2, "rspan": 1, "cspan": 1, "desc": "Bottom Right"},
        ]
    },
    "Dual-Lens Side-by-Side (2x1)": {
        "rows": 1, "cols": 2,
        "windows": [
            {"r": 0, "c": 0, "rspan": 1, "cspan": 1, "desc": "Lens 1 (Left)"},
            {"r": 0, "c": 1, "rspan": 1, "cspan": 1, "desc": "Lens 2 (Right)"},
        ]
    },
    "Triple Panoramic (3x1)": {
        "rows": 1, "cols": 3,
        "windows": [
            {"r": 0, "c": 0, "rspan": 1, "cspan": 1, "desc": "Camera 1 (Left)"},
            {"r": 0, "c": 1, "rspan": 1, "cspan": 1, "desc": "Camera 2 (Center)"},
            {"r": 0, "c": 2, "rspan": 1, "cspan": 1, "desc": "Camera 3 (Right)"},
        ]
    },
    "3x3 Grid (9 Windows)": {
        "rows": 3, "cols": 3,
        "windows": [
            {"r": 0, "c": 0, "rspan": 1, "cspan": 1, "desc": "Top Left"},
            {"r": 0, "c": 1, "rspan": 1, "cspan": 1, "desc": "Top Mid"},
            {"r": 0, "c": 2, "rspan": 1, "cspan": 1, "desc": "Top Right"},
            {"r": 1, "c": 0, "rspan": 1, "cspan": 1, "desc": "Mid Left"},
            {"r": 1, "c": 1, "rspan": 1, "cspan": 1, "desc": "Center"},
            {"r": 1, "c": 2, "rspan": 1, "cspan": 1, "desc": "Mid Right"},
            {"r": 2, "c": 0, "rspan": 1, "cspan": 1, "desc": "Bottom Left"},
            {"r": 2, "c": 1, "rspan": 1, "cspan": 1, "desc": "Bottom Mid"},
            {"r": 2, "c": 2, "rspan": 1, "cspan": 1, "desc": "Bottom Right"},
        ]
    },
    "Blank Canvas (Build from Scratch)": {
        "rows": 4, "cols": 4,
        "windows": []
    }
}


class CanvasWindowCard(QFrame):
    """
    Interactive window block rendered directly on the surveillance screen canvas.
    Displays window index, assigned camera, dimension chips, and direct action buttons.
    """
    clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)
    resize_clicked = pyqtSignal(int, int, int)   # win_id, delta_w, delta_h
    move_clicked = pyqtSignal(int, int, int)     # win_id, delta_r, delta_c

    def __init__(self, win_data: dict, is_selected: bool = False, camera_label: str = "Empty", parent=None):
        super().__init__(parent)
        self.win_id = win_data["id"]
        self.win_data = win_data
        self.is_selected = is_selected
        self.camera_label = camera_label
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.win_id)
        super().mousePressEvent(event)

    def _setup_ui(self):
        self.setObjectName("canvas_card")
        border_color = "#00e5ff" if self.is_selected else ("#2563eb" if self.win_data.get("stream_id") else "#334155")
        bg_color = "rgba(0, 229, 255, 0.09)" if self.is_selected else "#0e1726"
        border_width = "2px" if self.is_selected else "1px"

        self.setStyleSheet(f"""
            QFrame#canvas_card {{
                background-color: {bg_color};
                border: {border_width} solid {border_color};
                border-radius: 6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header Bar: Title + Camera Badge + Delete Button
        header = QHBoxLayout()
        header.setSpacing(4)

        lbl_title = QLabel(f"WINDOW #{self.win_id + 1}")
        lbl_title.setStyleSheet(f"font-weight: 800; font-size: 10px; color: {'#00e5ff' if self.is_selected else '#38bdf8'};")
        header.addWidget(lbl_title)

        header.addStretch()

        btn_del = QPushButton("X", self)
        btn_del.setFixedSize(18, 18)
        btn_del.setToolTip("Delete this window")
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                font-weight: 800;
                font-size: 10px;
                border: 1px solid #7f1d1d;
                border-radius: 3px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #dc2626;
                color: #ffffff;
            }
        """)
        btn_del.clicked.connect(lambda: self.delete_clicked.emit(self.win_id))
        header.addWidget(btn_del)
        layout.addLayout(header)

        # Camera Name Label
        is_assigned = bool(self.win_data.get("stream_id"))
        lbl_cam = QLabel(self.camera_label)
        lbl_cam.setStyleSheet(f"""
            font-size: 10px;
            font-weight: {'700' if is_assigned else '500'};
            color: {'#38bdf8' if is_assigned else '#64748b'};
            background-color: {'rgba(56, 189, 248, 0.12)' if is_assigned else 'rgba(100, 116, 139, 0.1)'};
            border-radius: 3px;
            padding: 2px 4px;
        """)
        lbl_cam.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_cam)

        # Center: Geometry Info
        info_row = QHBoxLayout()
        info_row.setSpacing(4)

        lbl_dim = QLabel(f"Size: {self.win_data['cspan']}w x {self.win_data['rspan']}h")
        lbl_dim.setStyleSheet("font-size: 9px; font-weight: 700; color: #cbd5e1;")
        info_row.addWidget(lbl_dim)

        info_row.addStretch()

        lbl_pos = QLabel(f"Pos: ({self.win_data['r']},{self.win_data['c']})")
        lbl_pos.setStyleSheet("font-size: 9px; color: #94a3b8;")
        info_row.addWidget(lbl_pos)
        layout.addLayout(info_row)

        layout.addStretch()

        # Bottom Quick Controls Bar (Wider / Taller / Move)
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(3)

        btn_style = """
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                font-size: 9px;
                font-weight: 700;
                border: 1px solid #334155;
                border-radius: 3px;
                min-width: 18px;
                max-width: 26px;
                height: 18px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #2563eb;
                border-color: #60a5fa;
                color: #ffffff;
            }
        """

        # Width
        btn_wm = QPushButton("-W", self)
        btn_wm.setStyleSheet(btn_style)
        btn_wm.setToolTip("Make narrower (decrease columns)")
        btn_wm.clicked.connect(lambda: self.resize_clicked.emit(self.win_id, -1, 0))
        ctrl_bar.addWidget(btn_wm)

        btn_wp = QPushButton("+W", self)
        btn_wp.setStyleSheet(btn_style)
        btn_wp.setToolTip("Make wider (increase columns)")
        btn_wp.clicked.connect(lambda: self.resize_clicked.emit(self.win_id, 1, 0))
        ctrl_bar.addWidget(btn_wp)

        # Height
        btn_hm = QPushButton("-H", self)
        btn_hm.setStyleSheet(btn_style)
        btn_hm.setToolTip("Make shorter (decrease rows)")
        btn_hm.clicked.connect(lambda: self.resize_clicked.emit(self.win_id, 0, -1))
        ctrl_bar.addWidget(btn_hm)

        btn_hp = QPushButton("+H", self)
        btn_hp.setStyleSheet(btn_style)
        btn_hp.setToolTip("Make taller (increase rows)")
        btn_hp.clicked.connect(lambda: self.resize_clicked.emit(self.win_id, 0, 1))
        ctrl_bar.addWidget(btn_hp)

        ctrl_bar.addStretch()

        # Directional arrows
        btn_up = QPushButton("^", self)
        btn_up.setStyleSheet(btn_style)
        btn_up.setToolTip("Move Up")
        btn_up.clicked.connect(lambda: self.move_clicked.emit(self.win_id, -1, 0))
        ctrl_bar.addWidget(btn_up)

        btn_down = QPushButton("v", self)
        btn_down.setStyleSheet(btn_style)
        btn_down.setToolTip("Move Down")
        btn_down.clicked.connect(lambda: self.move_clicked.emit(self.win_id, 1, 0))
        ctrl_bar.addWidget(btn_down)

        btn_left = QPushButton("<", self)
        btn_left.setStyleSheet(btn_style)
        btn_left.setToolTip("Move Left")
        btn_left.clicked.connect(lambda: self.move_clicked.emit(self.win_id, 0, -1))
        ctrl_bar.addWidget(btn_left)

        btn_right = QPushButton(">", self)
        btn_right.setStyleSheet(btn_style)
        btn_right.setToolTip("Move Right")
        btn_right.clicked.connect(lambda: self.move_clicked.emit(self.win_id, 0, 1))
        ctrl_bar.addWidget(btn_right)

        layout.addLayout(ctrl_bar)


class CustomLayoutDialog(QDialog):
    """
    True Custom Camera Layout Studio:
    Gives operator complete freedom to design surveillance viewport windows however they want.
    - Freely add, remove, resize (width & height), position, split, and duplicate camera windows.
    - Real-time interactive screen canvas.
    - Precision grid resolution selector (2x2 up to 6x6).
    - Instant starting templates that can be molded and customized at will.
    - Clean Save & Apply button.
    """

    layout_applied = pyqtSignal(dict)

    def __init__(self, available_streams: List[Dict[str, Any]], current_config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.available_streams = available_streams
        self.current_config = current_config or {}
        self.setWindowTitle("Custom Camera Layout Studio")

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        icon_path = os.path.join(base_dir, "assets", "cctv_logo.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_dir, "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1080, 720)
        self.setMinimumSize(880, 580)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        # Core layout model state
        self.grid_rows = 4
        self.grid_cols = 4
        self.windows: List[Dict[str, Any]] = []
        self.selected_win_id: Optional[int] = None

        self._setup_ui()
        self._load_initial_state()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #f1f5f9;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 12px;
                background: transparent;
                border: none;
            }
            QGroupBox {
                border: 1px solid #1e293b;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: 700;
                color: #38bdf8;
                background-color: #111827;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 600;
            }
            QComboBox:hover {
                border-color: #38bdf8;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #f8fafc;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
                border: 1px solid #334155;
                padding: 4px;
            }
            QSpinBox {
                background-color: #162032;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 3px 6px;
                font-size: 12px;
                font-weight: 800;
                min-height: 24px;
            }
            QSpinBox:focus {
                border-color: #00e5ff;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                font-weight: 700;
                font-size: 11px;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 24px;
            }
            QPushButton:hover {
                background-color: #27354a;
                border-color: #38bdf8;
            }
            QPushButton#btn_apply {
                background-color: #1d72f2;
                color: #ffffff;
                border: 1px solid #3b82f6;
                border-radius: 6px;
                font-weight: 700;
                font-size: 13px;
                padding: 7px 22px;
            }
            QPushButton#btn_apply:hover {
                background-color: #1b64d4;
                border-color: #60a5fa;
            }
            QPushButton#btn_add {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #0369a1;
            }
            QPushButton#btn_add:hover {
                background-color: #0369a1;
                border-color: #38bdf8;
            }
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

        # 1. Header Title & Subtitle
        header_row = QHBoxLayout()
        header_v = QVBoxLayout()
        header_v.setSpacing(2)

        lbl_header = QLabel("Custom Camera Layout Studio")
        lbl_header.setStyleSheet("font-size: 17px; font-weight: 800; color: #f8fafc;")
        lbl_sub = QLabel("Make your surveillance windows however you want: freely resize, position, add, split, and arrange feeds.")
        lbl_sub.setStyleSheet("font-size: 11px; color: #94a3b8;")
        header_v.addWidget(lbl_header)
        header_v.addWidget(lbl_sub)
        header_row.addLayout(header_v, stretch=1)
        root_layout.addLayout(header_row)

        # 2. Studio Master Toolbar
        tb_frame = QFrame(self)
        tb_frame.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        tb_layout = QHBoxLayout(tb_frame)
        tb_layout.setContentsMargins(10, 6, 10, 6)
        tb_layout.setSpacing(10)

        btn_add = QPushButton("+ Add Window", tb_frame)
        btn_add.setObjectName("btn_add")
        btn_add.setToolTip("Add a new camera window to the layout")
        btn_add.clicked.connect(self._add_window)
        tb_layout.addWidget(btn_add)

        tb_layout.addWidget(QLabel("Preset:"))
        self.cmb_template = QComboBox(tb_frame)
        for t_name in STARTER_TEMPLATES.keys():
            self.cmb_template.addItem(t_name)
        self.cmb_template.currentTextChanged.connect(self._on_template_selected)
        tb_layout.addWidget(self.cmb_template)

        tb_layout.addWidget(QLabel("Grid Precision:"))
        self.cmb_grid_res = QComboBox(tb_frame)
        self.cmb_grid_res.addItem("2x2 (Simple 4-Cell)", 2)
        self.cmb_grid_res.addItem("3x3 (Standard 9-Cell)", 3)
        self.cmb_grid_res.addItem("4x4 (High-Precision 16-Cell)", 4)
        self.cmb_grid_res.addItem("6x6 (Ultra-Precision 36-Cell)", 6)
        self.cmb_grid_res.setCurrentIndex(2) # Default 4x4
        self.cmb_grid_res.currentIndexChanged.connect(self._on_grid_res_changed)
        tb_layout.addWidget(self.cmb_grid_res)

        tb_layout.addStretch()

        btn_autofill = QPushButton("Auto-Fill Cameras", tb_frame)
        btn_autofill.setToolTip("Automatically assign available camera feeds to windows")
        btn_autofill.clicked.connect(self._autofill_cameras)
        tb_layout.addWidget(btn_autofill)

        btn_clear = QPushButton("Clear Canvas", tb_frame)
        btn_clear.setToolTip("Remove all windows and start from a blank canvas")
        btn_clear.clicked.connect(self._clear_canvas)
        tb_layout.addWidget(btn_clear)

        root_layout.addWidget(tb_frame)

        # 3. Main Workspace Splitter: Left Interactive Screen Canvas, Right Window Inspector
        workspace = QHBoxLayout()
        workspace.setSpacing(12)

        # Left: Interactive Screen Canvas Area
        canvas_group = QGroupBox("Interactive Surveillance Screen Canvas", self)
        canvas_group_lay = QVBoxLayout(canvas_group)
        canvas_group_lay.setContentsMargins(8, 12, 8, 8)

        self.canvas_scroll = QScrollArea(canvas_group)
        self.canvas_scroll.setWidgetResizable(True)
        self.canvas_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.canvas_container = QWidget()
        self.canvas_container.setStyleSheet("background-color: #080c14; border: 1px dashed #1e293b; border-radius: 6px;")
        self.canvas_layout = QGridLayout(self.canvas_container)
        self.canvas_layout.setContentsMargins(8, 8, 8, 8)
        self.canvas_layout.setSpacing(6)
        self.canvas_scroll.setWidget(self.canvas_container)

        canvas_group_lay.addWidget(self.canvas_scroll, stretch=1)
        workspace.addWidget(canvas_group, stretch=3)

        # Right: Selected Window Inspector & Properties Panel
        self.inspector_group = QGroupBox("Selected Window Inspector", self)
        self.inspector_group.setFixedWidth(340)
        group_lay = QVBoxLayout(self.inspector_group)
        group_lay.setContentsMargins(4, 12, 4, 4)

        insp_scroll = QScrollArea(self.inspector_group)
        insp_scroll.setWidgetResizable(True)
        insp_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        insp_container = QWidget()
        insp_lay = QVBoxLayout(insp_container)
        insp_lay.setContentsMargins(8, 4, 8, 8)
        insp_lay.setSpacing(8)
        insp_scroll.setWidget(insp_container)
        group_lay.addWidget(insp_scroll)

        self.lbl_insp_title = QLabel("Select a window on the canvas")
        self.lbl_insp_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #38bdf8;")
        insp_lay.addWidget(self.lbl_insp_title)

        # Camera selector
        lbl_cam_src = QLabel("Camera Feed:")
        lbl_cam_src.setStyleSheet("font-weight: 700; color: #cbd5e1;")
        insp_lay.addWidget(lbl_cam_src)

        self.cmb_stream_assign = QComboBox(self.inspector_group)
        self.cmb_stream_assign.currentIndexChanged.connect(self._on_inspector_stream_changed)
        insp_lay.addWidget(self.cmb_stream_assign)

        # Position (Col, Row)
        pos_row = QHBoxLayout()
        pos_row.setSpacing(8)

        col_v = QVBoxLayout()
        col_v.addWidget(QLabel("Column (X):"))
        self.spin_col = QSpinBox(self.inspector_group)
        self.spin_col.setRange(0, 10)
        self.spin_col.valueChanged.connect(self._on_inspector_coord_changed)
        col_v.addWidget(self.spin_col)
        pos_row.addLayout(col_v)

        row_v = QVBoxLayout()
        row_v.addWidget(QLabel("Row (Y):"))
        self.spin_row = QSpinBox(self.inspector_group)
        self.spin_row.setRange(0, 10)
        self.spin_row.valueChanged.connect(self._on_inspector_coord_changed)
        row_v.addWidget(self.spin_row)
        pos_row.addLayout(row_v)
        insp_lay.addLayout(pos_row)

        # Size (Width Span, Height Span)
        size_row = QHBoxLayout()
        size_row.setSpacing(8)

        w_v = QVBoxLayout()
        w_v.addWidget(QLabel("Width Span (Cols):"))
        self.spin_wspan = QSpinBox(self.inspector_group)
        self.spin_wspan.setRange(1, 10)
        self.spin_wspan.valueChanged.connect(self._on_inspector_size_changed)
        w_v.addWidget(self.spin_wspan)
        size_row.addLayout(w_v)

        h_v = QVBoxLayout()
        h_v.addWidget(QLabel("Height Span (Rows):"))
        self.spin_hspan = QSpinBox(self.inspector_group)
        self.spin_hspan.setRange(1, 10)
        self.spin_hspan.valueChanged.connect(self._on_inspector_size_changed)
        h_v.addWidget(self.spin_hspan)
        size_row.addLayout(h_v)
        insp_lay.addLayout(size_row)

        # Quick Sizing Presets
        lbl_quick_size = QLabel("Quick Dimensions:")
        lbl_quick_size.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11px; margin-top: 4px;")
        insp_lay.addWidget(lbl_quick_size)

        btn_grid_quick = QGridLayout()
        btn_grid_quick.setSpacing(6)

        btn_full_w = QPushButton("Full Width", self.inspector_group)
        btn_full_w.setToolTip("Expand window to occupy full width")
        btn_full_w.setFixedHeight(28)
        btn_full_w.clicked.connect(self._set_selected_full_width)
        btn_grid_quick.addWidget(btn_full_w, 0, 0)

        btn_full_h = QPushButton("Full Height", self.inspector_group)
        btn_full_h.setToolTip("Expand window to occupy full height")
        btn_full_h.setFixedHeight(28)
        btn_full_h.clicked.connect(self._set_selected_full_height)
        btn_grid_quick.addWidget(btn_full_h, 0, 1)

        btn_hero_2x2 = QPushButton("Hero (2x2)", self.inspector_group)
        btn_hero_2x2.setFixedHeight(28)
        btn_hero_2x2.clicked.connect(lambda: self._set_selected_size(2, 2))
        btn_grid_quick.addWidget(btn_hero_2x2, 1, 0)

        btn_std_1x1 = QPushButton("Compact (1x1)", self.inspector_group)
        btn_std_1x1.setFixedHeight(28)
        btn_std_1x1.clicked.connect(lambda: self._set_selected_size(1, 1))
        btn_grid_quick.addWidget(btn_std_1x1, 1, 1)
        insp_lay.addLayout(btn_grid_quick)

        # Window Splitting Tools
        lbl_split = QLabel("Window Operations:")
        lbl_split.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11px; margin-top: 4px;")
        insp_lay.addWidget(lbl_split)

        btn_split_h = QPushButton("Split Horizontal", self.inspector_group)
        btn_split_h.setFixedHeight(28)
        btn_split_h.setToolTip("Cut this window into two side-by-side windows")
        btn_split_h.clicked.connect(self._split_selected_horizontal)
        insp_lay.addWidget(btn_split_h)

        btn_split_v = QPushButton("Split Vertical", self.inspector_group)
        btn_split_v.setFixedHeight(28)
        btn_split_v.setToolTip("Cut this window into two top/bottom windows")
        btn_split_v.clicked.connect(self._split_selected_vertical)
        insp_lay.addWidget(btn_split_v)

        btn_dup = QPushButton("Duplicate Window", self.inspector_group)
        btn_dup.setFixedHeight(28)
        btn_dup.setToolTip("Clone window dimensions and camera feed")
        btn_dup.clicked.connect(self._duplicate_selected_window)
        insp_lay.addWidget(btn_dup)

        btn_del_sel = QPushButton("Delete Window", self.inspector_group)
        btn_del_sel.setFixedHeight(28)
        btn_del_sel.setStyleSheet("""
            QPushButton {
                background-color: #450a0a;
                color: #fca5a5;
                border: 1px solid #7f1d1d;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #991b1b;
                color: #ffffff;
            }
        """)
        btn_del_sel.clicked.connect(self._delete_selected_window)
        insp_lay.addWidget(btn_del_sel)

        insp_lay.addStretch()

        # Telemetry Summary
        self.lbl_telemetry = QLabel("0 Windows Active")
        self.lbl_telemetry.setStyleSheet("font-size: 10px; color: #64748b; font-weight: 600;")
        insp_lay.addWidget(self.lbl_telemetry)

        workspace.addWidget(self.inspector_group, stretch=1)
        root_layout.addLayout(workspace, stretch=1)

        # 4. Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.lbl_canvas_summary = QLabel("Ready to apply layout.")
        self.lbl_canvas_summary.setStyleSheet("font-size: 11px; color: #94a3b8;")
        bottom_bar.addWidget(self.lbl_canvas_summary)

        bottom_bar.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.clicked.connect(self.reject)
        bottom_bar.addWidget(btn_cancel)

        self.btn_apply = QPushButton("Save && Apply", self)
        self.btn_apply.setObjectName("btn_apply")
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        bottom_bar.addWidget(self.btn_apply)

        root_layout.addLayout(bottom_bar)

    def _populate_stream_dropdown(self):
        self.cmb_stream_assign.blockSignals(True)
        self.cmb_stream_assign.clear()
        self.cmb_stream_assign.addItem("(Empty Slot)", "")
        for s in self.available_streams:
            s_name = s.get("name", "Stream")
            cam_name = s.get("camera_name", "Camera")
            label = f"{cam_name} • {s_name}"
            self.cmb_stream_assign.addItem(label, s.get("id"))
        self.cmb_stream_assign.blockSignals(False)

    def _get_stream_label(self, stream_id: str) -> str:
        if not stream_id:
            return "Empty"
        for s in self.available_streams:
            if s.get("id") == stream_id:
                c_name = s.get("camera_name", "Camera")
                l_name = s.get("name", "Stream")
                return f"{c_name} • {l_name}"
        return "Camera Feed"

    def _load_initial_state(self):
        self._populate_stream_dropdown()

        saved = self.current_config or {}
        saved_slots = saved.get("slots", [])
        saved_assignments = saved.get("assignments", [])
        self.grid_rows = max(1, saved.get("rows", 4))
        self.grid_cols = max(1, saved.get("cols", 4))

        # Match grid precision combo
        for i in range(self.cmb_grid_res.count()):
            if self.cmb_grid_res.itemData(i) == self.grid_rows and self.cmb_grid_res.itemData(i) == self.grid_cols:
                self.cmb_grid_res.blockSignals(True)
                self.cmb_grid_res.setCurrentIndex(i)
                self.cmb_grid_res.blockSignals(False)
                break

        if saved_slots:
            self.windows = []
            for idx, slot in enumerate(saved_slots):
                sid = saved_assignments[idx] if idx < len(saved_assignments) else ""
                self.windows.append({
                    "id": idx,
                    "r": slot.get("r", 0),
                    "c": slot.get("c", 0),
                    "rspan": max(1, slot.get("rspan", 1)),
                    "cspan": max(1, slot.get("cspan", 1)),
                    "stream_id": sid,
                    "desc": slot.get("desc", f"Window #{idx + 1}")
                })
        else:
            # Default to 2x2 quad
            self._load_template("Quad (2x2 Grid)")

        if self.windows:
            self.selected_win_id = self.windows[0]["id"]
        self._render_canvas()

    def _load_template(self, template_name: str):
        tmpl = STARTER_TEMPLATES.get(template_name)
        if not tmpl:
            return

        self.grid_rows = tmpl["rows"]
        self.grid_cols = tmpl["cols"]

        # Match grid precision combo
        for i in range(self.cmb_grid_res.count()):
            if self.cmb_grid_res.itemData(i) == self.grid_rows and self.cmb_grid_res.itemData(i) == self.grid_cols:
                self.cmb_grid_res.blockSignals(True)
                self.cmb_grid_res.setCurrentIndex(i)
                self.cmb_grid_res.blockSignals(False)
                break

        self.windows = []
        for idx, win in enumerate(tmpl["windows"]):
            sid = self.available_streams[idx].get("id") if idx < len(self.available_streams) else ""
            self.windows.append({
                "id": idx,
                "r": win["r"],
                "c": win["c"],
                "rspan": win["rspan"],
                "cspan": win["cspan"],
                "stream_id": sid,
                "desc": win.get("desc", f"Window #{idx + 1}")
            })

        self.selected_win_id = self.windows[0]["id"] if self.windows else None
        self._render_canvas()

    def _on_template_selected(self, text: str):
        if text:
            self._load_template(text)

    def _on_grid_res_changed(self, idx: int):
        val = self.cmb_grid_res.itemData(idx)
        if val:
            self.grid_rows = val
            self.grid_cols = val
            self._clamp_all_windows()
            self._render_canvas()

    def _clamp_all_windows(self):
        for win in self.windows:
            win["r"] = max(0, min(win["r"], self.grid_rows - 1))
            win["c"] = max(0, min(win["c"], self.grid_cols - 1))
            win["rspan"] = max(1, min(win["rspan"], self.grid_rows - win["r"]))
            win["cspan"] = max(1, min(win["cspan"], self.grid_cols - win["c"]))

    def _render_canvas(self):
        # Clear layout
        while self.canvas_layout.count() > 0:
            item = self.canvas_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for r_reset in range(16):
            self.canvas_layout.setRowStretch(r_reset, 0)
        for c_reset in range(16):
            self.canvas_layout.setColumnStretch(c_reset, 0)

        # Empty state
        if not self.windows:
            lbl_empty = QLabel("Canvas is empty.\nClick '+ Add Window' or select a starting preset above to design your layout.")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("font-size: 13px; font-weight: 600; color: #64748b; padding: 40px;")
            self.canvas_layout.addWidget(lbl_empty, 0, 0, 1, 1)
            self._sync_inspector()
            self._update_telemetry()
            return

        # Render window cards
        for win in self.windows:
            win_id = win["id"]
            is_sel = (win_id == self.selected_win_id)
            cam_label = self._get_stream_label(win.get("stream_id", ""))

            card = CanvasWindowCard(win, is_selected=is_sel, camera_label=cam_label, parent=self.canvas_container)
            card.clicked.connect(self._select_window)
            card.delete_clicked.connect(self._delete_window_by_id)
            card.resize_clicked.connect(self._resize_window_by_id)
            card.move_clicked.connect(self._move_window_by_id)

            r = win["r"]
            c = win["c"]
            rspan = win["rspan"]
            cspan = win["cspan"]
            self.canvas_layout.addWidget(card, r, c, rspan, cspan)

        # Equal stretches for crisp visual aspect ratios
        for r in range(self.grid_rows):
            self.canvas_layout.setRowStretch(r, 1)
        for c in range(self.grid_cols):
            self.canvas_layout.setColumnStretch(c, 1)

        self._sync_inspector()
        self._update_telemetry()

    def _select_window(self, win_id: int):
        self.selected_win_id = win_id
        self._render_canvas()

    def _sync_inspector(self):
        sel_win = self._get_selected_window()
        if not sel_win:
            self.lbl_insp_title.setText("No Window Selected")
            self.cmb_stream_assign.setEnabled(False)
            self.spin_col.setEnabled(False)
            self.spin_row.setEnabled(False)
            self.spin_wspan.setEnabled(False)
            self.spin_hspan.setEnabled(False)
            return

        self.cmb_stream_assign.setEnabled(True)
        self.spin_col.setEnabled(True)
        self.spin_row.setEnabled(True)
        self.spin_wspan.setEnabled(True)
        self.spin_hspan.setEnabled(True)

        self.lbl_insp_title.setText(f"Window #{sel_win['id'] + 1} Properties")

        # Stream combo
        sid = sel_win.get("stream_id", "")
        self.cmb_stream_assign.blockSignals(True)
        c_idx = self.cmb_stream_assign.findData(sid)
        if c_idx >= 0:
            self.cmb_stream_assign.setCurrentIndex(c_idx)
        else:
            self.cmb_stream_assign.setCurrentIndex(0)
        self.cmb_stream_assign.blockSignals(False)

        # Bounds
        self.spin_col.blockSignals(True)
        self.spin_row.blockSignals(True)
        self.spin_wspan.blockSignals(True)
        self.spin_hspan.blockSignals(True)

        self.spin_col.setMaximum(self.grid_cols - 1)
        self.spin_row.setMaximum(self.grid_rows - 1)
        self.spin_wspan.setMaximum(self.grid_cols)
        self.spin_hspan.setMaximum(self.grid_rows)

        self.spin_col.setValue(sel_win["c"])
        self.spin_row.setValue(sel_win["r"])
        self.spin_wspan.setValue(sel_win["cspan"])
        self.spin_hspan.setValue(sel_win["rspan"])

        self.spin_col.blockSignals(False)
        self.spin_row.blockSignals(False)
        self.spin_wspan.blockSignals(False)
        self.spin_hspan.blockSignals(False)

    def _update_telemetry(self):
        count = len(self.windows)
        assigned = sum(1 for w in self.windows if w.get("stream_id"))
        self.lbl_telemetry.setText(f"{count} Windows Active • {assigned}/{count} Feeds Assigned")
        self.lbl_canvas_summary.setText(f"Layout Architecture: {self.grid_cols}x{self.grid_rows} Grid • {count} active viewport windows ready.")

    def _get_selected_window(self) -> Optional[Dict[str, Any]]:
        if self.selected_win_id is None:
            return None
        for w in self.windows:
            if w["id"] == self.selected_win_id:
                return w
        return None

    def _add_window(self):
        if len(self.windows) >= 16:
            QMessageBox.information(self, "Limit Reached", "A maximum of 16 simultaneous viewport windows is supported.")
            return

        new_id = len(self.windows)

        # Pick first available stream not yet assigned
        used_sids = {w.get("stream_id") for w in self.windows if w.get("stream_id")}
        next_sid = ""
        for s in self.available_streams:
            if s.get("id") not in used_sids:
                next_sid = s.get("id")
                break

        # Find best open slot
        pos_r, pos_c = 0, 0
        occupied_cells = {(w["r"], w["c"]) for w in self.windows}
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                if (r, c) not in occupied_cells:
                    pos_r, pos_c = r, c
                    break
            else:
                continue
            break

        new_win = {
            "id": new_id,
            "r": pos_r,
            "c": pos_c,
            "rspan": 1,
            "cspan": 1,
            "stream_id": next_sid,
            "desc": f"Window #{new_id + 1}"
        }
        self.windows.append(new_win)
        self.selected_win_id = new_id
        self._render_canvas()

    def _delete_window_by_id(self, win_id: int):
        self.windows = [w for w in self.windows if w["id"] != win_id]
        # Re-index
        for idx, w in enumerate(self.windows):
            w["id"] = idx
            w["desc"] = f"Window #{idx + 1}"

        if self.selected_win_id == win_id or self.selected_win_id >= len(self.windows):
            self.selected_win_id = self.windows[0]["id"] if self.windows else None

        self._render_canvas()

    def _delete_selected_window(self):
        if self.selected_win_id is not None:
            self._delete_window_by_id(self.selected_win_id)

    def _resize_window_by_id(self, win_id: int, delta_w: int, delta_h: int):
        for w in self.windows:
            if w["id"] == win_id:
                w["cspan"] = max(1, min(self.grid_cols - w["c"], w["cspan"] + delta_w))
                w["rspan"] = max(1, min(self.grid_rows - w["r"], w["rspan"] + delta_h))
                break
        self.selected_win_id = win_id
        self._render_canvas()

    def _move_window_by_id(self, win_id: int, delta_r: int, delta_c: int):
        for w in self.windows:
            if w["id"] == win_id:
                w["r"] = max(0, min(self.grid_rows - w["rspan"], w["r"] + delta_r))
                w["c"] = max(0, min(self.grid_cols - w["cspan"], w["c"] + delta_c))
                break
        self.selected_win_id = win_id
        self._render_canvas()

    def _on_inspector_coord_changed(self):
        sel = self._get_selected_window()
        if not sel:
            return
        sel["c"] = self.spin_col.value()
        sel["r"] = self.spin_row.value()
        self._clamp_all_windows()
        self._render_canvas()

    def _on_inspector_size_changed(self):
        sel = self._get_selected_window()
        if not sel:
            return
        sel["cspan"] = self.spin_wspan.value()
        sel["rspan"] = self.spin_hspan.value()
        self._clamp_all_windows()
        self._render_canvas()

    def _on_inspector_stream_changed(self):
        sel = self._get_selected_window()
        if not sel:
            return
        sel["stream_id"] = self.cmb_stream_assign.currentData() or ""
        self._render_canvas()

    def _set_selected_full_width(self):
        sel = self._get_selected_window()
        if not sel:
            return
        sel["c"] = 0
        sel["cspan"] = self.grid_cols
        self._render_canvas()

    def _set_selected_full_height(self):
        sel = self._get_selected_window()
        if not sel:
            return
        sel["r"] = 0
        sel["rspan"] = self.grid_rows
        self._render_canvas()

    def _set_selected_size(self, w: int, h: int):
        sel = self._get_selected_window()
        if not sel:
            return
        sel["cspan"] = min(self.grid_cols - sel["c"], w)
        sel["rspan"] = min(self.grid_rows - sel["r"], h)
        self._render_canvas()

    def _split_selected_horizontal(self):
        sel = self._get_selected_window()
        if not sel or len(self.windows) >= 16:
            return

        if sel["cspan"] < 2:
            # Expand grid resolution if necessary
            if self.grid_cols < 6:
                self.grid_cols = min(6, self.grid_cols * 2)
                for w in self.windows:
                    w["c"] *= 2
                    w["cspan"] *= 2
            else:
                return

        half = sel["cspan"] // 2
        rem = sel["cspan"] - half
        sel["cspan"] = half

        new_id = len(self.windows)
        new_win = {
            "id": new_id,
            "r": sel["r"],
            "c": sel["c"] + half,
            "rspan": sel["rspan"],
            "cspan": rem,
            "stream_id": "",
            "desc": f"Window #{new_id + 1}"
        }
        self.windows.append(new_win)
        self.selected_win_id = new_id
        self._render_canvas()

    def _split_selected_vertical(self):
        sel = self._get_selected_window()
        if not sel or len(self.windows) >= 16:
            return

        if sel["rspan"] < 2:
            if self.grid_rows < 6:
                self.grid_rows = min(6, self.grid_rows * 2)
                for w in self.windows:
                    w["r"] *= 2
                    w["rspan"] *= 2
            else:
                return

        half = sel["rspan"] // 2
        rem = sel["rspan"] - half
        sel["rspan"] = half

        new_id = len(self.windows)
        new_win = {
            "id": new_id,
            "r": sel["r"] + half,
            "c": sel["c"],
            "rspan": rem,
            "cspan": sel["cspan"],
            "stream_id": "",
            "desc": f"Window #{new_id + 1}"
        }
        self.windows.append(new_win)
        self.selected_win_id = new_id
        self._render_canvas()

    def _duplicate_selected_window(self):
        sel = self._get_selected_window()
        if not sel or len(self.windows) >= 16:
            return

        new_id = len(self.windows)
        new_r = min(self.grid_rows - sel["rspan"], sel["r"] + 1)
        new_c = min(self.grid_cols - sel["cspan"], sel["c"] + 1)

        new_win = {
            "id": new_id,
            "r": new_r,
            "c": new_c,
            "rspan": sel["rspan"],
            "cspan": sel["cspan"],
            "stream_id": sel.get("stream_id", ""),
            "desc": f"Window #{new_id + 1}"
        }
        self.windows.append(new_win)
        self.selected_win_id = new_id
        self._render_canvas()

    def _autofill_cameras(self):
        for idx, win in enumerate(self.windows):
            if idx < len(self.available_streams):
                win["stream_id"] = self.available_streams[idx].get("id", "")
            else:
                win["stream_id"] = ""
        self._render_canvas()

    def _clear_canvas(self):
        self.windows = []
        self.selected_win_id = None
        self._render_canvas()

    def _on_apply_clicked(self):
        if not self.windows:
            QMessageBox.warning(self, "Empty Layout", "Please add at least one camera window before applying.")
            return

        slots = []
        assignments = []
        for idx, win in enumerate(self.windows):
            slots.append({
                "slot": idx,
                "r": win["r"],
                "c": win["c"],
                "rspan": win["rspan"],
                "cspan": win["cspan"],
                "desc": win.get("desc", f"Window #{idx + 1}")
            })
            assignments.append(win.get("stream_id", ""))

        result = {
            "template_name": "Custom",
            "rows": self.grid_rows,
            "cols": self.grid_cols,
            "slots": slots,
            "assignments": assignments
        }
        self.accept()
        self.layout_applied.emit(result)
