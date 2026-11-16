"""
TYPO® — Nothing Design System Edition (Industrial Precision Automation)
High-fidelity desktop interface built strictly to Nothing design language tokens (measured from nothing.tech).

Specifications:
- Neutral dominant ground (#F4F4F4 70.4%, #040404 14.8%, #D8D9D9 9.5%, #FFFFFF 4.5%, #595A5A 0.3%, #3C3C3C 0.2%)
- Signature Nothing yellow accent (#FFC700 0.1%) strictly for active badges and indicators
- Zero gradients, zero glassmorphism, zero drop-shadow noise
- Strict geometry and radii: 4px, 6px, 8px, and pill
- Typography stack: Inter Tight (body), JetBrains Mono (code), Figtree (display)
- Industrial high-contrast mechanical toggle switches and flat sliders
- Full TypingEngine automation integration with thread-safe Qt Signal Bridge
"""

import os
import sys
import time
import winsound
import ctypes
from typing import Optional

from PySide6.QtCore import Qt, QSize, QPointF, QRectF, Signal, QTimer, QObject, QEvent
from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QPainter, QPen,
    QBrush, QIcon, QPixmap, QPainterPath
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSlider, QTextEdit,
    QSizePolicy, QSpacerItem, QStackedWidget
)

from typo.typing_engine import TypingEngine, EngineState
from typo.win32_api import GlobalHotKeyManager, PRIMARY_HOTKEY_LABEL, get_foreground_window_info
from typo.clipboard import (
    get_current_clipboard,
    analyze_clipboard_content,
    set_test_clipboard_text,
    get_clipboard_sequence_number
)

APP_NAME = "TYPO — Precision Studio"
if getattr(sys, "frozen", False):
    ROOT_DIR = sys._MEIPASS
    ASSETS_DIR = os.path.join(ROOT_DIR, "typo", "assets")
    USER_FONTS_DIR = os.path.join(ROOT_DIR, "fonts")
else:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    USER_FONTS_DIR = os.path.join(ROOT_DIR, "fonts")

FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# =========================================================================
# Nothing Design Tokens (Measured from nothing.tech — DESIGN.md)
# =========================================================================
COLOR_BACKGROUND = "#F4F4F4"   # 70.4% dominant ground
COLOR_TEXT = "#040404"         # 14.8% action, high-contrast text & dark fills
COLOR_BORDER = "#D8D9D9"       # 9.5% subtle outlines, lines, slider tracks
COLOR_SURFACE = "#FFFFFF"      # 4.5% cards, input surfaces, active pills
COLOR_TEXT_MUTED = "#595A5A"   # 0.3% secondary labels, metadata
COLOR_DETAIL = "#3C3C3C"       # 0.2% detail elements, dark code editor
COLOR_WARNING = "#FFC700"      # 0.1% signature accent (never large panels)

# Typography Hierarchy
FONT_BODY_FAMILIES = ["Inter Tight", "Helvetica Neue", "Arial", "Segoe UI", "sans-serif"]
FONT_CODE_FAMILIES = ["JetBrains Mono", "LatteraMonoLL", "Consolas", "Courier New", "monospace"]
FONT_DISPLAY_FAMILIES = ["Figtree", "NType82-Regular", "Arial", "sans-serif"]
FONT_FAMILIES = FONT_BODY_FAMILIES
MONO_FAMILIES = FONT_CODE_FAMILIES


class EngineBridge(QObject):
    """
    Thread-safe Qt Signal Bridge.
    Marshals background thread callbacks cleanly into the Qt main GUI event loop via QueuedConnection.
    """
    sig_hotkey = Signal()
    sig_abort = Signal()
    sig_state_change = Signal(str, dict)
    sig_countdown = Signal(float)
    sig_progress = Signal(float, int, int, float, float, str)
    sig_error = Signal(str)


def get_app_font(size: int = 10, weight: QFont.Weight = QFont.Weight.Normal, mono: bool = False, display: bool = False) -> QFont:
    """Returns a QFont configured with Nothing design typography specifications."""
    if mono:
        f = QFont("JetBrains Mono", size, weight)
        f.setFamilies(FONT_CODE_FAMILIES)
    elif display:
        # Nothing design rule: Headings 24px or larger never heavier than 400
        w = QFont.Weight.Normal if size >= 24 else weight
        f = QFont("Figtree", size, w)
        f.setFamilies(FONT_DISPLAY_FAMILIES)
    else:
        f = QFont("Inter Tight", size, weight)
        f.setFamilies(FONT_BODY_FAMILIES)
    return f

SAMPLE_CODE = """#include <vector>
#include <string>
using namespace std;

class Solution {
public:
    int closedIsland(vector<vector<int>>& grid) {
        int rows = static_cast<int>(grid.size());
        if (rows == 0) return 0;
        int cols = static_cast<int>(grid[0].size());
        int islands = 0;

        // Explore connected components and count closed islands.
        for (int r = 0; r < rows; ++r) {
            for (int c = 0; c < cols; ++c) {
                if (grid[r][c] == 0) {
                    // Add your traversal here.
                }
            }
        }
        return islands;
    }
};"""


