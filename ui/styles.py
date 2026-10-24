"""
Ultra-Modern Multi-Theme Stylesheet Engine for Cam720 Revamped / CCTVPanelView.
Clean, professional desktop surveillance studio aesthetics:
- Crisp 4px-6px radii on all interactive elements (NO pill shapes or capsule buttons)
- Refined, cohesive color palettes (neutral zinc/slate bases, modern accents)
- Multi-Theme Support:
  * Slate Modern (Refined Slate Dark & Modern Sapphire - Default)
  * Onyx Minimal (Deep OLED Pitch Black & Titanium)
  * Midnight Navy (Deep Aerospace Navy & Cyan)
  * Nordic Light (Clean, Professional White & Slate Light Theme)
  * Tactical Charcoal (Warm Gunmetal & Graphite)
"""

THEMES = {
    "Slate Modern": {
        "is_light": False,
        "bg_base": "#101114",
        "bg_surface": "#16171d",
        "bg_card": "#1d1f27",
        "bg_input": "#14151a",
        "border_color": "#282a35",
        "border_focus": "#3b82f6",
        "text_primary": "#f3f4f6",
        "text_secondary": "#9ca3af",
        "text_muted": "#64748b",
        "accent_primary": "#2563eb",
        "accent_secondary": "#3b82f6",
        "accent_glow": "#60a5fa",
        "selection_bg": "#2563eb",
        "selection_fg": "#ffffff",
        "tile_selected_border": "#3b82f6",
        "badge_live_bg": "rgba(56, 189, 248, 0.16)",
        "badge_live_fg": "#38bdf8",
        "badge_live_bd": "#0284c7",
    },
    "Onyx Minimal": {
        "is_light": False,
        "bg_base": "#09090b",
        "bg_surface": "#121215",
        "bg_card": "#18181c",
        "bg_input": "#0e0e11",
        "border_color": "#242428",
        "border_focus": "#3b82f6",
        "text_primary": "#fafafa",
        "text_secondary": "#a1a1aa",
        "text_muted": "#71717a",
        "accent_primary": "#2563eb",
        "accent_secondary": "#3b82f6",
        "accent_glow": "#60a5fa",
        "selection_bg": "#2563eb",
        "selection_fg": "#ffffff",
        "tile_selected_border": "#3b82f6",
        "badge_live_bg": "rgba(56, 189, 248, 0.16)",
        "badge_live_fg": "#38bdf8",
        "badge_live_bd": "#0284c7",
    },
    "Midnight Navy": {
        "is_light": False,
        "bg_base": "#090d16",
        "bg_surface": "#0f1624",
        "bg_card": "#151e30",
        "bg_input": "#0b101c",
        "border_color": "#1e293b",
        "border_focus": "#0284c7",
        "text_primary": "#f0f6fc",
        "text_secondary": "#8fa3bf",
        "text_muted": "#5e7392",
        "accent_primary": "#0284c7",
        "accent_secondary": "#0ea5e9",
        "accent_glow": "#38bdf8",
        "selection_bg": "#0284c7",
        "selection_fg": "#ffffff",
        "tile_selected_border": "#0ea5e9",
        "badge_live_bg": "rgba(14, 165, 233, 0.16)",
        "badge_live_fg": "#38bdf8",
        "badge_live_bd": "#0284c7",
    },
    "Nordic Light": {
        "is_light": True,
        "bg_base": "#f8fafc",
        "bg_surface": "#ffffff",
        "bg_card": "#f1f5f9",
        "bg_input": "#ffffff",
        "border_color": "#e2e8f0",
        "border_focus": "#2563eb",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "text_muted": "#94a3b8",
        "accent_primary": "#2563eb",
        "accent_secondary": "#3b82f6",
        "accent_glow": "#1d4ed8",
        "selection_bg": "#dbeafe",
        "selection_fg": "#1e3a8a",
        "tile_selected_border": "#2563eb",
        "badge_live_bg": "rgba(2, 132, 199, 0.15)",
        "badge_live_fg": "#0284c7",
        "badge_live_bd": "#38bdf8",
    },
    "Tactical Charcoal": {
        "is_light": False,
        "bg_base": "#121316",
        "bg_surface": "#18191e",
        "bg_card": "#202228",
        "bg_input": "#141519",
        "border_color": "#282a32",
        "border_focus": "#3b82f6",
        "text_primary": "#f3f4f6",
        "text_secondary": "#9ca3af",
        "text_muted": "#6b7280",
        "accent_primary": "#2563eb",
        "accent_secondary": "#3b82f6",
        "accent_glow": "#60a5fa",
        "selection_bg": "#2563eb",
        "selection_fg": "#ffffff",
        "tile_selected_border": "#60a5fa",
        "badge_live_bg": "rgba(56, 189, 248, 0.16)",
        "badge_live_fg": "#38bdf8",
        "badge_live_bd": "#0284c7",
    }
}

