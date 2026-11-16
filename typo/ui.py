"""
TYPO® — Frosted Black Edition (Apple Liquid Glassmorphism)
High-fidelity desktop interface built with Apple visionOS / macOS dark frosted glass styling.

Specifications:
- Obsidian dark foundation (#090B10) with subtle ambient atmospheric depth glows
- Translucent frosted black acrylic glass cards (rgba(18, 22, 32, 0.70)) with specular hairlines
- Recessed smoked glass monospace code buffer with live clipboard analytics
- Apple visionOS animated iOS switch toggles with electric green (#30D158) active state
- Studio & Speed decks with dual faders, Inhuman Mode (360 WPM), and 2x2 stealth matrix
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
    QColor, QFont, QFontDatabase, QLinearGradient, QRadialGradient, QPainter, QPen,
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

APP_NAME = "TYPO — Frosted Black Studio"
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
# Frosted Black Glassmorphism Design Tokens (Apple Liquid Glass)
# =========================================================================
COLOR_BACKGROUND = "#090B10"           # Dark obsidian foundation
COLOR_PANEL_BG = "rgba(18, 22, 32, 0.70)" # Frosted dark glass
COLOR_PANEL_ELEVATED = "rgba(24, 30, 44, 0.80)" # Elevated frosted dark glass
COLOR_PANEL_BORDER = "rgba(255, 255, 255, 0.11)" # Specular glass rim
COLOR_PANEL_BORDER_ELEV = "rgba(255, 255, 255, 0.18)" # Luminous glass highlight
COLOR_INSET_BG = "rgba(8, 11, 16, 0.75)"   # Recessed dark glass (code editor & sub-cards)
COLOR_TEXT_PRIMARY = "#FFFFFF"         # Crisp Apple white
COLOR_TEXT_SECONDARY = "#94A3B8"       # Secondary silver/slate
COLOR_TEXT_MUTED = "#64748B"           # Muted hints/labels
COLOR_ACCENT_AMBER = "#F59E0B"         # Vibrant gold/amber accent
COLOR_ACCENT_CYAN = "#38BDF8"          # Luminous blue accent
COLOR_ACCENT_GREEN = "#30D158"         # Apple green

# Backwards compatibility aliases
COLOR_TEXT = COLOR_TEXT_PRIMARY
COLOR_BORDER = COLOR_PANEL_BORDER
COLOR_SURFACE = COLOR_PANEL_BG
COLOR_WARNING = COLOR_ACCENT_AMBER

# Typography Hierarchy
FONT_BODY_FAMILIES = ["SF Pro", "Inter", "Segoe UI", "-apple-system", "sans-serif"]
FONT_CODE_FAMILIES = ["JetBrains Mono", "Consolas", "Courier New", "monospace"]
FONT_DISPLAY_FAMILIES = ["SF Pro Display", "SF Pro", "Inter", "Segoe UI", "sans-serif"]
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
    """Returns a QFont configured with Apple frosted glass typography specifications."""
    if mono:
        f = QFont("JetBrains Mono", size, weight)
        f.setFamilies(FONT_CODE_FAMILIES)
    elif display:
        f = QFont("SF Pro Display", size, weight)
        f.setFamilies(FONT_DISPLAY_FAMILIES)
    else:
        f = QFont("SF Pro", size, weight)
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
# Apple iOS / visionOS Animated Switch
# ==========================================
class IOSSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, parent=None, checked=True):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(38, 22)
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

        track_rect = QRectF(1, 1, 36, 20)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, 10, 10)

        if self._checked:
            track_color = QColor("#30D158")       # Apple Vibrant Green
            border_color = QColor(48, 209, 88, 180)
            thumb_x = 18.5
        else:
            track_color = QColor(36, 44, 58, 210) # Dark frosted slate track
            border_color = QColor(255, 255, 255, 30)
            thumb_x = 2.5

        p.fillPath(track_path, QBrush(track_color))
        p.setPen(QPen(border_color, 1))
        p.drawPath(track_path)

        # Smooth circular thumb
        thumb_rect = QRectF(thumb_x, 2.5, 17.0, 17.0)
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.setPen(QPen(QColor(0, 0, 0, 35), 0.5))
        p.drawEllipse(thumb_rect)
        p.end()

NothingSwitch = IOSSwitch  # Alias for compatibility


# ==========================================
# Ambient Obsidian Background with Glass Glow
# ==========================================
class AmbientBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = self.rect()

        # Rich dark obsidian foundation
        base = QLinearGradient(0, 0, r.width(), r.height())
        base.setColorAt(0.0, QColor("#090B10"))
        base.setColorAt(0.5, QColor("#10141E"))
        base.setColorAt(1.0, QColor("#06080C"))
        p.fillRect(r, base)

        # Ambient frosted glass illumination (subtle deep sapphire / slate glow)
        glow1 = QRadialGradient(r.width() * 0.75, r.height() * 0.20, r.width() * 0.65)
        glow1.setColorAt(0.0, QColor(38, 52, 78, 90))
        glow1.setColorAt(0.5, QColor(22, 30, 46, 45))
        glow1.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(r, glow1)

        glow2 = QRadialGradient(r.width() * 0.25, r.height() * 0.85, r.width() * 0.55)
        glow2.setColorAt(0.0, QColor(42, 32, 54, 55))
        glow2.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(r, glow2)

        p.end()


# ==========================================
# Frosted Black Glass Card Panel
# ==========================================
class GlassCard(QFrame):
    def __init__(self, parent=None, elevated=False):
        super().__init__(parent)
        self.setObjectName("glassCard")
        bg_col = COLOR_PANEL_ELEVATED if elevated else COLOR_PANEL_BG
        border_col = COLOR_PANEL_BORDER_ELEV if elevated else COLOR_PANEL_BORDER
        self.setStyleSheet(f"""
            QFrame#glassCard {{
                background: {bg_col};
                border: 1px solid {border_col};
                border-radius: 16px;
            }}
        """)

NothingCard = GlassCard  # Alias for compatibility


def make_label(text, size=10, color="#FFFFFF", bold=False, mono=False, display=False):
    lbl = QLabel(text)
    weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
    lbl.setFont(get_app_font(size, weight, mono=mono, display=display))
    lbl.setStyleSheet(f"color: {color}; background: transparent; border: none; padding: 0;")
    return lbl


def make_pill_button(text, active=False, danger=False, primary=False):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFont(get_app_font(9, QFont.Weight.DemiBold))
    btn.setMinimumHeight(32)

    if danger:
        btn.setStyleSheet("""
            QPushButton {
                color: #F87171;
                background: rgba(239, 68, 68, 0.16);
                border: 1px solid rgba(248, 113, 113, 0.38);
                border-radius: 16px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.28);
                border-color: rgba(248, 113, 113, 0.55);
            }
        """)
    elif primary or active:
        btn.setStyleSheet("""
            QPushButton {
                color: #FFFFFF;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(245, 158, 11, 0.88), stop:1 rgba(217, 119, 6, 0.88));
                border: 1px solid rgba(255, 215, 150, 0.65);
                border-radius: 16px;
                padding: 0 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(251, 191, 36, 0.98), stop:1 rgba(245, 158, 11, 0.98));
                border-color: rgba(255, 235, 180, 0.85);
            }
        """)
    else:
        btn.setStyleSheet("""
            QPushButton {
                color: #F1F5F9;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 16px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
                border-color: rgba(255, 255, 255, 0.25);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.05);
            }
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
                dark_val = ctypes.c_int(1)
                dwmapi.DwmSetWindowAttribute(top_hwnd, 20, ctypes.byref(dark_val), ctypes.sizeof(dark_val))
                round_val = ctypes.c_int(2)
                dwmapi.DwmSetWindowAttribute(top_hwnd, 33, ctypes.byref(round_val), ctypes.sizeof(round_val))
        except Exception:
            pass

    # ==========================================
    # 1. Left Frosted Glass Sidebar Bay
    # ==========================================
    def _build_sidebar(self):
        panel = GlassCard()
        col = QVBoxLayout(panel)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(6)

        # Top Profile Card (Frosted Glass Inset)
        profile = QFrame()
        profile.setFixedHeight(54)
        profile.setStyleSheet("""
            QFrame {
                background: rgba(10, 14, 22, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
            }
        """)
        pr_lay = QHBoxLayout(profile)
        pr_lay.setContentsMargins(10, 8, 10, 8)
        pr_lay.setSpacing(8)

        # Square 'T' Mark (Frosted Luminous Badge)
        logo_box = QLabel("T")
        logo_box.setFixedSize(34, 34)
        logo_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_box.setFont(get_app_font(15, QFont.Weight.Bold, display=True))
        logo_box.setStyleSheet("""
            background: rgba(255, 255, 255, 0.12);
            color: #FFFFFF;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
        """)
        pr_lay.addWidget(logo_box)

        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(2)
        text_box.addWidget(make_label("TYPO STUDIO", 9, "#FFFFFF", bold=True, display=True))
        text_box.addWidget(make_label("Frosted Glass Edition", 8, "#94A3B8", bold=False))
        pr_lay.addLayout(text_box, 1)

        # Green Beacon Dot
        beacon = QLabel("●")
        beacon.setStyleSheet("color: #30D158; font-size: 9px; background: transparent; border: none;")
        pr_lay.addWidget(beacon)
        col.addWidget(profile)
        col.addSpacing(4)

        # Navigation Groups
        self.nav_buttons = {}
        groups = [
            ("CONTROL DECK", [("⌂", "Control Deck", True, False)]),
            ("PRECISION INPUT ENGINE", [("💬", "Live Chat", False, False), ("🖼", "Images", False, False)]),
            ("SEQUENCER", [("⊞", "Sequencer Deck", False, True), ("⚡", "Biometrics Lab", False, False)]),
            ("TOOLS", [("🧠", "Code Memory", False, False), ("📊", "Session Telemetry", False, False)]),
        ]

        for heading, items in groups:
            col.addWidget(make_label(heading, 8, "#64748B", bold=True))
            for icon_char, name, is_active, has_beacon in items:
                btn = QPushButton()
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedHeight(32)
                b_lay = QHBoxLayout(btn)
                b_lay.setContentsMargins(10, 0, 10, 0)
                b_lay.setSpacing(8)

                icon_lbl = QLabel(icon_char)
                icon_lbl.setStyleSheet("color: #F59E0B;" if is_active else "color: #94A3B8; font-size: 12px; background: transparent;")
                b_lay.addWidget(icon_lbl)

                title_lbl = QLabel(name)
                title_lbl.setFont(get_app_font(10, QFont.Weight.Bold if is_active else QFont.Weight.Normal))
                title_lbl.setStyleSheet("color: #FFFFFF;" if is_active else "color: #CBD5E1; background: transparent;")
                b_lay.addWidget(title_lbl, 1)

                if has_beacon:
                    b_dot = QLabel("●")
                    b_dot.setStyleSheet("color: #30D158; font-size: 9px; background: transparent;")
                    b_lay.addWidget(b_dot)

                if is_active:
                    btn.setStyleSheet("""
                        QPushButton {
                            background: rgba(255, 255, 255, 0.14);
                            border: 1px solid rgba(255, 255, 255, 0.24);
                            border-radius: 10px;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background: transparent;
                            border: 1px solid transparent;
                            border-radius: 10px;
                        }
                        QPushButton:hover {
                            background: rgba(255, 255, 255, 0.08);
                            border: 1px solid rgba(255, 255, 255, 0.12);
                        }
                    """)

                btn.clicked.connect(lambda checked=False, n=name: self._on_sidebar_nav_clicked(n))
                self.nav_buttons[name] = (btn, title_lbl)
                col.addWidget(btn)
            col.addSpacing(2)

        col.addStretch(1)

        # Bottom Hardware Hotkey Panel
        hk_card = QFrame()
        hk_card.setFixedHeight(84)
        hk_card.setStyleSheet("""
            QFrame {
                background: rgba(10, 14, 22, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
            }
        """)
        hk_lay = QVBoxLayout(hk_card)
        hk_lay.setContentsMargins(10, 8, 10, 8)
        hk_lay.setSpacing(6)

        hk_lay.addWidget(make_label("HARDWARE HOTKEY", 8, "#64748B", bold=True))

        # Inset Key Capsule (Interactive trigger button)
        key_capsule = QPushButton()
        key_capsule.setCursor(Qt.CursorShape.PointingHandCursor)
        key_capsule.setToolTip("Click or press Alt + Z + T to start typing")
        key_capsule.clicked.connect(self._trigger_execution)
        key_capsule.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 8px;
                text-align: left;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.28);
            }
        """)
        kc_lay = QHBoxLayout(key_capsule)
        kc_lay.setContentsMargins(10, 5, 10, 5)
        opt_lbl = make_label("⌥", 11, "#F59E0B", bold=True)
        opt_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        kc_lay.addWidget(opt_lbl)
        self.lbl_hotkey_disp = make_label(f"  {self.current_hotkey_label}  ", 9, "#FFFFFF", bold=True, mono=True)
        self.lbl_hotkey_disp.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        kc_lay.addWidget(self.lbl_hotkey_disp, 1)
        hk_lay.addWidget(key_capsule)

        # Emergency Abort
        self.btn_abort = QPushButton("!  Emergency Abort [ Esc ]")
        self.btn_abort.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_abort.setFont(get_app_font(9, QFont.Weight.Bold))
        self.btn_abort.setStyleSheet("""
            QPushButton {
                color: #F87171;
                background: transparent;
                border: 0;
                text-align: left;
                padding: 4px 2px;
            }
            QPushButton:hover {
                color: #FCA5A5;
            }
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
        left.addWidget(make_label("TYPO ⚡", 9, "#F59E0B", bold=True))
        self.lbl_deck_title = make_label("Control Deck · Studio Sequencer", 16, "#FFFFFF", bold=True)
        left.addWidget(self.lbl_deck_title)
        row.addLayout(left, 1)

        # Right Action Pills (Frosted Black Glass Pills)
        self.btn_target = make_pill_button("● Target: Standby")
        self.btn_target.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_target.setToolTip("Click to start or stop typing automation")
        self.btn_target.clicked.connect(self._toggle_execution)
        row.addWidget(self.btn_target)

        self.btn_ghost_hud = make_pill_button("👻 Ghost HUD")
        self.btn_ghost_hud.clicked.connect(self._toggle_ghost_hud)
        row.addWidget(self.btn_ghost_hud)

        return w

    def _build_capsule_bar(self):
        capsule_bar = QFrame()
        capsule_bar.setStyleSheet("""
            QFrame {
                background: rgba(16, 21, 30, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
            }
        """)
        row = QHBoxLayout(capsule_bar)
        row.setContentsMargins(6, 4, 8, 4)
        row.setSpacing(4)

        # Plus (+) Circle Button
        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFont(get_app_font(13, QFont.Weight.Bold))
        add_btn.setStyleSheet("""
            QPushButton {
                color: #FFFFFF;
                background: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.20);
                border-color: rgba(255, 255, 255, 0.30);
            }
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
            btn.setFont(get_app_font(9, QFont.Weight.DemiBold if is_active else QFont.Weight.Normal))
            btn.setFixedHeight(28)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        color: #FFFFFF;
                        background: rgba(255, 255, 255, 0.16);
                        border: 1px solid rgba(255, 255, 255, 0.28);
                        border-radius: 14px;
                        padding: 0 14px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        color: #94A3B8;
                        background: transparent;
                        border: none;
                        padding: 0 12px;
                    }
                    QPushButton:hover {
                        color: #FFFFFF;
                        background: rgba(255, 255, 255, 0.08);
                        border-radius: 14px;
                    }
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
        grid.setSpacing(14)

        slider_groove_qss = """
            QSlider::groove:horizontal {
                height: 5px;
                background: rgba(255, 255, 255, 0.12);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid rgba(255, 255, 255, 0.85);
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #F8FAFC;
                border-color: #FFFFFF;
            }
        """

        # ------------------------------------------
        # Left Slider: Typo & Mistake Rate
        # ------------------------------------------
        card1 = GlassCard()
        c1_lay = QVBoxLayout(card1)
        c1_lay.setContentsMargins(18, 14, 18, 14)
        c1_lay.setSpacing(8)

        h1 = QHBoxLayout()
        h1.addWidget(make_label("Typo & Mistake Rate", 12, "#FFFFFF", bold=True), 1)
        self.lbl_mistake_badge = make_label("1.5%", 10, "#FDE68A", bold=True, mono=True)
        self.lbl_mistake_badge.setStyleSheet("""
            color: #FDE68A;
            background: rgba(245, 158, 11, 0.2);
            border: 1px solid rgba(245, 158, 11, 0.45);
            border-radius: 10px;
            padding: 3px 10px;
        """)
        h1.addWidget(self.lbl_mistake_badge)
        c1_lay.addLayout(h1)

        self.slider_mistake = QSlider(Qt.Orientation.Horizontal)
        self.slider_mistake.setRange(0, 50)
        self.slider_mistake.setValue(15)
        self.slider_mistake.setStyleSheet(slider_groove_qss + """
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D97706, stop:1 #F59E0B);
                border-radius: 2px;
            }
        """)
        self.slider_mistake.valueChanged.connect(self._on_mistake_change)
        c1_lay.addWidget(self.slider_mistake)

        sub1 = QHBoxLayout()
        sub1.addWidget(make_label("0.0% (Flawless)", 8, "#64748B"))
        sub1.addStretch(1)
        sub1.addWidget(make_label("5.0% (Natural Typos)", 8, "#64748B"))
        c1_lay.addLayout(sub1)
        grid.addWidget(card1, 0, 0)

        # ------------------------------------------
        # Right Slider: Safety Focus Countdown
        # ------------------------------------------
        card2 = GlassCard()
        c2_lay = QVBoxLayout(card2)
        c2_lay.setContentsMargins(18, 14, 18, 14)
        c2_lay.setSpacing(8)

        h2 = QHBoxLayout()
        h2.addWidget(make_label("Safety Focus Countdown", 12, "#FFFFFF", bold=True), 1)
        self.lbl_safety_badge = make_label("3.0s", 10, "#BAE6FD", bold=True, mono=True)
        self.lbl_safety_badge.setStyleSheet("""
            color: #BAE6FD;
            background: rgba(56, 189, 248, 0.2);
            border: 1px solid rgba(56, 189, 248, 0.45);
            border-radius: 10px;
            padding: 3px 10px;
        """)
        h2.addWidget(self.lbl_safety_badge)
        c2_lay.addLayout(h2)

        self.slider_safety = QSlider(Qt.Orientation.Horizontal)
        self.slider_safety.setRange(10, 80)
        self.slider_safety.setValue(30)
        self.slider_safety.setStyleSheet(slider_groove_qss + """
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #38BDF8);
                border-radius: 2px;
            }
        """)
        self.slider_safety.valueChanged.connect(self._on_safety_change)
        c2_lay.addWidget(self.slider_safety)

        sub2 = QHBoxLayout()
        sub2.addWidget(make_label("1.0s (Fast Switch)", 8, "#64748B"))
        sub2.addStretch(1)
        sub2.addWidget(make_label("8.0s (Relaxed)", 8, "#64748B"))
        c2_lay.addLayout(sub2)
        grid.addWidget(card2, 0, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return row_w

    def _build_code_buffer_card(self):
        card = GlassCard()
        col = QVBoxLayout(card)
        col.setContentsMargins(18, 14, 18, 14)
        col.setSpacing(8)

        # Header Row
        hdr = QHBoxLayout()
        beacon = QLabel("●")
        beacon.setStyleSheet("color: #F59E0B; font-size: 10px; background: transparent;")
        hdr.addWidget(beacon)
        hdr.addWidget(make_label("Live Code Buffer & Non-Destructive Inspection", 12, "#FFFFFF", bold=True), 1)

        self.btn_refresh = make_pill_button("↻ Refresh")
        self.btn_refresh.clicked.connect(self._refresh_clipboard)
        hdr.addWidget(self.btn_refresh)

        self.btn_load_sample = make_pill_button("📁 Load Sample Code", primary=True)
        self.btn_load_sample.clicked.connect(self._load_sample)
        hdr.addWidget(self.btn_load_sample)
        col.addLayout(hdr)

        # Recessed Frosted Dark Monospace Editor
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setFont(get_app_font(10, mono=True))
        self.editor.setMinimumHeight(110)
        self.editor.setStyleSheet("""
            QTextEdit {
                color: #F8FAFC;
                background: rgba(8, 11, 16, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 12px;
                padding: 10px 12px;
                selection-background-color: rgba(245, 158, 11, 0.55);
                selection-color: #FFFFFF;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
                margin: 4px 1px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.18);
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.30);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        self.editor.setPlainText("Windows clipboard buffer is empty.\nCopy source code from your IDE, or click 'Load Sample Code' above.")
        self.editor.textChanged.connect(self._update_code_stats)
        col.addWidget(self.editor, 1)

        # Status Meta Label
        self.lbl_code_meta = make_label("Clipboard empty", 9, "#38BDF8", mono=True)
        col.addWidget(self.lbl_code_meta)
        return card

    def _build_stealth_matrix_card(self):
        card = GlassCard()
        col = QVBoxLayout(card)
        col.setContentsMargins(18, 14, 18, 14)
        col.setSpacing(8)

        # Header Row
        hdr = QHBoxLayout()
        beacon = QLabel("●")
        beacon.setStyleSheet("color: #30D158; font-size: 10px; background: transparent;")
        hdr.addWidget(beacon)
        hdr.addWidget(make_label("Anti-Detection & Algorithmic Stealth Matrix", 12, "#FFFFFF", bold=True), 1)
        col.addLayout(hdr)

        # 2x2 Feature Grid
        grid = QGridLayout()
        grid.setSpacing(10)

        features = [
            ("🖱", "Simulated Cursor Wandering", "Subtle mouse drift with cubic easing defeats webcam gaze & mouse anomaly sensors", True, 0, 0),
            ("⚡", "Complexity Cadence Throttler", "Throttles to 35–50 WPM on nested DP & bitwise logic; fast on boilerplate", True, 0, 1),
            ("</>", "Incremental Code Construction", "Outlines signature stub first, then navigates back inside function", False, 1, 0),
            ("☰", "Selection & Refactoring Simulation", "Simulates Shift+Left selection & backspace replacement of variable", True, 1, 1),
        ]

        self.switches = {}
        for icon_char, title, desc, default_val, r, c in features:
            cell = QFrame()
            cell.setFixedHeight(54)
            cell.setStyleSheet("""
                QFrame {
                    background: rgba(10, 14, 22, 0.60);
                    border: 1px solid rgba(255, 255, 255, 0.09);
                    border-radius: 12px;
                }
            """)
            c_lay = QHBoxLayout(cell)
            c_lay.setContentsMargins(12, 6, 12, 6)
            c_lay.setSpacing(10)

            # Circular/Rounded Icon Box
            icon_box = QLabel(icon_char)
            icon_box.setFixedSize(32, 32)
            icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_box.setStyleSheet("""
                color: #FFFFFF;
                font-size: 13px;
                background: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 8px;
            """)
            c_lay.addWidget(icon_box)

            # Text
            t_col = QVBoxLayout()
            t_col.setContentsMargins(0, 0, 0, 0)
            t_col.setSpacing(2)
            t_col.addWidget(make_label(title, 9, "#FFFFFF", bold=True))
            d_lbl = make_label(desc, 8, "#94A3B8")
            d_lbl.setWordWrap(True)
            t_col.addWidget(d_lbl)
            c_lay.addLayout(t_col, 1)

            # Switch
            sw = IOSSwitch(checked=default_val)
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
        hero = GlassCard(elevated=True)
        h_lay = QVBoxLayout(hero)
        h_lay.setContentsMargins(18, 14, 18, 14)
        h_lay.setSpacing(8)

        h_top = QHBoxLayout()
        h_top.addWidget(make_label("⚡ Inhuman Mode (360 WPM)", 13, "#FFFFFF", bold=True))
        self.lbl_inhuman_badge = make_label("STANDBY", 9, "#94A3B8", bold=True, mono=True)
        self.lbl_inhuman_badge.setStyleSheet("""
            color: #94A3B8;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            padding: 3px 8px;
        """)
        h_top.addWidget(self.lbl_inhuman_badge)
        h_top.addStretch(1)

        self.btn_engage_360 = make_pill_button("⚡ Engage 360 WPM", primary=True)
        self.btn_engage_360.clicked.connect(self._engage_360_wpm)
        h_top.addWidget(self.btn_engage_360)

        self.sw_inhuman = IOSSwitch(checked=False)
        self.sw_inhuman.toggled.connect(self._on_inhuman_toggled)
        h_top.addWidget(self.sw_inhuman)
        h_lay.addLayout(h_top)

        h_desc = make_label(
            "Overclocks typing velocity to 360 WPM (~33.3ms inter-keystroke cadence) with adaptive 12ms micro-dwell dynamics to bypass OS queue choke and blast through speed tests.",
            9, "#CBD5E1"
        )
        h_desc.setWordWrap(True)
        h_lay.addWidget(h_desc)
        col.addWidget(hero)

        # Extended Velocity Fader Card
        fader_card = GlassCard()
        f_lay = QVBoxLayout(fader_card)
        f_lay.setContentsMargins(18, 14, 18, 14)
        f_lay.setSpacing(10)

        f_hdr = QHBoxLayout()
        f_hdr.addWidget(make_label("Typing Velocity", 12, "#FFFFFF", bold=True), 1)
        self.lbl_wpm_val = make_label("80 WPM", 11, "#FFFFFF", bold=True, mono=True)
        self.lbl_wpm_val.setStyleSheet("""
            color: #FFFFFF;
            background: rgba(255, 255, 255, 0.10);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 9px;
            padding: 3px 10px;
        """)
        f_hdr.addWidget(self.lbl_wpm_val)
        f_lay.addLayout(f_hdr)

        self.slider_wpm = QSlider(Qt.Orientation.Horizontal)
        self.slider_wpm.setRange(30, 360)
        self.slider_wpm.setValue(80)
        self.slider_wpm.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 5px;
                background: rgba(255, 255, 255, 0.12);
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D97706, stop:1 #F59E0B);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid rgba(255, 255, 255, 0.85);
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #F8FAFC;
            }
        """)
        self.slider_wpm.valueChanged.connect(self._on_wpm_slider_change)
        f_lay.addWidget(self.slider_wpm)

        f_sub = QHBoxLayout()
        f_sub.addWidget(make_label("30 (Relaxed)", 8, "#64748B"))
        f_sub.addWidget(make_label("80 (Human)", 8, "#64748B"))
        f_sub.addWidget(make_label("180 (Extreme)", 8, "#64748B"))
        f_sub.addStretch(1)
        f_sub.addWidget(make_label("⚡ 360 WPM (Inhuman)", 8, "#F59E0B", bold=True))
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
            btn.setFont(get_app_font(9, QFont.Weight.DemiBold if is_active else QFont.Weight.Normal))
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        color: #FFFFFF;
                        background: rgba(255, 255, 255, 0.16);
                        border: 1px solid rgba(255, 255, 255, 0.28);
                        border-radius: 14px;
                        padding: 0 14px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        color: #94A3B8;
                        background: transparent;
                        border: none;
                        padding: 0 12px;
                    }
                    QPushButton:hover {
                        color: #FFFFFF;
                        background: rgba(255, 255, 255, 0.08);
                        border-radius: 14px;
                    }
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
            self.lbl_wpm_val.setStyleSheet("""
                color: #FEF08A;
                background: rgba(245, 158, 11, 0.25);
                border: 1px solid #F59E0B;
                border-radius: 9px;
                padding: 3px 10px;
                font-weight: bold;
            """)
            self.lbl_inhuman_badge.setText("ACTIVE · 360 WPM")
            self.lbl_inhuman_badge.setStyleSheet("""
                color: #FEF08A;
                background: rgba(245, 158, 11, 0.25);
                border: 1px solid #F59E0B;
                border-radius: 8px;
                padding: 3px 8px;
                font-weight: bold;
            """)
        else:
            self.lbl_wpm_val.setText(f"{wpm} WPM")
            self.lbl_wpm_val.setStyleSheet("""
                color: #FFFFFF;
                background: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 9px;
                padding: 3px 10px;
            """)
            self.lbl_inhuman_badge.setText("STANDBY")
            self.lbl_inhuman_badge.setStyleSheet("""
                color: #94A3B8;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 3px 8px;
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