# ==========================================
# Nothing Mechanical Precision Switch
# ==========================================
class NothingSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, parent=None, checked=True):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(36, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_rect = QRectF(1, 1, 34, 18)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, 9, 9)

        if self._checked:
            track_color = QColor(COLOR_TEXT)       # #040404 stark dark track
            border_color = QColor(COLOR_TEXT)
            thumb_color = QColor(COLOR_SURFACE)     # #FFFFFF thumb
            thumb_x = 17.0
        else:
            track_color = QColor(COLOR_BORDER)     # #D8D9D9 neutral track
            border_color = QColor(COLOR_BORDER)
            thumb_color = QColor(COLOR_TEXT_MUTED)  # #595A5A thumb
            thumb_x = 2.0

        p.fillPath(track_path, QBrush(track_color))
        p.setPen(QPen(border_color, 1))
        p.drawPath(track_path)

        # Clean circular thumb
        thumb_rect = QRectF(thumb_x, 2.5, 15.0, 15.0)
        p.setBrush(QBrush(thumb_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(thumb_rect)

        # Active accent indicator dot (Nothing signature yellow dot)
        if self._checked:
            dot_rect = QRectF(thumb_x + 5.5, 8.0, 4.0, 4.0)
            p.setBrush(QBrush(QColor(COLOR_WARNING)))
            p.drawEllipse(dot_rect)

        p.end()

IOSSwitch = NothingSwitch


# ==========================================
# Nothing Clean Ground Background
# ==========================================
class AmbientBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(COLOR_BACKGROUND))
        p.end()


# ==========================================
# Nothing Surface Card Panel
# ==========================================
class NothingCard(QFrame):
    def __init__(self, parent=None, elevated=False):
        super().__init__(parent)
        self.setObjectName("nothingCard")
        bg_col = COLOR_SURFACE
        border_col = COLOR_BORDER
        self.setStyleSheet(f"""
            QFrame#nothingCard {{
                background: {bg_col};
                border: 1px solid {border_col};
                border-radius: 8px;
            }}
        """)

GlassCard = NothingCard


def make_label(text, size=10, color=COLOR_TEXT, bold=False, mono=False, display=False):
    lbl = QLabel(text)
    weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
    lbl.setFont(get_app_font(size, weight, mono=mono, display=display))
    lbl.setStyleSheet(f"color: {color}; background: transparent; border: none; padding: 0;")
    return lbl


def make_pill_button(text, active=False, danger=False, primary=False):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFont(get_app_font(9, QFont.Weight.Normal))
    btn.setMinimumHeight(30)

    if danger:
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {COLOR_TEXT};
                background: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background: {COLOR_BORDER};
                border-color: {COLOR_TEXT};
            }}
        """)
    elif primary or active:
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {COLOR_SURFACE};
                background: {COLOR_TEXT};
                border: 1px solid {COLOR_TEXT};
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: {COLOR_DETAIL};
                border-color: {COLOR_DETAIL};
            }}
        """)
    else:
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {COLOR_TEXT};
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background: {COLOR_BACKGROUND};
                border-color: {COLOR_TEXT};
            }}
            QPushButton:pressed {{
                background: {COLOR_BORDER};
            }}
        """)
    return btn


# ==========================================
# Main Studio Glass Window
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1024, 560)
        self.setMinimumSize(1000, 540)

        # Core Engine & Automation Pipeline
        self.engine = TypingEngine()
        self.hotkey_mgr: Optional[GlobalHotKeyManager] = None
        self.current_hotkey_label = PRIMARY_HOTKEY_LABEL
        self.sound_enabled = True
        self.ghost_hud = None
        self._last_clipboard_text = ""
        self._last_clip_seq = get_clipboard_sequence_number()
        self.active_tab_name = "Studio"

        # Apply Global DWM Dark Mode on Windows
        self._setup_dwm()

        # Register Apple SF Pro, SF Compact, New York, and Inter typefaces
        font_dirs_to_scan = [USER_FONTS_DIR, FONTS_DIR]
        for fdir in font_dirs_to_scan:
            if os.path.exists(fdir):
                for fname in os.listdir(fdir):
                    if fname.lower().endswith((".ttf", ".otf")):
                        full_fpath = os.path.join(fdir, fname)
                        QFontDatabase.addApplicationFont(full_fpath)
        QApplication.setFont(get_app_font(10))

        # Build Ambient Wallpaper Root
        self.root = AmbientBackground(self)
        self.setCentralWidget(self.root)

        root_layout = QHBoxLayout(self.root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(14)

        # 1. Left Frosted Glass Sidebar Bay (~204px)
        self.sidebar = self._build_sidebar()
        self.sidebar.setFixedWidth(204)
        root_layout.addWidget(self.sidebar)

        # 2. Right Workspace Deck (Fluid Multi-Tab Area)
        self.workspace = self._build_workspace()
        root_layout.addWidget(self.workspace, 1)

        # Thread-Safe Qt Signal Bridge for Background Threads
        self.bridge = EngineBridge()
        self.bridge.sig_hotkey.connect(self._trigger_execution)
        self.bridge.sig_abort.connect(self._trigger_abort)
        self.bridge.sig_state_change.connect(self._apply_state_change)
        self.bridge.sig_countdown.connect(self._apply_countdown_tick)
        self.bridge.sig_progress.connect(self._apply_progress_tick)
        self.bridge.sig_error.connect(self._apply_engine_error)

        # Bind Engine Callbacks via Bridge
        self.engine.on_state_change = self.bridge.sig_state_change.emit
        self.engine.on_countdown = self.bridge.sig_countdown.emit
        self.engine.on_progress = self.bridge.sig_progress.emit
        self.engine.on_error = self.bridge.sig_error.emit

        # Initialize Global Hotkey
        self._init_hotkeys()

        # Real-time System Clipboard Event Listener
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self._on_clipboard_data_changed)

        # Background Polling Timers (fast fallback monitor for external clipboard updates)
        self.clip_timer = QTimer(self)
        self.clip_timer.timeout.connect(self._poll_clipboard)
        self.clip_timer.start(400)

        self.target_timer = QTimer(self)
        self.target_timer.timeout.connect(self._poll_target_window)
        self.target_timer.start(800)

        # Initial Refresh
        self._sync_clipboard(force=True)

    def _setup_dwm(self):
        try:
            hwnd = int(self.winId())
            if sys.platform == "win32" and hwnd:
                top_hwnd = ctypes.windll.user32.GetAncestor(hwnd, 2) or hwnd
                dwmapi = ctypes.windll.dwmapi
                light_val = ctypes.c_int(0)
                dwmapi.DwmSetWindowAttribute(top_hwnd, 20, ctypes.byref(light_val), ctypes.sizeof(light_val))
                round_val = ctypes.c_int(2)
                dwmapi.DwmSetWindowAttribute(top_hwnd, 33, ctypes.byref(round_val), ctypes.sizeof(round_val))
        except Exception:
            pass

    # ==========================================
    # 1. Left Sidebar Bay
    # ==========================================
    def _build_sidebar(self):
        panel = NothingCard()
        col = QVBoxLayout(panel)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(6)

        # Top Profile Card
        profile = QFrame()
        profile.setFixedHeight(50)
        profile.setStyleSheet(f"""
            QFrame {{
                background: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
            }}
        """)
        pr_lay = QHBoxLayout(profile)
        pr_lay.setContentsMargins(8, 6, 8, 6)
        pr_lay.setSpacing(8)

        # Square 'T' Mark
        logo_box = QLabel("T")
        logo_box.setFixedSize(32, 32)
        logo_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_box.setFont(get_app_font(14, QFont.Weight.Normal, display=True))
        logo_box.setStyleSheet(f"""
            background: {COLOR_TEXT};
            color: {COLOR_SURFACE};
            border-radius: 4px;
        """)
        pr_lay.addWidget(logo_box)

        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(2)
        text_box.addWidget(make_label("TYPO STUDIO", 9, COLOR_TEXT, bold=False, display=True))
        text_box.addWidget(make_label("Precision Automation", 8, COLOR_TEXT_MUTED, bold=False))
        pr_lay.addLayout(text_box, 1)

        # Yellow Beacon Dot (0.1% signature Nothing accent)
        beacon = QLabel("●")
        beacon.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 8px; background: transparent; border: none;")
        pr_lay.addWidget(beacon)
        col.addWidget(profile)
        col.addSpacing(4)

        # Navigation Groups
        self.nav_buttons = {}
        groups = [
            ("CONTROL DECK", [("•", "Control Deck", True, False)]),
            ("PRECISION INPUT ENGINE", [("•", "Live Chat", False, False), ("•", "Images", False, False)]),
            ("SEQUENCER", [("•", "Sequencer Deck", False, True), ("•", "Biometrics Lab", False, False)]),
            ("TOOLS", [("•", "Code Memory", False, False), ("•", "Session Telemetry", False, False)]),
        ]

        for heading, items in groups:
            col.addWidget(make_label(heading, 8, COLOR_TEXT_MUTED, bold=False))
            for icon_char, name, is_active, has_beacon in items:
                btn = QPushButton()
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedHeight(30)
                b_lay = QHBoxLayout(btn)
                b_lay.setContentsMargins(8, 0, 8, 0)
                b_lay.setSpacing(6)

                icon_lbl = QLabel(icon_char)
                icon_lbl.setStyleSheet(f"color: {COLOR_TEXT if is_active else COLOR_TEXT_MUTED}; font-size: 11px; background: transparent;")
                b_lay.addWidget(icon_lbl)

                title_lbl = QLabel(name)
                title_lbl.setFont(get_app_font(9, QFont.Weight.Normal))
                title_lbl.setStyleSheet(f"color: {COLOR_SURFACE if is_active else COLOR_TEXT}; background: transparent;")
                b_lay.addWidget(title_lbl, 1)

                if has_beacon:
                    b_dot = QLabel("●")
                    b_dot.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 8px; background: transparent;")
                    b_lay.addWidget(b_dot)

                if is_active:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: {COLOR_TEXT};
                            border: 1px solid {COLOR_TEXT};
                            border-radius: 6px;
                        }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            border: 1px solid transparent;
                            border-radius: 6px;
                        }}
                        QPushButton:hover {{
                            background: {COLOR_BACKGROUND};
                            border: 1px solid {COLOR_BORDER};
                        }}
                    """)

                btn.clicked.connect(lambda checked=False, n=name: self._on_sidebar_nav_clicked(n))
                self.nav_buttons[name] = (btn, title_lbl)
                col.addWidget(btn)
            col.addSpacing(2)

        col.addStretch(1)

        # Bottom Hardware Hotkey Panel
        hk_card = QFrame()
        hk_card.setFixedHeight(84)
        hk_card.setStyleSheet(f"""
            QFrame {{
                background: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
            }}
        """)
        hk_lay = QVBoxLayout(hk_card)
        hk_lay.setContentsMargins(10, 8, 10, 8)
        hk_lay.setSpacing(6)

        hk_lay.addWidget(make_label("HARDWARE HOTKEY", 8, COLOR_TEXT_MUTED, bold=False))

        # Inset Key Capsule (Interactive trigger button)
        key_capsule = QPushButton()
        key_capsule.setCursor(Qt.CursorShape.PointingHandCursor)
        key_capsule.setToolTip("Click or press Alt + Z + T to start typing")
        key_capsule.clicked.connect(self._trigger_execution)
        key_capsule.setStyleSheet(f"""
            QPushButton {{
                background: {COLOR_TEXT};
                border: 1px solid {COLOR_TEXT};
                border-radius: 4px;
                text-align: left;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {COLOR_DETAIL};
                border-color: {COLOR_DETAIL};
            }}
        """)
        kc_lay = QHBoxLayout(key_capsule)
        kc_lay.setContentsMargins(8, 4, 8, 4)
        opt_lbl = make_label("⌨", 10, COLOR_WARNING, bold=False)
        opt_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        kc_lay.addWidget(opt_lbl)
        self.lbl_hotkey_disp = make_label(f"  {self.current_hotkey_label}  ", 9, COLOR_SURFACE, bold=False, mono=True)
        self.lbl_hotkey_disp.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        kc_lay.addWidget(self.lbl_hotkey_disp, 1)
        hk_lay.addWidget(key_capsule)

        # Emergency Abort
        self.btn_abort = QPushButton("!  Emergency Abort [ Esc ]")
        self.btn_abort.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abort.setFont(get_app_font(9, QFont.Weight.Normal, mono=True))
        self.btn_abort.setStyleSheet(f"""
            QPushButton {{
                color: {COLOR_TEXT_MUTED};
                background: transparent;
                border: 0;
                text-align: left;
                padding: 4px 2px;
            }}
            QPushButton:hover {{
                color: {COLOR_TEXT};
            }}
        """)
        self.btn_abort.clicked.connect(self._trigger_abort)
        hk_lay.addWidget(self.btn_abort)

        col.addWidget(hk_card)
        return panel

    # ==========================================
    # 2. Right Workspace Deck
    # ==========================================
    def _build_workspace(self):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        main_col = QVBoxLayout(container)
        main_col.setContentsMargins(0, 0, 0, 0)
        main_col.setSpacing(12)

        # A. Top Header Area (Subtitle + Title + Action Pills)
        main_col.addWidget(self._build_header_row())

        # B. Floating Capsule Navigation Bar (Tabs)
        main_col.addWidget(self._build_capsule_bar())

        # C. Multi-View Stacked Decks
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")

        # Primary Studio Deck (Matching reference screenshot)
        self.primary_studio_deck = self._build_primary_studio_deck()
        self.stack.addWidget(self.primary_studio_deck)

        # Biometrics Deck (Inhuman Mode 360 WPM & Extended Faders)
        self.biometrics_deck = self._build_biometrics_deck()
        self.stack.addWidget(self.biometrics_deck)

        main_col.addWidget(self.stack, 1)
        return container

    def _build_header_row(self):
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(4, 2, 4, 0)
        row.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(2)
        left.addWidget(make_label("TYPO ⚡", 9, COLOR_TEXT_MUTED, bold=False))
        self.lbl_deck_title = make_label("Control Deck · Studio Sequencer", 16, COLOR_TEXT, bold=False, display=True)
        left.addWidget(self.lbl_deck_title)
        row.addLayout(left, 1)

        # Right Action Pills (Nothing High-Contrast Style)
        self.btn_target = make_pill_button("● Target: Standby", primary=True)
        self.btn_target.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_target.setToolTip("Click to start or stop typing automation")
        self.btn_target.clicked.connect(self._toggle_execution)
        row.addWidget(self.btn_target)

        self.btn_ghost_hud = make_pill_button("Ghost HUD")
        self.btn_ghost_hud.clicked.connect(self._toggle_ghost_hud)
        row.addWidget(self.btn_ghost_hud)

        return w

    def _build_capsule_bar(self):
        capsule_bar = QFrame()
        capsule_bar.setStyleSheet(f"""
            QFrame {{
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
            }}
        """)
        row = QHBoxLayout(capsule_bar)
        row.setContentsMargins(6, 4, 6, 4)
        row.setSpacing(4)

        # Plus (+) Circle Button
        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFont(get_app_font(12, QFont.Weight.Normal))
        add_btn.setStyleSheet(f"""
            QPushButton {{
                color: {COLOR_SURFACE};
                background: {COLOR_TEXT};
                border: 1px solid {COLOR_TEXT};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {COLOR_DETAIL};
                border-color: {COLOR_DETAIL};
            }}
        """)
        add_btn.clicked.connect(self._load_sample)
        row.addWidget(add_btn)

        # Tabs (Studio and Speed)
        self.tab_buttons = {}
        tabs = ["Studio", "Speed"]

        for tname in tabs:
            is_active = (tname == "Studio")
            disp_text = f"● {tname}" if is_active else tname
            btn = QPushButton(disp_text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(get_app_font(9, QFont.Weight.Normal))
            btn.setFixedHeight(28)
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {COLOR_SURFACE};
                        background: {COLOR_TEXT};
                        border: 1px solid {COLOR_TEXT};
                        border-radius: 4px;
                        padding: 0 14px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {COLOR_TEXT_MUTED};
                        background: transparent;
                        border: 1px solid transparent;
                        border-radius: 4px;
                        padding: 0 12px;
                    }}
                    QPushButton:hover {{
                        color: {COLOR_TEXT};
                        background: {COLOR_BACKGROUND};
                        border: 1px solid {COLOR_BORDER};
                    }}
                """)
            btn.clicked.connect(lambda checked=False, tn=tname: self._select_tab(tn))
            self.tab_buttons[tname] = btn
            row.addWidget(btn)

        row.addStretch(1)
        return capsule_bar

    # ==========================================
    # 3. Primary Studio Deck
    # ==========================================
    def _build_primary_studio_deck(self):
        deck = QWidget()
        col = QVBoxLayout(deck)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)

        # A. Side-by-Side Sliders (Dual Column)
        col.addWidget(self._build_sliders_row())

        # B. Live Code Buffer & Non-Destructive Inspection Card
        col.addWidget(self._build_code_buffer_card(), 1)

        # C. Anti-Detection & Algorithmic Stealth Matrix Card
        col.addWidget(self._build_stealth_matrix_card())

        return deck

    def _build_sliders_row(self):
        row_w = QWidget()
        grid = QGridLayout(row_w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)

        # Flat minimalist Nothing slider styling
        slider_qss = f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {COLOR_BORDER};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLOR_TEXT};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {COLOR_TEXT};
                border: 2px solid {COLOR_SURFACE};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {COLOR_DETAIL};
            }}
        """

        # ------------------------------------------
        # Left Slider: Typo & Mistake Rate
        # ------------------------------------------
        card1 = NothingCard()
        c1_lay = QVBoxLayout(card1)
        c1_lay.setContentsMargins(16, 12, 16, 12)
        c1_lay.setSpacing(8)

        h1 = QHBoxLayout()
        h1.addWidget(make_label("Typo & Mistake Rate", 11, COLOR_TEXT, bold=False), 1)
        self.lbl_mistake_badge = make_label("1.5%", 9, COLOR_TEXT, bold=False, mono=True)
        self.lbl_mistake_badge.setStyleSheet(f"""
            color: {COLOR_TEXT};
            background: {COLOR_BACKGROUND};
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
            padding: 2px 8px;
        """)
        h1.addWidget(self.lbl_mistake_badge)
        c1_lay.addLayout(h1)

        self.slider_mistake = QSlider(Qt.Orientation.Horizontal)
        self.slider_mistake.setRange(0, 50)
        self.slider_mistake.setValue(15)
        self.slider_mistake.setStyleSheet(slider_qss)
        self.slider_mistake.valueChanged.connect(self._on_mistake_change)
        c1_lay.addWidget(self.slider_mistake)

        sub1 = QHBoxLayout()
        sub1.addWidget(make_label("0.0% (Flawless)", 8, COLOR_TEXT_MUTED))
        sub1.addStretch(1)
        sub1.addWidget(make_label("5.0% (Natural Typos)", 8, COLOR_TEXT_MUTED))
        c1_lay.addLayout(sub1)
        grid.addWidget(card1, 0, 0)

        # ------------------------------------------
        # Right Slider: Safety Focus Countdown
        # ------------------------------------------
        card2 = NothingCard()
        c2_lay = QVBoxLayout(card2)
        c2_lay.setContentsMargins(16, 12, 16, 12)
        c2_lay.setSpacing(8)

        h2 = QHBoxLayout()
        h2.addWidget(make_label("Safety Focus Countdown", 11, COLOR_TEXT, bold=False), 1)
        self.lbl_safety_badge = make_label("3.0s", 9, COLOR_TEXT, bold=False, mono=True)
        self.lbl_safety_badge.setStyleSheet(f"""
            color: {COLOR_TEXT};
            background: {COLOR_BACKGROUND};
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
            padding: 2px 8px;
        """)
        h2.addWidget(self.lbl_safety_badge)
        c2_lay.addLayout(h2)

        self.slider_safety = QSlider(Qt.Orientation.Horizontal)
        self.slider_safety.setRange(10, 80)
        self.slider_safety.setValue(30)
        self.slider_safety.setStyleSheet(slider_qss)
        self.slider_safety.valueChanged.connect(self._on_safety_change)
        c2_lay.addWidget(self.slider_safety)

        sub2 = QHBoxLayout()
        sub2.addWidget(make_label("1.0s (Fast Switch)", 8, COLOR_TEXT_MUTED))
        sub2.addStretch(1)
        sub2.addWidget(make_label("8.0s (Relaxed)", 8, COLOR_TEXT_MUTED))
        c2_lay.addLayout(sub2)
        grid.addWidget(card2, 0, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return row_w
    def _build_code_buffer_card(self):
        card = NothingCard()
        col = QVBoxLayout(card)
        col.setContentsMargins(16, 12, 16, 12)
        col.setSpacing(8)

        # Header Row
        hdr = QHBoxLayout()
        beacon = QLabel("●")
        beacon.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 8px; background: transparent;")
        hdr.addWidget(beacon)
        hdr.addWidget(make_label("Live Code Buffer & Non-Destructive Inspection", 11, COLOR_TEXT, bold=False), 1)

        self.btn_refresh = make_pill_button("Refresh")
        self.btn_refresh.clicked.connect(self._refresh_clipboard)
        hdr.addWidget(self.btn_refresh)

        self.btn_load_sample = make_pill_button("Load Sample Code", primary=True)
        self.btn_load_sample.clicked.connect(self._load_sample)
        hdr.addWidget(self.btn_load_sample)
        col.addLayout(hdr)

        # Recessed High-Contrast Monospace Editor
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setFont(get_app_font(10, mono=True))
        self.editor.setMinimumHeight(105)
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                color: {COLOR_SURFACE};
                background: {COLOR_TEXT};
                border: 1px solid {COLOR_DETAIL};
                border-radius: 6px;
                padding: 10px 12px;
                selection-background-color: {COLOR_WARNING};
                selection-color: {COLOR_TEXT};
            }}
            QScrollBar:vertical {{
                width: 6px;
                background: transparent;
                margin: 4px 1px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLOR_DETAIL};
                border-radius: 3px;
                min-height: 24px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        self.editor.setPlainText("Windows clipboard buffer is empty.\nCopy source code from your IDE, or click 'Load Sample Code' above.")
        self.editor.textChanged.connect(self._update_code_stats)
        col.addWidget(self.editor, 1)

        # Status Meta Label
        self.lbl_code_meta = make_label("Clipboard empty", 9, COLOR_TEXT_MUTED, mono=True)
        col.addWidget(self.lbl_code_meta)
        return card

    def _build_stealth_matrix_card(self):
        card = NothingCard()
        col = QVBoxLayout(card)
        col.setContentsMargins(16, 12, 16, 12)
        col.setSpacing(8)

        # Header Row
        hdr = QHBoxLayout()
        beacon = QLabel("●")
        beacon.setStyleSheet(f"color: {COLOR_WARNING}; font-size: 8px; background: transparent;")
        hdr.addWidget(beacon)
        hdr.addWidget(make_label("Anti-Detection & Algorithmic Stealth Matrix", 11, COLOR_TEXT, bold=False), 1)
        col.addLayout(hdr)

        # 2x2 Feature Grid
        grid = QGridLayout()
        grid.setSpacing(8)

        features = [
            ("•", "Simulated Cursor Wandering", "Subtle mouse drift with cubic easing defeats webcam gaze & mouse anomaly sensors", True, 0, 0),
            ("•", "Complexity Cadence Throttler", "Throttles to 35–50 WPM on nested DP & bitwise logic; fast on boilerplate", True, 0, 1),
            ("•", "Incremental Code Construction", "Outlines signature stub first, then navigates back inside function", False, 1, 0),
            ("•", "Selection & Refactoring Simulation", "Simulates Shift+Left selection & backspace replacement of variable", True, 1, 1),
        ]

        self.switches = {}
        for icon_char, title, desc, default_val, r, c in features:
            cell = QFrame()
            cell.setFixedHeight(50)
            cell.setStyleSheet(f"""
                QFrame {{
                    background: {COLOR_BACKGROUND};
                    border: 1px solid {COLOR_BORDER};
                    border-radius: 6px;
                }}
            """)
            c_lay = QHBoxLayout(cell)
            c_lay.setContentsMargins(10, 6, 10, 6)
            c_lay.setSpacing(8)

            # Minimalist Icon Box
            icon_box = QLabel(icon_char)
            icon_box.setFixedSize(24, 24)
            icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_box.setStyleSheet(f"""
                color: {COLOR_SURFACE};
                font-size: 11px;
                background: {COLOR_TEXT};
                border-radius: 4px;
            """)
            c_lay.addWidget(icon_box)

            # Text
            t_col = QVBoxLayout()
            t_col.setContentsMargins(0, 0, 0, 0)
            t_col.setSpacing(1)
            t_col.addWidget(make_label(title, 9, COLOR_TEXT, bold=False))
            d_lbl = make_label(desc, 8, COLOR_TEXT_MUTED)
            d_lbl.setWordWrap(True)
            t_col.addWidget(d_lbl)
            c_lay.addLayout(t_col, 1)

            # Nothing Switch
            sw = NothingSwitch(checked=default_val)
            sw.toggled.connect(lambda val, t=title: self._on_switch_toggled(t, val))
            self.switches[title] = sw
            c_lay.addWidget(sw)

            grid.addWidget(cell, r, c)

        col.addLayout(grid)
        return card

    # ==========================================
    # 4. Biometrics Lab Deck (Inhuman Mode 360 WPM)
    # ==========================================
    def _build_biometrics_deck(self):
        deck = QWidget()
        col = QVBoxLayout(deck)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)

        # Hero Inhuman Mode Card
        hero = NothingCard()
        h_lay = QVBoxLayout(hero)
        h_lay.setContentsMargins(16, 14, 16, 14)
        h_lay.setSpacing(8)

        h_top = QHBoxLayout()
        h_top.addWidget(make_label("Inhuman Mode (360 WPM)", 12, COLOR_TEXT, bold=False))
        self.lbl_inhuman_badge = make_label("STANDBY", 8, COLOR_TEXT_MUTED, bold=False, mono=True)
        self.lbl_inhuman_badge.setStyleSheet(f"""
            color: {COLOR_TEXT_MUTED};
            background: {COLOR_BACKGROUND};
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
            padding: 2px 8px;
        """)
        h_top.addWidget(self.lbl_inhuman_badge)
        h_top.addStretch(1)

        self.btn_engage_360 = make_pill_button("Engage 360 WPM", primary=True)
        self.btn_engage_360.clicked.connect(self._engage_360_wpm)
        h_top.addWidget(self.btn_engage_360)

        self.sw_inhuman = NothingSwitch(checked=False)
        self.sw_inhuman.toggled.connect(self._on_inhuman_toggled)
        h_top.addWidget(self.sw_inhuman)
        h_lay.addLayout(h_top)

        h_desc = make_label(
            "Overclocks typing velocity to 360 WPM (~33.3ms inter-keystroke cadence) with adaptive 12ms micro-dwell dynamics to bypass OS queue choke and blast through speed tests.",
            8, COLOR_TEXT_MUTED
        )
        h_desc.setWordWrap(True)
        h_lay.addWidget(h_desc)
        col.addWidget(hero)

        # Extended Velocity Fader Card
        fader_card = NothingCard()
        f_lay = QVBoxLayout(fader_card)
        f_lay.setContentsMargins(16, 14, 16, 14)
        f_lay.setSpacing(10)

        f_hdr = QHBoxLayout()
        f_hdr.addWidget(make_label("Typing Velocity", 11, COLOR_TEXT, bold=False), 1)
        self.lbl_wpm_val = make_label("80 WPM", 9, COLOR_TEXT, bold=False, mono=True)
        self.lbl_wpm_val.setStyleSheet(f"""
            color: {COLOR_TEXT};
            background: {COLOR_BACKGROUND};
            border: 1px solid {COLOR_BORDER};
            border-radius: 4px;
            padding: 2px 8px;
        """)
        f_hdr.addWidget(self.lbl_wpm_val)
        f_lay.addLayout(f_hdr)

        self.slider_wpm = QSlider(Qt.Orientation.Horizontal)
        self.slider_wpm.setRange(30, 360)
        self.slider_wpm.setValue(80)
        self.slider_wpm.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {COLOR_BORDER};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLOR_TEXT};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {COLOR_TEXT};
                border: 2px solid {COLOR_SURFACE};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {COLOR_DETAIL};
            }}
        """)
        self.slider_wpm.valueChanged.connect(self._on_wpm_slider_change)
        f_lay.addWidget(self.slider_wpm)

        f_sub = QHBoxLayout()
        f_sub.addWidget(make_label("30 (Relaxed)", 8, COLOR_TEXT_MUTED))
        f_sub.addWidget(make_label("80 (Human)", 8, COLOR_TEXT_MUTED))
        f_sub.addWidget(make_label("180 (Extreme)", 8, COLOR_TEXT_MUTED))
        f_sub.addStretch(1)
        f_sub.addWidget(make_label("360 WPM (Inhuman)", 8, COLOR_TEXT, bold=False))
        f_lay.addLayout(f_sub)
        col.addWidget(fader_card)

        col.addStretch(1)
        return deck

    # ==========================================
    # Navigation & Tab Handling
    # ==========================================
    def _select_tab(self, tab_name: str):
        self.active_tab_name = tab_name
        for name, btn in self.tab_buttons.items():
            is_active = (name == tab_name)
            btn.setText(f"● {name}" if is_active else name)
            btn.setFont(get_app_font(9, QFont.Weight.Normal))
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {COLOR_SURFACE};
                        background: {COLOR_TEXT};
                        border: 1px solid {COLOR_TEXT};
                        border-radius: 4px;
                        padding: 0 14px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {COLOR_TEXT_MUTED};
                        background: transparent;
                        border: 1px solid transparent;
                        border-radius: 4px;
                        padding: 0 12px;
                    }}
                    QPushButton:hover {{
                        color: {COLOR_TEXT};
                        background: {COLOR_BACKGROUND};
                        border: 1px solid {COLOR_BORDER};
                    }}
                """)

        if tab_name in ("Speed", "Biometrics"):
            self.stack.setCurrentWidget(self.biometrics_deck)
            self.lbl_deck_title.setText("Speed Deck · Cadence & Inhuman Mode")
        else:
            self.stack.setCurrentWidget(self.primary_studio_deck)
            self.lbl_deck_title.setText("Control Deck · Studio Sequencer")

    def _on_sidebar_nav_clicked(self, name: str):
        if name in ("Biometrics Lab", "Speed"):
            self._select_tab("Speed")
        else:
            self._select_tab("Studio")

    # ==========================================
    # Event Handlers & Sliders
    # ==========================================
    def _on_mistake_change(self, val: int):
        rate = val / 1000.0  # 15 -> 0.015
        self.engine.mistake_rate = rate
        self.lbl_mistake_badge.setText(f"{val / 10.0:.1f}%")

    def _on_safety_change(self, val: int):
        sec = val / 10.0     # 30 -> 3.0
        self.engine.safety_delay = sec
        self.lbl_safety_badge.setText(f"{sec:.1f}s")

    def _engage_360_wpm(self):
        self.engine.inhuman_mode = True
        self.engine.wpm = 360.0
        self.slider_wpm.setValue(360)
        self.sw_inhuman.setChecked(True)
        self._update_wpm_display(360, is_inhuman=True)
        if self.sound_enabled:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _on_inhuman_toggled(self, checked: bool):
        self.engine.inhuman_mode = checked
        if checked:
            self.engine.wpm = 360.0
            self.slider_wpm.setValue(360)
            self._update_wpm_display(360, is_inhuman=True)
        else:
            self.engine.wpm = 80.0
            self.slider_wpm.setValue(80)
            self._update_wpm_display(80, is_inhuman=False)

    def _on_wpm_slider_change(self, val: int):
        self.engine.wpm = float(val)
        is_inhuman = (val >= 300)
        self.engine.inhuman_mode = is_inhuman
        if self.sw_inhuman.isChecked() != is_inhuman:
            self.sw_inhuman.setChecked(is_inhuman)
        self._update_wpm_display(val, is_inhuman=is_inhuman)

    def _update_wpm_display(self, wpm: int, is_inhuman: bool):
        if is_inhuman:
            self.lbl_wpm_val.setText(f"⚡ {wpm} WPM (Inhuman)")
            self.lbl_wpm_val.setStyleSheet(f"""
                color: {COLOR_TEXT};
                background: {COLOR_WARNING};
                border: 1px solid {COLOR_WARNING};
                border-radius: 4px;
                padding: 2px 8px;
                font-weight: bold;
            """)
            self.lbl_inhuman_badge.setText("ACTIVE · 360 WPM")
            self.lbl_inhuman_badge.setStyleSheet(f"""
                color: {COLOR_TEXT};
                background: {COLOR_WARNING};
                border: 1px solid {COLOR_WARNING};
                border-radius: 4px;
                padding: 2px 8px;
                font-weight: bold;
            """)
        else:
            self.lbl_wpm_val.setText(f"{wpm} WPM")
            self.lbl_wpm_val.setStyleSheet(f"""
                color: {COLOR_TEXT};
                background: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 2px 8px;
            """)
            self.lbl_inhuman_badge.setText("STANDBY")
            self.lbl_inhuman_badge.setStyleSheet(f"""
                color: {COLOR_TEXT_MUTED};
                background: {COLOR_BACKGROUND};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 2px 8px;
            """)

    def _on_switch_toggled(self, title: str, enabled: bool):
        if title == "Simulated Cursor Wandering":
            self.engine.cursor_wandering_enabled = enabled
        elif title == "Complexity Cadence Throttler":
            self.engine.complexity_throttler_enabled = enabled
        elif title == "Incremental Code Construction":
            self.engine.incremental_construction_mode = enabled
        elif title == "Selection & Refactoring Simulation":
            self.engine.refactoring_simulation_enabled = enabled

    def _toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        if hasattr(self, "btn_sound") and self.btn_sound is not None:
            self.btn_sound.setText("◖)) Audio On" if self.sound_enabled else "◖× Audio Off")
        if self.sound_enabled:
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass

    def _toggle_ghost_hud(self):
        from typo.ghost_hud import GhostHUD
        if self.ghost_hud is None:
            try:
                self.ghost_hud = GhostHUD(master=None, on_close_callback=lambda: setattr(self, "ghost_hud", None))
                self.ghost_hud.show_hud()
                self.btn_ghost_hud.setText("◉ Ghost HUD (On)")
            except Exception as e:
                print(f"[Ghost HUD] Open note: {e}")
                self.ghost_hud = None
        else:
            try:
                self.ghost_hud.destroy()
            except Exception:
                pass
            self.ghost_hud = None
            self.btn_ghost_hud.setText("◉ Ghost HUD")

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self._sync_clipboard(force=False)
        super().changeEvent(event)

    # ==========================================
    # Clipboard & Target Polling
    # ==========================================
    def _on_clipboard_data_changed(self):
        """Instantaneous handler triggered by Qt when system clipboard updates."""
        if self.engine.state in (EngineState.COUNTDOWN, EngineState.TYPING):
            return
        self._sync_clipboard(force=False)

    def _sync_clipboard(self, force: bool = False):
        """
        Synchronizes the live code buffer with the system clipboard.
        Detects clipboard changes via sequence number and content verification.
        Does not disrupt user if they are currently typing in the editor widget.
        """
        if not force and self.engine.state in (EngineState.COUNTDOWN, EngineState.TYPING):
            return

        seq = get_clipboard_sequence_number()
        # Fast path: sequence number unchanged and not forced
        if not force and seq != 0 and seq == self._last_clip_seq:
            return

        text, is_empty, err_msg = get_current_clipboard()
        self._last_clip_seq = seq

        if not is_empty and text:
            editor_text = self.editor.toPlainText()
            # If editor has focus and clipboard text matches current editor text, don't clobber
            if not force and self.editor.hasFocus() and text == editor_text:
                self._last_clipboard_text = text
                return

            if force or text != self._last_clipboard_text or text != editor_text:
                self._last_clipboard_text = text
                self.editor.setPlainText(text)
                self._update_code_stats()
        elif is_empty:
            editor_text = self.editor.toPlainText()
            if force or not editor_text or editor_text.startswith("Windows clipboard buffer is empty."):
                self._last_clipboard_text = ""
                self.lbl_code_meta.setText("Clipboard empty")
                self.lbl_code_meta.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")

    def _poll_clipboard(self):
        """Periodic fallback check for clipboard updates."""
        self._sync_clipboard(force=False)

    def _refresh_clipboard(self):
        """Manual refresh button handler."""
        self._sync_clipboard(force=True)
        if self.sound_enabled:
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass

    def _load_sample(self):
        self.editor.setPlainText(SAMPLE_CODE)
        self._last_clipboard_text = SAMPLE_CODE
        set_test_clipboard_text(SAMPLE_CODE)
        self._last_clip_seq = get_clipboard_sequence_number()
        self._update_code_stats()
        if self.sound_enabled:
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass

    def _update_code_stats(self):
        text = self.editor.toPlainText()
        if not text or text.startswith("Windows clipboard buffer is empty."):
            self.lbl_code_meta.setText("Clipboard empty")
            self.lbl_code_meta.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; background: transparent;")
            return

        stats = analyze_clipboard_content(text)
        tag = " • Code detected" if stats.get("has_code", False) else ""
        lines = stats.get("line_count", stats.get("lines", 0))
        chars = stats.get("char_count", len(text))
        words = stats.get("word_count", stats.get("words", 0))
        self.lbl_code_meta.setText(f"{chars} characters • {lines} lines • {words} tokens{tag}")
        self.lbl_code_meta.setStyleSheet(f"color: {COLOR_TEXT}; background: transparent;")

    def _poll_target_window(self):
        try:
            info = get_foreground_window_info()
            proc = info.get("process_name", "")
            if proc and self.engine.state in (EngineState.IDLE, EngineState.COMPLETED, EngineState.STOPPED):
                if not any(p in proc.lower() for p in ("typo", "python")):
                    self.btn_target.setText(f"● Target: {proc[:16]}")
        except Exception:
            pass

    # ==========================================
    # Global Hotkey & Engine Integration
    # ==========================================
    def _init_hotkeys(self):
        try:
            self.hotkey_mgr = GlobalHotKeyManager(
                callback=self.bridge.sig_hotkey.emit,
                abort_callback=self.bridge.sig_abort.emit
            )
            self.hotkey_mgr.start()
        except Exception as e:
            print(f"[TYPO Hotkey] Initialization note: {e}")

    def _toggle_execution(self):
        if self.engine.state in (EngineState.COUNTDOWN, EngineState.TYPING):
            self._trigger_abort()
        else:
            self._trigger_execution()

    def _trigger_execution(self):
        try:
            if self.engine.state in (EngineState.COUNTDOWN, EngineState.TYPING):
                return

            # Always sync with latest clipboard before starting
            self._sync_clipboard(force=False)

            text = self.editor.toPlainText()
            if not text or text.startswith("Windows clipboard buffer is empty."):
                text, is_empty, err_msg = get_current_clipboard()
                if is_empty or not text:
                    text = SAMPLE_CODE
                    self.editor.setPlainText(SAMPLE_CODE)
                    self._update_code_stats()

            self.btn_target.setText("⏳ Armed...")
            self.engine.start(text)
            if self.sound_enabled:
                try:
                    winsound.MessageBeep(winsound.MB_OK)
                except Exception:
                    pass
        except Exception as e:
            print(f"[TYPO Trigger Error] {e}")
            self.btn_target.setText(f"❌ Error: {str(e)[:14]}")

    def _reset_to_idle(self):
        if self.engine.state in (EngineState.STOPPED, EngineState.COMPLETED):
            self.engine.state = EngineState.IDLE
            self.btn_target.setText("● Target: Standby")

    def _trigger_abort(self):
        self.engine.stop()
        self.engine.state = EngineState.IDLE
        self.btn_target.setText("● Target: Standby")
        if self.sound_enabled:
            try:
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception:
                pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._trigger_abort()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _apply_state_change(self, state: str, details: dict):
        if state == EngineState.IDLE:
            self.btn_target.setText("● Target: Standby")
        elif state == EngineState.COUNTDOWN:
            delay = details.get("delay", self.engine.safety_delay)
            self.btn_target.setText(f"⏳ Switch: {delay:.1f}s")
        elif state == EngineState.TYPING:
            target = details.get("target", {})
            proc = target.get("process_name", "Editor")[:12]
            self.btn_target.setText(f"⚡ Typing: {proc}")
        elif state == EngineState.PAUSED:
            self.btn_target.setText("⏸ Paused")
        elif state == EngineState.STOPPED:
            self.btn_target.setText("🛑 Stopped")
            QTimer.singleShot(1500, self._reset_to_idle)
        elif state == EngineState.COMPLETED:
            self.btn_target.setText("✔ Done (100%)")
            QTimer.singleShot(2500, self._reset_to_idle)

        if self.ghost_hud and hasattr(self.ghost_hud, "update_state"):
            try:
                self.ghost_hud.update_state(state, details)
            except Exception:
                pass

    def _apply_countdown_tick(self, seconds_left: float):
        if seconds_left > 0:
            self.btn_target.setText(f"⏳ Armed: {seconds_left:.1f}s")
        else:
            self.btn_target.setText("⚡ Typing...")
        if self.ghost_hud and hasattr(self.ghost_hud, "update_countdown"):
            try:
                self.ghost_hud.update_countdown(seconds_left)
            except Exception:
                pass

    def _apply_progress_tick(self, pct, typed, total, elapsed, remaining, char):
        if self.ghost_hud and hasattr(self.ghost_hud, "update_progress"):
            try:
                self.ghost_hud.update_progress(pct, typed, total, elapsed, remaining, char)
            except Exception:
                pass

    def _apply_engine_error(self, err_msg: str):
        self.btn_target.setText(f"❌ {err_msg[:16]}")

    def closeEvent(self, event):
        self.engine.stop()
        if self.hotkey_mgr:
            self.hotkey_mgr.stop()
        if self.ghost_hud:
            try:
                self.ghost_hud.destroy()
            except Exception:
                pass
        event.accept()


# Backwards compatibility alias
TypoApp = MainWindow


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("TYPO Studio")
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