AVAILABLE_THEMES = list(THEMES.keys())


def build_theme_qss(colors: dict) -> str:
    """Generates a cohesive, modern QSS stylesheet from a color palette dictionary."""
    is_light = colors.get("is_light", False)
    btn_specular = "rgba(0, 0, 0, 0.04)" if is_light else "rgba(255, 255, 255, 0.05)"
    item_hover_bg = "rgba(0, 0, 0, 0.05)" if is_light else colors['bg_card']

    return f"""
/* Global Reset & Base Typography */
QWidget {{
    background-color: {colors['bg_base']};
    color: {colors['text_primary']};
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", "Helvetica Neue", sans-serif;
    font-size: 13px;
    selection-background-color: {colors['selection_bg']};
    selection-color: {colors['selection_fg']};
}}

MainWindow {{
    background: transparent;
}}

#central_widget {{
    background: transparent;
}}

QSplitter {{
    background: transparent;
}}

/* Scrollbars - Sleek Minimal Modern Design */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {colors['border_color']};
    min-height: 28px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: {colors['accent_secondary']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: transparent;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 6px;
    margin: 0px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {colors['border_color']};
    min-width: 28px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {colors['accent_secondary']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: transparent;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* Tooltips */
QToolTip {{
    background-color: {colors['bg_surface']};
    color: {colors['text_primary']};
    border: 1px solid {colors['border_color']};
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 11px;
}}

/* Push Buttons - Clean Modern Surfaces (No Pill Shapes) */
QPushButton {{
    background-color: {colors['bg_surface']};
    color: {colors['text_primary']};
    border: 1px solid {colors['border_color']};
    border-top: 1px solid {btn_specular};
    border-radius: 5px;
    padding: 5px 12px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: {colors['bg_card']};
    border-color: {colors['border_focus']};
    color: {colors['text_primary']};
}}
QPushButton:pressed {{
    background-color: {colors['bg_base']};
    border-color: {colors['accent_primary']};
}}
QPushButton:checked {{
    background-color: {colors['accent_primary']};
    border: 1px solid {colors['accent_secondary']};
    color: #ffffff;
    font-weight: 700;
}}
QPushButton:disabled {{
    background-color: {colors['bg_base']};
    color: {colors['text_muted']};
    border-color: {colors['border_color']};
    opacity: 0.5;
}}

/* Primary Action Buttons */
QPushButton.primary-btn, QPushButton[class="primary-btn"] {{
    background-color: {colors['accent_primary']};
    color: #ffffff;
    border: 1px solid {colors['accent_secondary']};
    border-radius: 5px;
    font-weight: 700;
    padding: 5px 14px;
}}
QPushButton.primary-btn:hover, QPushButton[class="primary-btn"]:hover {{
    background-color: {colors['accent_secondary']};
    border-color: {colors['accent_glow']};
    color: #ffffff;
}}
QPushButton.primary-btn:pressed, QPushButton[class="primary-btn"]:pressed {{
    background-color: {colors['accent_primary']};
}}

/* Danger Action Buttons */
QPushButton.danger-btn, QPushButton[class="danger-btn"] {{
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #ef4444;
    border-radius: 5px;
    font-weight: 700;
    padding: 5px 12px;
}}
QPushButton.danger-btn:hover, QPushButton[class="danger-btn"]:hover {{
    background-color: #b91c1c;
    border-color: #f87171;
}}

/* Inputs & Form Controls */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {colors['bg_input']};
    color: {colors['text_primary']};
    border: 1px solid {colors['border_color']};
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 12px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {colors['border_focus']};
    background-color: {colors['bg_surface']};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid {colors['border_color']};
}}
QComboBox QAbstractItemView {{
    background-color: {colors['bg_surface']};
    color: {colors['text_primary']};
    border: 1px solid {colors['border_color']};
    selection-background-color: {colors['selection_bg']};
    selection-color: {colors['selection_fg']};
    padding: 4px;
    outline: none;
    border-radius: 4px;
}}

/* CheckBoxes */
QCheckBox {{
    color: {colors['text_primary']};
    font-size: 12px;
    spacing: 7px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {colors['border_color']};
    border-radius: 4px;
    background-color: {colors['bg_input']};
}}
QCheckBox::indicator:hover {{
    border-color: {colors['border_focus']};
}}
QCheckBox::indicator:checked {{
    background-color: {colors['accent_primary']};
    border-color: {colors['accent_secondary']};
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='white'><path d='M13.485 3.515a1 1 0 0 1 0 1.414l-7 7a1 1 0 0 1-1.414 0l-3.5-3.5a1 1 0 0 1 1.414-1.414L6.07 10.1l6.001-6.001a1 1 0 0 1 1.414 0z'/></svg>");
}}

/* Group Boxes - Modern Structured Containers */
QGroupBox {{
    font-weight: 700;
    font-size: 12px;
    color: {colors['text_primary']};
    border: 1px solid {colors['border_color']};
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 14px;
    padding-bottom: 8px;
    padding-left: 8px;
    padding-right: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    color: {colors['accent_secondary']};
}}

/* Splitter Grips */
QSplitter::handle:horizontal {{
    background-color: {colors['border_color']};
    width: 7px;
    margin: 0px;
    border-left: 1px solid rgba(255, 255, 255, 0.04);
    border-right: 1px solid rgba(0, 0, 0, 0.15);
}}
QSplitter::handle:horizontal:hover {{
    background-color: {colors['accent_secondary']};
}}

/* Top Navigation Bar - Modern Apple Glass & Windows 11 Fluent System */
#top_bar {{
    background-color: #080c16;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    min-height: 74px;
    max-height: 84px;
}}
QFrame.top-bar-capsule, #top_bar QFrame[class="top-bar-capsule"] {{
    background-color: rgba(15, 23, 42, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px;
}}
QFrame.top-bar-capsule:hover {{
    background-color: rgba(15, 23, 42, 0.90);
    border-color: rgba(255, 255, 255, 0.20);
}}
#top_bar QPushButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 13px;
    color: #cbd5e1;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    min-height: 26px;
}}
#top_bar QPushButton:hover {{
    background-color: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.16);
    color: #ffffff;
}}
#top_bar QPushButton:pressed {{
    background-color: rgba(255, 255, 255, 0.22);
}}
#top_bar QPushButton:checked {{
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    color: #ffffff;
    font-weight: 700;
}}
#top_bar QComboBox {{
    padding: 3px 6px;
    font-size: 11px;
    border-radius: 6px;
}}
.grid-layout-btn, QPushButton[class="grid-layout-btn"] {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 13px;
    color: #94a3b8;
    font-weight: 600;
    font-size: 11px;
    padding: 3px 8px;
    min-width: 26px;
}}
.grid-layout-btn:hover, QPushButton[class="grid-layout-btn"]:hover {{
    background-color: rgba(255, 255, 255, 0.10);
    color: #f1f5f9;
}}
.grid-layout-btn:checked, QPushButton[class="grid-layout-btn"]:checked {{
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    color: #ffffff;
    font-weight: 700;
}}

/* Left / Right Dockable Sidebar */
#left_sidebar {{
    background-color: {colors['bg_surface']};
    border-right: 1px solid {colors['border_color']};
    border-left: 1px solid {colors['border_color']};
    min-width: 0px;
    max-width: 1400px;
    border-radius: 6px;
}}

/* Section Titles */
QLabel.section-title {{
    color: {colors['text_secondary']};
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding-top: 4px;
    padding-bottom: 2px;
}}

/* Video Tile Frames */
QFrame.video-tile {{
    background-color: #000000;
    border: 1px solid {colors['border_color']};
    border-radius: 6px;
}}
QFrame.video-tile-selected {{
    background-color: #000000;
    border: 2px solid {colors['tile_selected_border']};
    border-radius: 6px;
}}

/* Tree & List Widgets */
QTreeWidget, QListWidget {{
    background-color: transparent;
    border: none;
    color: {colors['text_primary']};
    font-size: 12px;
}}
QTreeWidget::item, QListWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
    margin: 1px 2px;
}}
QTreeWidget::item:hover, QListWidget::item:hover {{
    background-color: {item_hover_bg};
    color: {colors['text_primary']};
}}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {colors['selection_bg']};
    color: {colors['selection_fg']};
    font-weight: 700;
}}

/* Settings Navigation Sidebar (Apple Vision Studio style) */
QListWidget#settings_sidebar {{
    background-color: {colors['bg_surface']};
    border: none;
    border-right: 1px solid {colors['border_color']};
    outline: none;
    padding: 14px 8px 10px 8px;
}}
QListWidget#settings_sidebar::item {{
    color: {colors['text_secondary']};
    font-weight: 600;
    font-size: 12px;
    padding: 10px 14px;
    border-radius: 8px;
    margin-bottom: 4px;
    border: 1px solid transparent;
}}
QListWidget#settings_sidebar::item:hover:!selected {{
    background-color: {item_hover_bg};
    color: {colors['text_primary']};
}}
QListWidget#settings_sidebar::item:selected {{
    background-color: rgba(56, 189, 248, 0.14);
    border: 1px solid rgba(56, 189, 248, 0.40);
    color: #ffffff;
    font-weight: 700;
}}

/* Tab Widgets - Clean Modern Line Style (No Round Pills) */
QTabWidget::pane {{
    border: 1px solid {colors['border_color']};
    background-color: {colors['bg_surface']};
    border-radius: 6px;
}}
QTabBar::tab {{
    background-color: {colors['bg_base']};
    color: {colors['text_secondary']};
    border: 1px solid {colors['border_color']};
    border-bottom: none;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-weight: 600;
}}
QTabBar::tab:hover {{
    color: {colors['text_primary']};
    background-color: {colors['bg_surface']};
}}
QTabBar::tab:selected {{
    background-color: {colors['bg_surface']};
    color: {colors['accent_secondary']};
    font-weight: 700;
    border-top: 2px solid {colors['accent_secondary']};
}}

/* Sidebar Modern Segmented Tab Bar (Apple macOS / Windows 11 Fluent) */
#side_tabs::pane {{
    border: none;
    background-color: transparent;
    margin-top: 8px;
}}
#side_tabs QTabBar {{
    background-color: #090b10;
    border: 1px solid #1a1e2b;
    border-radius: 8px;
    padding: 3px;
    qproperty-expanding: true;
}}
#side_tabs QTabBar::tab {{
    background: transparent;
    color: #94a3b8;
    padding: 7px 6px;
    font-weight: 600;
    font-size: 11px;
    border: none;
    border-radius: 6px;
    margin: 1px;
    text-align: center;
}}
#side_tabs QTabBar::tab:hover {{
    color: #f1f5f9;
    background-color: rgba(255, 255, 255, 0.04);
}}
#side_tabs QTabBar::tab:selected {{
    background-color: #1d2538;
    color: #38bdf8;
    border: 1px solid #2d3b5b;
    font-weight: 700;
}}

/* Camera Tree Modern Card Items (Windows 11 / Apple Smart Device List) */
QTreeWidget#cam_tree {{
    background-color: transparent;
    border: none;
    outline: none;
    padding: 0px;
}}
QTreeWidget#cam_tree::item {{
    height: 34px;
    background-color: #0f121a;
    border: 1px solid #1b1e2a;
    border-radius: 6px;
    color: #f1f5f9;
    font-size: 11px;
    font-weight: 600;
    padding-left: 8px;
    padding-right: 8px;
    margin-top: 2px;
    margin-bottom: 2px;
}}
QTreeWidget#cam_tree::item:hover {{
    background-color: #151924;
    border-color: #262c3e;
    color: #ffffff;
}}
QTreeWidget#cam_tree::item:selected {{
    background-color: rgba(37, 99, 235, 0.20);
    border: 1px solid #3b82f6;
    color: #ffffff;
    font-weight: 700;
}}
QTreeWidget#cam_tree::branch {{
    background: transparent;
}}

/* Sidebar System Overview Card - Windows 11 / Apple Control Widget */
QFrame#sidebar_info_card {{
    background-color: #090b10;
    border: 1px solid #1a1e2b;
    border-radius: 8px;
    padding: 10px 12px;
}}
QProgressBar#sidebar_storage_bar {{
    background-color: #141722;
    border: 1px solid #1f2536;
    border-radius: 3px;
    height: 5px;
    text-align: right;
}}
QProgressBar#sidebar_storage_bar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #38bdf8);
    border-radius: 2px;
}}

/* Sliders - Clean Linear Track */
QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {colors['border_color']};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {colors['accent_primary']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {colors['accent_secondary']};
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 3px;
}}
QSlider::handle:horizontal:hover {{
    background: #ffffff;
}}

/* Status Badges - Clean Rectangles with 4px Radii (NO Pills) */
QLabel.badge-live {{
    background-color: {colors['badge_live_bg']};
    color: {colors['badge_live_fg']};
    border: 1px solid {colors['badge_live_bd']};
    border-radius: 4px;
    padding: 2px 6px;
    font-weight: 700;
    font-size: 11px;
}}
QLabel.badge-connecting {{
    background-color: rgba(245, 158, 11, 0.18);
    color: #fbbf24;
    border: 1px solid #d97706;
    border-radius: 4px;
    padding: 2px 6px;
    font-weight: 700;
    font-size: 11px;
}}
QLabel.badge-error {{
    background-color: rgba(239, 68, 68, 0.18);
    color: #f87171;
    border: 1px solid #dc2626;
    border-radius: 4px;
    padding: 2px 6px;
    font-weight: 700;
    font-size: 11px;
}}
"""


def get_theme_qss(theme_name: str) -> str:
    """Returns QSS string for the specified theme name, falling back to Slate Modern."""
    name_map = {
        "slate modern": "Slate Modern",
        "slate_modern": "Slate Modern",
        "slate": "Slate Modern",
        "cyber dark": "Slate Modern",
        "cyber_dark": "Slate Modern",
        "dark_cyber": "Slate Modern",
        "stealth obsidian": "Onyx Minimal",
        "stealth_obsidian": "Onyx Minimal",
        "obsidian": "Onyx Minimal",
        "onyx minimal": "Onyx Minimal",
        "onyx_minimal": "Onyx Minimal",
        "onyx": "Onyx Minimal",
        "midnight navy": "Midnight Navy",
        "midnight_navy": "Midnight Navy",
        "midnight": "Midnight Navy",
        "nordic light": "Nordic Light",
        "nordic_light": "Nordic Light",
        "nordic": "Nordic Light",
        "light": "Nordic Light",
        "tactical charcoal": "Tactical Charcoal",
        "tactical_charcoal": "Tactical Charcoal",
        "tactical": "Tactical Charcoal",
        "emerald surveillance": "Tactical Charcoal",
        "agent tactical (ispy)": "Midnight Navy",
        "agent tactical": "Midnight Navy",
    }
    canonical = name_map.get(str(theme_name).lower(), theme_name)
    palette = THEMES.get(canonical, THEMES["Slate Modern"])
    return build_theme_qss(palette)


DARK_THEME_QSS = get_theme_qss("Slate Modern")
