"""
TYPO® — Studio Glass Edition (Apple visionOS & macOS Liquid Glass)
High-fidelity, responsive CustomTkinter UI for precision keystroke automation.

Engineered with:
- Warm Amber, Burnt Bronze & Mahogany Liquid Glass Palette
- Native Windows 10 & 11 Acrylic Frosted Blur via SetWindowCompositionAttribute & DWM
- Atmospheric illuminated background with softly blurred golden-amber light streaks
- Apple San Francisco typography hierarchy (Segoe UI & Consolas fallbacks)
- macOS Traffic Light window controls and floating capsule navigation
- Fluid 60 FPS linear interpolation (lerp) animation engine
- 100% full preservation of typing engine, hotkeys (Alt+Z+T, Esc), and anti-detection matrix
"""

import os
import sys
import time
import queue
import winsound
import ctypes
from ctypes import wintypes
from typing import Optional
import customtkinter as ctk
from PIL import Image

from typo.typing_engine import TypingEngine, EngineState
from typo.win32_api import GlobalHotKeyManager, PRIMARY_HOTKEY_LABEL
from typo.clipboard import get_current_clipboard, analyze_clipboard_content, set_test_clipboard_text

# ==========================================
# Apple Studio Glass Tokens & Color Space
# ==========================================
# Deep Obsidian & Atmospheric Warm Glass Bases
GLASS_BG = "#0D0907"               # Atmospheric obsidian liquid canvas
GLASS_SIDEBAR = "#140F0C"          # Frosted amber-glass sidebar bay
GLASS_SIDEBAR_BORDER = "#2C2016"   # Sidebar glass divider

# Frosted Glass Cards (Squircle Slices with Amber Specular Edges)
GLASS_CARD = "#19130F"             # Translucent frosted amber glass card
GLASS_CARD_HOVER = "#221A15"       # Elevated glass refraction on hover
GLASS_CARD_BORDER = "#423121"      # Specular glass bevel border (1px hairline)
GLASS_CARD_BORDER_GLOW = "#6B4E32" # Specular rim golden highlight

# Inset Glass Wells (Code Buffer & Slider Wells)
GLASS_INSET = "#100C09"            # Recessed dark glass well
GLASS_INSET_BORDER = "#261C14"     # Inset boundary

# Floating Glass Pill Bar & Capsules
GLASS_PILL_BAR = "#1A130E"         # Floating capsule bar
GLASS_PILL_BAR_BORDER = "#3A2A1C"  # Capsule bar rim
GLASS_PILL = "#201711"             # Standby capsule item
GLASS_PILL_BORDER = "#402E1E"
GLASS_PILL_ACTIVE = "#3E2818"      # Active Studio amber pill
GLASS_PILL_ACTIVE_BORDER = "#845427"

# Luminous Accents (Matching Reference Vision OS)
AMBER_GOLD = "#F59E0B"             # Radiant warm amber / beacon dot
AMBER_GOLD_BRIGHT = "#FCD34D"      # Golden text / thumb highlight
AMBER_PILL_BG = "#462913"          # 1.5% badge fill
AMBER_PILL_BORDER = "#8F5625"      # 1.5% badge border
AMBER_TRACK = "#D97706"            # Typo & Mistake slider progress

MAGENTA_ACCENT = "#E879F9"         # 3.0s badge highlight
MAGENTA_PILL_BG = "#421835"        # 3.0s badge fill
MAGENTA_PILL_BORDER = "#8B2E6E"    # 3.0s badge border
MAGENTA_TRACK = "#C026D3"          # Safety countdown slider progress

SLIDER_BG_TRACK = "#201711"        # Recessed slider background track

APPLE_GREEN = "#30D158"            # iOS / visionOS luminous switch green
APPLE_GREEN_GLOW = "#1A3D22"
APPLE_BLUE = "#38BDF8"             # Secondary telemetry blue
APPLE_CORAL = "#FF453A"            # Emergency abort coral red
APPLE_CORAL_GLOW = "#3A1719"

# Typography Colors
TEXT_PRIMARY = "#FFFFFF"           # Crisp pure white
TEXT_SECONDARY = "#C2B5A8"         # Warm secondary system text
TEXT_MUTED = "#736456"             # Muted annotations & technical indicators
TEXT_DIM = "#3E332A"               # Subtle glass grooves

# Typography Fonts (Apple San Francisco standard Windows fallbacks)
FONT_FAMILY = "Segoe UI"
FONT_MONO_FAMILY = "Consolas"

# Assets Directory
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
WALLPAPER_PATH = os.path.join(ASSETS_DIR, "glass_bg_amber.png")


# ==========================================
# Native Windows 10 & 11 Acrylic Blur Engine
# ==========================================
class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),      # 4 = ACCENT_ENABLE_ACRYLICBLURBEHIND, 3 = ACCENT_ENABLE_BLURBEHIND
        ("AccentFlags", ctypes.c_int),      # 2
        ("GradientColor", ctypes.c_int),    # ARGB (e.g. 0xCC0D0A08: CC alpha, 0D0A08 dark amber tint)
        ("AnimationId", ctypes.c_int),      # 0
    ]

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),        # WCA_ACCENT_POLICY = 19
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


def apply_native_glassmorphism(window):
    """
    Enables native hardware-accelerated Acrylic / Blur-behind on Windows 10 (1803+)
    and Windows 11, with immersive dark mode titlebar and smooth corner composition.
    """
    try:
        if not getattr(window, "winfo_exists", None) or not window.winfo_exists():
            return
        window.update_idletasks()
        inner_hwnd = window.winfo_id()
        top_hwnd = ctypes.windll.user32.GetAncestor(inner_hwnd, 2) or inner_hwnd

        # 1. Windows DWM Immersive Dark Mode (DWMWA_USE_IMMERSIVE_DARK_MODE = 20)
        dwmapi = ctypes.windll.dwmapi
        dark_val = ctypes.c_int(1)
        dwmapi.DwmSetWindowAttribute(top_hwnd, 20, ctypes.byref(dark_val), ctypes.sizeof(dark_val))

        # 2. Windows 11 Rounded Squircle Corners (DWMWCP_ROUND = 2) if supported
        round_val = ctypes.c_int(2)
        dwmapi.DwmSetWindowAttribute(top_hwnd, 33, ctypes.byref(round_val), ctypes.sizeof(round_val))

        # 3. Native Windows 10 & 11 Acrylic Frosted Glass Blur (SetWindowCompositionAttribute)
        if hasattr(ctypes.windll.user32, "SetWindowCompositionAttribute"):
            # AccentState = 4 (ACCENT_ENABLE_ACRYLICBLURBEHIND) with warm dark obsidian tint
            # 0xCC0D0907 -> alpha ~80%, RGB #0D0907
            policy = ACCENT_POLICY(4, 2, 0xCC0D0907, 0)
            data = WINDOWCOMPOSITIONATTRIBDATA(19, ctypes.addressof(policy), ctypes.sizeof(policy))
            res = ctypes.windll.user32.SetWindowCompositionAttribute(top_hwnd, ctypes.byref(data))
            if res != 1:
                # Fallback to standard blur behind if acrylic is disabled
                policy.AccentState = 3
                ctypes.windll.user32.SetWindowCompositionAttribute(top_hwnd, ctypes.byref(data))

        # 4. Set delicate window alpha for subtle frosted glass transparency
        window.wm_attributes("-alpha", 0.97)

    except Exception as e:
        print(f"[TYPO DWM] Glassmorphism initialization note: {e}")


# ==========================================
# Main Studio Glass Application
# ==========================================
class TypoApp(ctk.CTk):
    def __init__(self, init_hotkeys: bool = True):
        super().__init__()

        # Window Shell Configuration
        self.title("TYPO — Studio Glass Edition")
        self.geometry("1180x840")
        self.minsize(1020, 720)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=GLASS_BG)

        # Core Engine & Automation Pipeline
        self.engine = TypingEngine()
        self.hotkey_mgr: Optional[GlobalHotKeyManager] = None
        self.current_hotkey_label = PRIMARY_HOTKEY_LABEL
        self._ui_queue = queue.Queue()
        self._last_clipboard_fingerprint = None
        self._is_closing = False
        self._after_ids = set()
        self.sound_enabled = True
        self.ghost_hud = None
        self.active_tab = "Primary Studio"
        self.active_sidebar_nav = "Control Deck"

        # Smooth Animation Engine State (60 FPS Progress Lerp)
        self._target_progress = 0.0
        self._current_progress = 0.0

        # Bind Engine Callbacks
        self.engine.on_state_change = self._queue_state_change
        self.engine.on_progress = self._queue_progress
        self.engine.on_countdown = self._queue_countdown
        self.engine.on_error = self._queue_error

        # Build Studio Glass Layout (Illuminated Background + macOS Chrome + Sidebar + Fluid Workspace)
        self._build_main_shell()

        # Initialize Global Hotkey (Alt + Z + T)
        if init_hotkeys:
            self._init_hotkeys()

        # Scheduled Background Loops & 60 FPS Animation Ticker
        self._schedule(30, self._process_ui_queue)
        self._schedule(16, self._animate_tick)
        self._schedule(1000, self._periodic_clipboard_check)
        self._schedule(350, self._refresh_clipboard_view)
        self._schedule(120, lambda: apply_native_glassmorphism(self))

        # Clean Window Closure Protocol
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _schedule(self, delay: int, callback):
        """Schedules a Tkinter after timer with strict closure tracking to prevent memory leaks."""
        if getattr(self, "_is_closing", False) or not self.winfo_exists():
            return None
        after_id = None
        def wrapper():
            self._after_ids.discard(after_id)
            if not getattr(self, "_is_closing", False) and self.winfo_exists():
                callback()
        after_id = self.after(delay, wrapper)
        self._after_ids.add(after_id)
        return after_id

    def _animate_tick(self):
        """
        60 FPS Smooth Linear Interpolation (Lerp) Animation Ticker.
        Eases the progress bar with fluid liquid-glass inertia.
        """
        if getattr(self, "_is_closing", False) or not self.winfo_exists():
            return

        diff = self._target_progress - self._current_progress
        if abs(diff) > 0.0005:
            self._current_progress += diff * 0.20
            if hasattr(self, "progress_bar") and self.progress_bar.winfo_exists():
                self.progress_bar.set(self._current_progress)

        self._schedule(16, self._animate_tick)

    # ==========================================
    # Main Shell Architecture
    # ==========================================
    def _build_main_shell(self):
        # 0. Atmospheric Blurred Background Layer
        if os.path.exists(WALLPAPER_PATH):
            try:
                pil_bg = Image.open(WALLPAPER_PATH)
                self._bg_ctk = ctk.CTkImage(light_image=pil_bg, dark_image=pil_bg, size=(1920, 1200))
                self.bg_label = ctk.CTkLabel(self, image=self._bg_ctk, text="")
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception as e:
                print(f"[TYPO Assets] Wallpaper load warning: {e}")

        # Root Window Container (Pack above background)
        self.root_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.root_container.pack(fill="both", expand=True)

        # 1. macOS Style Titlebar & Window Chrome
        self._build_macos_titlebar()

        # 2. Main Horizontal Split (Sidebar + Workspace)
        self.content_container = ctk.CTkFrame(self.root_container, fg_color="transparent", corner_radius=0)
        self.content_container.pack(fill="both", expand=True)

        # 3. Frosted Glass Sidebar (Island Navigation)
        self._build_sidebar()

        # 4. Fluid Canvas Workspace (Vision OS Liquid Glass)
        self._build_workspace()

    # ==========================================
    # macOS Titlebar & Window Chrome
    # ==========================================
    def _build_macos_titlebar(self):
        self.title_bar = ctk.CTkFrame(
            self.root_container,
            height=40,
            fg_color="#120D0A",
            border_color="#261B12",
            border_width=1,
            corner_radius=0
        )
        self.title_bar.pack(fill="x")
        self.title_bar.pack_propagate(False)

        # macOS Traffic Light Buttons
        dots_box = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        dots_box.pack(side="left", padx=(16, 12))

        # Close Dot (Red)
        btn_close = ctk.CTkLabel(
            dots_box,
            text="",
            width=12,
            height=12,
            corner_radius=6,
            fg_color="#FF5F56",
            cursor="hand2"
        )
        btn_close.pack(side="left", padx=3)
        btn_close.bind("<Button-1>", lambda e: self._on_close())

        # Minimize Dot (Yellow)
        btn_min = ctk.CTkLabel(
            dots_box,
            text="",
            width=12,
            height=12,
            corner_radius=6,
            fg_color="#FFBD2E",
            cursor="hand2"
        )
        btn_min.pack(side="left", padx=3)
        btn_min.bind("<Button-1>", lambda e: self.iconify())

        # Maximize Dot (Green)
        btn_max = ctk.CTkLabel(
            dots_box,
            text="",
            width=12,
            height=12,
            corner_radius=6,
            fg_color="#27C93F",
            cursor="hand2"
        )
        btn_max.pack(side="left", padx=3)
        btn_max.bind("<Button-1>", lambda e: self._toggle_maximize())

        # App Icon Squircle Badge
        icon_badge = ctk.CTkFrame(
            self.title_bar,
            width=22,
            height=22,
            corner_radius=6,
            fg_color="#241912",
            border_color="#523924",
            border_width=1
        )
        icon_badge.pack(side="left", padx=(4, 8))
        icon_badge.pack_propagate(False)
        ctk.CTkLabel(
            icon_badge,
            text="T",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color="#FFFFFF"
        ).place(relx=0.5, rely=0.5, anchor="center")

        # Window Title Text
        ctk.CTkLabel(
            self.title_bar,
            text="TYPO — Studio Glass Edition",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color="#C4B9AD"
        ).pack(side="left")

        # Right Controls
        right_box = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        right_box.pack(side="right", padx=16)

        ctk.CTkLabel(
            right_box,
            text="—   □   ✕",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color="#6B5949"
        ).pack(side="right")

    def _toggle_maximize(self):
        try:
            if self.state() == "zoomed":
                self.state("normal")
            else:
                self.state("zoomed")
        except Exception:
            pass

    # ==========================================
    # Frosted Glass Sidebar (Island Navigation)
    # ==========================================
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.content_container,
            width=245,
            fg_color=GLASS_SIDEBAR,
            border_color=GLASS_SIDEBAR_BORDER,
            border_width=1,
            corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # 1. Profile Pill Box: TYPO STUDIO Vision Liquid Glass
        brand_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_box.pack(fill="x", padx=16, pady=(16, 12))

        profile_row = ctk.CTkFrame(
            brand_box,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=18,
            height=54
        )
        profile_row.pack(fill="x")
        profile_row.pack_propagate(False)

        # Avatar Icon Box
        avatar_box = ctk.CTkFrame(
            profile_row,
            width=36,
            height=36,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER_GLOW,
            border_width=1,
            corner_radius=12
        )
        avatar_box.pack(side="left", padx=(10, 10))
        avatar_box.pack_propagate(False)

        ctk.CTkLabel(
            avatar_box,
            text="🎛",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14),
            text_color=AMBER_GOLD
        ).place(relx=0.5, rely=0.5, anchor="center")

        user_text = ctk.CTkFrame(profile_row, fg_color="transparent")
        user_text.pack(side="left", fill="y", pady=8)

        ctk.CTkLabel(
            user_text,
            text="TYPO STUDIO",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=AMBER_GOLD
        ).pack(anchor="w")

        ctk.CTkLabel(
            user_text,
            text="Vision Liquid Glass",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        # Luminous Green Beacon Dot
        ctk.CTkLabel(
            profile_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=APPLE_GREEN
        ).pack(side="right", padx=(0, 14))

        # 2. Navigation Categories (Matching Image 2 Reference)
        self.nav_menu = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_menu.pack(fill="x", padx=14, pady=(6, 0))

        self.nav_items_widgets = {}

        # Category 1: CONTROL DECK
        self._add_nav_section_header("CONTROL DECK")
        self._add_nav_button("Control Deck", "⌂", True)

        # Category 2: PRECISION INPUT ENGINE
        self._add_nav_section_header("PRECISION INPUT ENGINE")
        self._add_nav_button("Live Chat", "💬", False)
        self._add_nav_button("Images", "🖼", False)

        # Category 3: SEQUENCER
        self._add_nav_section_header("SEQUENCER")
        self._add_nav_button("Sequencer Deck", "⊞", False, has_beacon=True)
        self._add_nav_button("Biometrics Lab", "⚡", False)

        # Category 4: TOOLS
        self._add_nav_section_header("TOOLS")
        self._add_nav_button("Code Memory", "🧠", False)
        self._add_nav_button("Session Telemetry", "📊", False)

        # 3. Bottom Hardware Hotkey Panel (Matching Image 2 Reference)
        bottom_box = ctk.CTkFrame(
            self.sidebar,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=18
        )
        bottom_box.pack(side="bottom", fill="x", padx=14, pady=16)

        ctk.CTkLabel(
            bottom_box,
            text="HARDWARE HOTKEY",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=14, pady=(12, 6))

        # Hotkey Badge: ⌥  Alt  +  Z  +  T
        lbl_hk = ctk.CTkLabel(
            bottom_box,
            text=f"⌥  {self.current_hotkey_label}",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=10,
            padx=12,
            pady=6
        )
        lbl_hk.pack(anchor="w", padx=14, pady=(0, 8))

        # Emergency Abort
        abort_lbl = ctk.CTkLabel(
            bottom_box,
            text="🛑 Emergency Abort [ Esc ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=APPLE_CORAL,
            cursor="hand2"
        )
        abort_lbl.pack(anchor="w", padx=14, pady=(0, 12))
        abort_lbl.bind("<Button-1>", lambda e: self._trigger_emergency_stop())

    def _add_nav_section_header(self, text: str):
        ctk.CTkLabel(
            self.nav_menu,
            text=text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=8, pady=(12, 4))

    def _add_nav_button(self, name: str, icon: str, is_active: bool, has_beacon: bool = False):
        bg_col = "#2B1E15" if is_active else "transparent"
        border_col = GLASS_CARD_BORDER_GLOW if is_active else GLASS_SIDEBAR
        border_w = 1 if is_active else 0
        text_col = TEXT_PRIMARY if is_active else TEXT_SECONDARY

        row = ctk.CTkFrame(
            self.nav_menu,
            fg_color=bg_col,
            border_color=border_col,
            border_width=border_w,
            corner_radius=12,
            height=36
        )
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        ctk.CTkLabel(
            row,
            text=icon,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=AMBER_GOLD if is_active else TEXT_MUTED
        ).pack(side="left", padx=(10, 8))

        lbl = ctk.CTkLabel(
            row,
            text=name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold" if is_active else "normal"),
            text_color=text_col,
            anchor="w",
            cursor="hand2"
        )
        lbl.pack(side="left", fill="both", expand=True)

        beacon_lbl = None
        if has_beacon or is_active:
            beacon_lbl = ctk.CTkLabel(
                row,
                text="●",
                font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                text_color=APPLE_GREEN if has_beacon else AMBER_GOLD
            )
            beacon_lbl.pack(side="right", padx=(0, 10))

        # Store widget references for dynamic switching
        self.nav_items_widgets[name] = {"frame": row, "label": lbl, "beacon": beacon_lbl}

        def on_click(e):
            self._select_sidebar_nav(name)

        row.bind("<Button-1>", on_click)
        lbl.bind("<Button-1>", on_click)

    def _select_sidebar_nav(self, nav_name: str):
        self.active_sidebar_nav = nav_name
        for name, item in self.nav_items_widgets.items():
            is_active = (name == nav_name)
            item["frame"].configure(
                fg_color="#2B1E15" if is_active else "transparent",
                border_color=GLASS_CARD_BORDER_GLOW if is_active else GLASS_SIDEBAR,
                border_width=1 if is_active else 0
            )
            item["label"].configure(
                text_color=TEXT_PRIMARY if is_active else TEXT_SECONDARY,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold" if is_active else "normal")
            )
        # Switch tab or scroll view
        if nav_name in ("Control Deck", "Sequencer Deck"):
            self._select_tab("Primary Studio")
        elif nav_name == "Biometrics Lab":
            self._select_tab("Biometrics")
        elif nav_name == "Code Memory":
            self._select_tab("Code Buffer")
        elif nav_name == "Session Telemetry":
            self._select_tab("Telemetry Log")

    # ==========================================
    # Fluid Canvas Workspace
    # ==========================================
    def _build_workspace(self):
        self.workspace = ctk.CTkFrame(self.content_container, fg_color="transparent", corner_radius=0)
        self.workspace.pack(side="right", fill="both", expand=True)

        # 1. Header Bar: Subtitle + Title + Status Pills
        self._build_header_bar()

        # 2. Floating Liquid Glass Capsule Navigation Bar
        self._build_capsule_bar()

        # 3. Responsive Scrollable Deck Body
        self.body_scroll = ctk.CTkScrollableFrame(
            self.workspace,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#261B12",
            scrollbar_button_hover_color="#433121"
        )
        self.body_scroll.pack(fill="both", expand=True, padx=22, pady=(0, 16))

        # Build Deck Cards
        self._build_execution_status_card()
        self._build_sliders_row_cards()
        self._build_code_buffer_card()
        self._build_stealth_matrix_card()
        self._build_biometrics_deck_card()

    # ==========================================
    # Header Bar: Title & Top Action Pills
    # ==========================================
    def _build_header_bar(self):
        bar = ctk.CTkFrame(self.workspace, fg_color="transparent", height=56)
        bar.pack(fill="x", padx=22, pady=(14, 8))
        bar.pack_propagate(False)

        left_titles = ctk.CTkFrame(bar, fg_color="transparent")
        left_titles.pack(side="left")

        ctk.CTkLabel(
            left_titles,
            text="VISION OS // AUTOMATION STUDIO",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=AMBER_GOLD
        ).pack(anchor="w")

        self.lbl_view_title = ctk.CTkLabel(
            left_titles,
            text="Control Deck · Dynamic Glass Sequencer",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.lbl_view_title.pack(anchor="w", pady=(1, 0))

        # Right Action Capsule Pills
        right_pills = ctk.CTkFrame(bar, fg_color="transparent")
        right_pills.pack(side="right")

        # 1. Liquid Glass Pill (Far right)
        lens_pill = ctk.CTkFrame(
            right_pills,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER_GLOW,
            border_width=1,
            corner_radius=18,
            height=36
        )
        lens_pill.pack(side="right", padx=(8, 0))
        ctk.CTkLabel(
            lens_pill,
            text="💧 Liquid Glass",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=AMBER_GOLD_BRIGHT,
            padx=14,
            pady=6
        ).pack()

        # 2. Ghost HUD Button Pill
        self.btn_ghost_hud = ctk.CTkButton(
            right_pills,
            text="👻 Ghost HUD",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=36,
            corner_radius=18,
            fg_color=GLASS_CARD,
            hover_color=GLASS_CARD_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._toggle_ghost_hud
        )
        self.btn_ghost_hud.pack(side="right", padx=(8, 0))

        # 3. Audio On / Off Pill
        self.btn_sound = ctk.CTkButton(
            right_pills,
            text="🔊 Audio On",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=36,
            corner_radius=18,
            fg_color=GLASS_CARD,
            hover_color=GLASS_CARD_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._toggle_sound
        )
        self.btn_sound.pack(side="right", padx=(8, 0))

        # 4. Target Window Pill
        target_frame = ctk.CTkFrame(
            right_pills,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=18,
            height=36
        )
        target_frame.pack(side="right")

        self.lbl_target_dot = ctk.CTkLabel(
            target_frame,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=APPLE_GREEN
        )
        self.lbl_target_dot.pack(side="left", padx=(12, 4))

        self.lbl_target_window = ctk.CTkLabel(
            target_frame,
            text="Target: Standby",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY
        )
        self.lbl_target_window.pack(side="left", padx=(0, 14), pady=6)

    # ==========================================
    # Floating Liquid Glass Capsule Bar
    # ==========================================
    def _build_capsule_bar(self):
        capsule_bar = ctk.CTkFrame(
            self.workspace,
            height=48,
            fg_color=GLASS_PILL_BAR,
            border_color=GLASS_PILL_BAR_BORDER,
            border_width=1,
            corner_radius=24
        )
        capsule_bar.pack(fill="x", padx=22, pady=(0, 14))
        capsule_bar.pack_propagate(False)

        caps_inner = ctk.CTkFrame(capsule_bar, fg_color="transparent")
        caps_inner.pack(fill="both", expand=True, padx=6, pady=4)

        # Plus (+) Circle Button
        add_btn = ctk.CTkLabel(
            caps_inner,
            text="+",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=20,
            width=40,
            height=40,
            cursor="hand2"
        )
        add_btn.pack(side="left", padx=(2, 8))
        add_btn.bind("<Button-1>", lambda e: self._load_sample_code())

        # Pill Tabs Matching Image 2
        tabs = [
            ("Primary Studio", True),
            ("Biometrics", False),
            ("Code Buffer", False),
            ("Telemetry Log", False),
            ("Anti-Gaze", False),
        ]

        self.tab_widgets = {}

        for tab_name, is_active in tabs:
            pill_frame = ctk.CTkFrame(
                caps_inner,
                fg_color=GLASS_PILL_ACTIVE if is_active else "transparent",
                border_color=GLASS_PILL_ACTIVE_BORDER if is_active else GLASS_PILL_BAR,
                border_width=1 if is_active else 0,
                corner_radius=20,
                height=40
            )
            pill_frame.pack(side="left", padx=3)

            dot_lbl = None
            if is_active:
                dot_lbl = ctk.CTkLabel(
                    pill_frame,
                    text="●",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=AMBER_GOLD
                )
                dot_lbl.pack(side="left", padx=(12, 4))

            txt_lbl = ctk.CTkLabel(
                pill_frame,
                text=tab_name,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold" if is_active else "normal"),
                text_color=TEXT_PRIMARY if is_active else TEXT_SECONDARY,
                cursor="hand2"
            )
            padx_right = 14 if is_active else 12
            padx_left = 0 if is_active else 12
            txt_lbl.pack(side="left", padx=(padx_left, padx_right), pady=8)

            self.tab_widgets[tab_name] = {
                "frame": pill_frame,
                "label": txt_lbl,
                "dot": dot_lbl
            }

            def make_tab_handler(tname):
                return lambda e: self._select_tab(tname)

            pill_frame.bind("<Button-1>", make_tab_handler(tab_name))
            txt_lbl.bind("<Button-1>", make_tab_handler(tab_name))

    def _select_tab(self, selected_tab: str):
        self.active_tab = selected_tab
        for tname, w in self.tab_widgets.items():
            is_active = (tname == selected_tab)
            w["frame"].configure(
                fg_color=GLASS_PILL_ACTIVE if is_active else "transparent",
                border_color=GLASS_PILL_ACTIVE_BORDER if is_active else GLASS_PILL_BAR,
                border_width=1 if is_active else 0
            )
            w["label"].configure(
                text_color=TEXT_PRIMARY if is_active else TEXT_SECONDARY,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold" if is_active else "normal")
            )
            if w.get("dot"):
                if is_active:
                    w["dot"].pack(side="left", padx=(12, 4), before=w["label"])
                else:
                    w["dot"].pack_forget()

        # Update view title
        self.lbl_view_title.configure(text=f"Control Deck · {selected_tab}")

        # Show/hide relevant cards
        if selected_tab == "Primary Studio":
            self.sliders_card.pack(fill="x", pady=(0, 16))
            self.code_buffer_card.pack(fill="x", pady=(0, 16))
            self.matrix_card.pack(fill="x", pady=(0, 16))
            self.biometrics_card.pack_forget()
        elif selected_tab == "Biometrics":
            self.sliders_card.pack(fill="x", pady=(0, 16))
            self.biometrics_card.pack(fill="x", pady=(0, 16))
            self.code_buffer_card.pack_forget()
            self.matrix_card.pack_forget()
        elif selected_tab == "Code Buffer":
            self.code_buffer_card.pack(fill="x", pady=(0, 16))
            self.sliders_card.pack_forget()
            self.matrix_card.pack_forget()
            self.biometrics_card.pack_forget()
        elif selected_tab in ("Telemetry Log", "Anti-Gaze"):
            self.sliders_card.pack(fill="x", pady=(0, 16))
            self.matrix_card.pack(fill="x", pady=(0, 16))
            self.code_buffer_card.pack_forget()
            self.biometrics_card.pack_forget()

    # ==========================================
    # 1. Execution & Telemetry Glass Strip
    # ==========================================
    def _build_execution_status_card(self):
        self.exec_card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=22
        )
        self.exec_card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(self.exec_card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        # Top Control Row
        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 12))

        # Left Status Pill & Description
        status_box = ctk.CTkFrame(top_row, fg_color="transparent")
        status_box.pack(side="left")

        self.status_pill = ctk.CTkLabel(
            status_box,
            text="● Ready",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color="#241B13",
            border_color=GLASS_CARD_BORDER_GLOW,
            border_width=1,
            corner_radius=14,
            padx=14,
            pady=5
        )
        self.status_pill.pack(side="left")

        self.status_desc_lbl = ctk.CTkLabel(
            status_box,
            text=f"Focus your target editor and press {self.current_hotkey_label}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY
        )
        self.status_desc_lbl.pack(side="left", padx=12)

        # Right Action Buttons
        act_box = ctk.CTkFrame(top_row, fg_color="transparent")
        act_box.pack(side="right")

        self.btn_start = ctk.CTkButton(
            act_box,
            text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            height=38,
            corner_radius=19,
            fg_color=AMBER_GOLD,
            hover_color=AMBER_GOLD_BRIGHT,
            text_color="#000000",
            command=self._trigger_start
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_pause = ctk.CTkButton(
            act_box,
            text="⏸ Pause",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            height=38,
            width=80,
            corner_radius=19,
            fg_color="#241B13",
            hover_color="#36281D",
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            text_color=TEXT_MUTED,
            state="disabled",
            command=self._trigger_pause_resume
        )
        self.btn_pause.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            act_box,
            text="■ Esc / Abort",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            height=38,
            width=100,
            corner_radius=19,
            fg_color=APPLE_CORAL_GLOW,
            hover_color="#4F1D20",
            border_color=APPLE_CORAL,
            border_width=1,
            text_color=APPLE_CORAL,
            command=self._trigger_emergency_stop
        )
        self.btn_stop.pack(side="left")

        # 60 FPS Fluid Linear Interpolated Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            inner,
            height=6,
            corner_radius=3,
            fg_color=SLIDER_BG_TRACK,
            progress_color=AMBER_GOLD
        )
        self.progress_bar.pack(fill="x", pady=(2, 14))
        self.progress_bar.set(0.0)

        # 4-Column Live Telemetry Counter Grid
        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # 1. Progress
        c1 = ctk.CTkFrame(grid, fg_color=GLASS_INSET, corner_radius=14, border_color=GLASS_INSET_BORDER, border_width=1)
        c1.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=2)
        ctk.CTkLabel(c1, text="PROGRESS", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(8, 2))
        self.lbl_tele_progress = ctk.CTkLabel(c1, text="0 / 0 (0%)", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_tele_progress.pack(anchor="w", padx=14, pady=(0, 8))

        # 2. Velocity
        c2 = ctk.CTkFrame(grid, fg_color=GLASS_INSET, corner_radius=14, border_color=GLASS_INSET_BORDER, border_width=1)
        c2.grid(row=0, column=1, sticky="ew", padx=3, pady=2)
        ctk.CTkLabel(c2, text="VELOCITY", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(8, 2))
        self.lbl_tele_speed = ctk.CTkLabel(c2, text="80.0 WPM", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=AMBER_GOLD)
        self.lbl_tele_speed.pack(anchor="w", padx=14, pady=(0, 8))

        # 3. Elapsed / Remain
        c3 = ctk.CTkFrame(grid, fg_color=GLASS_INSET, corner_radius=14, border_color=GLASS_INSET_BORDER, border_width=1)
        c3.grid(row=0, column=2, sticky="ew", padx=3, pady=2)
        ctk.CTkLabel(c3, text="ELAPSED / REMAIN", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(8, 2))
        self.lbl_tele_time = ctk.CTkLabel(c3, text="00:00 / 00:00", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_tele_time.pack(anchor="w", padx=14, pady=(0, 8))

        # 4. Token & Biometric Dwell
        c4 = ctk.CTkFrame(grid, fg_color=GLASS_INSET, corner_radius=14, border_color=GLASS_INSET_BORDER, border_width=1)
        c4.grid(row=0, column=3, sticky="ew", padx=(5, 0), pady=2)
        ctk.CTkLabel(c4, text="LAST TOKEN // DWELL", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(8, 2))
        self.lbl_tele_token = ctk.CTkLabel(c4, text="[ ↵ ] ~55ms", font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=13, weight="bold"), text_color=APPLE_BLUE)
        self.lbl_tele_token.pack(anchor="w", padx=14, pady=(0, 8))

    # ==========================================
    # 2. Precision Faders Cards (Typo Rate & Safety Countdown)
    # Matching Reference Image 2 Side-by-Side Sliders
    # ==========================================
    def _build_sliders_row_cards(self):
        self.sliders_card = ctk.CTkFrame(self.body_scroll, fg_color="transparent")
        self.sliders_card.pack(fill="x", pady=(0, 16))
        self.sliders_card.grid_columnconfigure((0, 1), weight=1)

        # ------------------------------------------
        # Left Slider Card: Typo & Mistake Rate (Amber)
        # ------------------------------------------
        card_typo = ctk.CTkFrame(
            self.sliders_card,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=22
        )
        card_typo.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        inner_typo = ctk.CTkFrame(card_typo, fg_color="transparent")
        inner_typo.pack(fill="both", expand=True, padx=20, pady=18)

        # Header: Title + Amber 1.5% Badge
        hdr_typo = ctk.CTkFrame(inner_typo, fg_color="transparent")
        hdr_typo.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            hdr_typo,
            text="Typo & Mistake Rate",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        self.lbl_mistake_val = ctk.CTkLabel(
            hdr_typo,
            text="1.5%",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=12, weight="bold"),
            text_color=AMBER_GOLD_BRIGHT,
            fg_color=AMBER_PILL_BG,
            border_color=AMBER_PILL_BORDER,
            border_width=1,
            corner_radius=10,
            padx=12,
            pady=3
        )
        self.lbl_mistake_val.pack(side="right")

        # Custom Slider (Amber Glow Track)
        self.slider_mistake = ctk.CTkSlider(
            inner_typo,
            from_=0.0,
            to=0.05,
            number_of_steps=50,
            fg_color=SLIDER_BG_TRACK,
            progress_color=AMBER_TRACK,
            button_color=AMBER_GOLD_BRIGHT,
            button_hover_color="#FDE68A",
            command=self._on_mistake_rate_change
        )
        self.slider_mistake.set(0.015)
        self.slider_mistake.pack(fill="x", pady=(8, 10))

        # Scale Annotations
        sub_typo = ctk.CTkFrame(inner_typo, fg_color="transparent")
        sub_typo.pack(fill="x")
        ctk.CTkLabel(sub_typo, text="0.0% (Flawless)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(sub_typo, text="5.0% (Natural Typos)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="right")

        # ------------------------------------------
        # Right Slider Card: Safety Focus Countdown (Magenta)
        # ------------------------------------------
        card_safety = ctk.CTkFrame(
            self.sliders_card,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=22
        )
        card_safety.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        inner_safety = ctk.CTkFrame(card_safety, fg_color="transparent")
        inner_safety.pack(fill="both", expand=True, padx=20, pady=18)

        # Header: Title + Magenta 3.0s Badge
        hdr_safety = ctk.CTkFrame(inner_safety, fg_color="transparent")
        hdr_safety.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            hdr_safety,
            text="Safety Focus Countdown",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        self.lbl_delay_val = ctk.CTkLabel(
            hdr_safety,
            text="3.0s",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=12, weight="bold"),
            text_color=MAGENTA_ACCENT,
            fg_color=MAGENTA_PILL_BG,
            border_color=MAGENTA_PILL_BORDER,
            border_width=1,
            corner_radius=10,
            padx=12,
            pady=3
        )
        self.lbl_delay_val.pack(side="right")

        # Custom Slider (Magenta Glow Track)
        self.slider_delay = ctk.CTkSlider(
            inner_safety,
            from_=1.0,
            to=8.0,
            number_of_steps=70,
            fg_color=SLIDER_BG_TRACK,
            progress_color=MAGENTA_TRACK,
            button_color=MAGENTA_ACCENT,
            button_hover_color="#F9A8D4",
            command=self._on_delay_change
        )
        self.slider_delay.set(3.0)
        self.slider_delay.pack(fill="x", pady=(8, 10))

        # Scale Annotations
        sub_safety = ctk.CTkFrame(inner_safety, fg_color="transparent")
        sub_safety.pack(fill="x")
        ctk.CTkLabel(sub_safety, text="1.0s (Fast Switch)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(sub_safety, text="8.0s (Relaxed)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="right")

    # ==========================================
    # 3. Live Code Buffer & Non-Destructive Inspection
    # Matching Reference Image 2
    # ==========================================
    def _build_code_buffer_card(self):
        self.code_buffer_card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=22
        )
        self.code_buffer_card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(self.code_buffer_card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=18)

        # Header Row
        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            hdr,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=APPLE_GREEN
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hdr,
            text="Live Code Buffer & Non-Destructive Inspection",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        # Action Buttons: Refresh & Load Sample Code
        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.pack(side="right")

        btn_sample = ctk.CTkButton(
            btn_box,
            text="📁 Load Sample Code",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=32,
            corner_radius=16,
            fg_color="#241B13",
            hover_color="#36281D",
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._load_sample_code
        )
        btn_sample.pack(side="right", padx=(8, 0))

        btn_refresh = ctk.CTkButton(
            btn_box,
            text="⟳ Refresh",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=32,
            width=76,
            corner_radius=16,
            fg_color="#241B13",
            hover_color="#36281D",
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._refresh_clipboard_view
        )
        btn_refresh.pack(side="right")

        # Monospace Inset Code Textbox
        self.clip_textbox = ctk.CTkTextbox(
            inner,
            height=135,
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=12),
            fg_color=GLASS_INSET,
            text_color="#E2D9CE",
            border_color=GLASS_INSET_BORDER,
            border_width=1,
            corner_radius=14,
            wrap="none"
        )
        self.clip_textbox.pack(fill="x", pady=(2, 10))

        # Bottom Status / Metadata
        self.lbl_clip_meta = ctk.CTkLabel(
            inner,
            text="Clipboard empty",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=AMBER_GOLD
        )
        self.lbl_clip_meta.pack(anchor="w")

    # ==========================================
    # 4. Anti-Detection & Algorithmic Stealth Matrix
    # Matching Reference Image 2 (4 Primary Feature Cards with Switches)
    # ==========================================
    def _build_stealth_matrix_card(self):
        self.matrix_card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=22
        )
        self.matrix_card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(self.matrix_card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=18)

        # Header Row
        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            hdr,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=APPLE_GREEN
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hdr,
            text="Anti-Detection & Algorithmic Stealth Matrix",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        # 2x2 Feature Grid (Matching Reference Image 2 Exactly)
        matrix_grid = ctk.CTkFrame(inner, fg_color="transparent")
        matrix_grid.pack(fill="x")
        matrix_grid.grid_columnconfigure((0, 1), weight=1)

        features = [
            (
                "Simulated Cursor Wandering",
                "Subtle mouse drift with cubic easing defeats webcam gaze & mouse anomaly sensors",
                "🖱",
                self._on_toggle_cursor_wandering,
                True,
                0, 0
            ),
            (
                "Complexity Cadence Throttler",
                "Throttles to 35–50 WPM on nested DP & bitwise logic; fast on boilerplate",
                "⑂",
                self._on_toggle_complexity_throttler,
                True,
                0, 1
            ),
            (
                "Incremental Code Construction",
                "Outlines signature stub first, then navigates back inside function",
                "⟨/⟩",
                self._on_toggle_incremental,
                False,
                1, 0
            ),
            (
                "Selection & Refactoring Simulation",
                "Simulates Shift+Left selection & backspace replacement of variable",
                "≣",
                self._on_toggle_refactoring,
                True,
                1, 1
            ),
        ]

        self.switches = {}

        for title, desc, icon, callback, default_val, row, col in features:
            padx = (0, 6) if col == 0 else (6, 0)
            cell = ctk.CTkFrame(
                matrix_grid,
                fg_color=GLASS_INSET,
                border_color=GLASS_INSET_BORDER,
                border_width=1,
                corner_radius=16
            )
            cell.grid(row=row, column=col, sticky="nsew", padx=padx, pady=5)

            c_inner = ctk.CTkFrame(cell, fg_color="transparent")
            c_inner.pack(fill="both", expand=True, padx=14, pady=12)

            # Left Icon Circle Box
            icon_box = ctk.CTkFrame(
                c_inner,
                width=38,
                height=38,
                fg_color="#241912",
                border_color="#4A3423",
                border_width=1,
                corner_radius=19
            )
            icon_box.pack(side="left", padx=(0, 12))
            icon_box.pack_propagate(False)

            ctk.CTkLabel(
                icon_box,
                text=icon,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=AMBER_GOLD
            ).place(relx=0.5, rely=0.5, anchor="center")

            # Center Text (Title + Desc)
            text_box = ctk.CTkFrame(c_inner, fg_color="transparent")
            text_box.pack(side="left", fill="both", expand=True)

            ctk.CTkLabel(
                text_box,
                text=title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=TEXT_PRIMARY
            ).pack(anchor="w")

            ctk.CTkLabel(
                text_box,
                text=desc,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED,
                wraplength=280,
                justify="left"
            ).pack(anchor="w", pady=(2, 0))

            # Right iOS Style Switch
            sw = ctk.CTkSwitch(
                c_inner,
                text="",
                width=42,
                height=22,
                switch_width=38,
                switch_height=20,
                progress_color=APPLE_GREEN,
                button_color=TEXT_PRIMARY,
                command=callback
            )
            sw.pack(side="right", padx=(8, 0))
            if default_val:
                sw.select()
            else:
                sw.deselect()
            self.switches[title] = sw

    # ==========================================
    # 5. Biometrics & Cadence Extended Deck Card
    # ==========================================
    def _build_biometrics_deck_card(self):
        self.biometrics_card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=22
        )
        # Not packed by default (visible when Biometrics tab is chosen)

        inner = ctk.CTkFrame(self.biometrics_card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=18)

        # Header
        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            hdr,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=AMBER_GOLD
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hdr,
            text="Biometrics & Cadence Velocity Faders",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        # Two Faders: Velocity WPM & Jitter Variance
        f_grid = ctk.CTkFrame(inner, fg_color="transparent")
        f_grid.pack(fill="x")
        f_grid.grid_columnconfigure((0, 1), weight=1)

        # WPM Fader
        f1 = ctk.CTkFrame(f_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=16)
        f1.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)
        f1_h = ctk.CTkFrame(f1, fg_color="transparent")
        f1_h.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(f1_h, text="Typing Velocity", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        self.lbl_wpm_val = ctk.CTkLabel(
            f1_h,
            text="80 WPM",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=11, weight="bold"),
            text_color=AMBER_GOLD,
            fg_color=AMBER_PILL_BG,
            border_color=AMBER_PILL_BORDER,
            border_width=1,
            corner_radius=8,
            padx=8,
            pady=2
        )
        self.lbl_wpm_val.pack(side="right")

        self.slider_wpm = ctk.CTkSlider(
            f1,
            from_=30,
            to=180,
            number_of_steps=150,
            fg_color=SLIDER_BG_TRACK,
            progress_color=AMBER_GOLD,
            button_color=AMBER_GOLD_BRIGHT,
            button_hover_color="#FDE68A",
            command=self._on_wpm_change
        )
        self.slider_wpm.set(80)
        self.slider_wpm.pack(fill="x", padx=14, pady=(4, 6))

        # Jitter Fader
        f2 = ctk.CTkFrame(f_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=16)
        f2.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=4)
        f2_h = ctk.CTkFrame(f2, fg_color="transparent")
        f2_h.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(f2_h, text="Human Cadence Jitter", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        self.lbl_jitter_val = ctk.CTkLabel(
            f2_h,
            text="25%",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=11, weight="bold"),
            text_color=APPLE_BLUE,
            fg_color="#182A3A",
            border_color="#2E4F70",
            border_width=1,
            corner_radius=8,
            padx=8,
            pady=2
        )
        self.lbl_jitter_val.pack(side="right")

        self.slider_jitter = ctk.CTkSlider(
            f2,
            from_=0.0,
            to=0.60,
            number_of_steps=60,
            fg_color=SLIDER_BG_TRACK,
            progress_color=APPLE_BLUE,
            button_color=APPLE_BLUE,
            button_hover_color="#7DD3FC",
            command=self._on_jitter_change
        )
        self.slider_jitter.set(0.25)
        self.slider_jitter.pack(fill="x", padx=14, pady=(4, 6))

        # Additional Stealth Switches
        addl_sw_box = ctk.CTkFrame(inner, fg_color="transparent")
        addl_sw_box.pack(fill="x", pady=(12, 0))
        addl_sw_box.grid_columnconfigure((0, 1), weight=1)

        extra_features = [
            ("Target Focus Guard", "Auto-pauses typing if target editor window loses focus", self._on_toggle_focus, True, 0, 0),
            ("Smart Auto-Indent & Dedent Sync", "Zero spacebars for code indent; syncs with editor indentation", self._on_toggle_bracket_neutralizer, True, 0, 1),
            ("Biometric Keystroke Dynamics", "Non-uniform Gaussian dwell times (~55ms) bypass virtual key detection", self._on_toggle_biometrics, True, 1, 0),
            ("Autonomous Mistake Injection", "Types adjacent QWERTY keys with human hesitation & backspace recovery", self._on_toggle_mistakes, True, 1, 1),
        ]

        for title, desc, callback, default_val, r, c in extra_features:
            px = (0, 6) if c == 0 else (6, 0)
            c_frame = ctk.CTkFrame(addl_sw_box, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=14)
            c_frame.grid(row=r, column=c, sticky="ew", padx=px, pady=4)

            top_l = ctk.CTkFrame(c_frame, fg_color="transparent")
            top_l.pack(fill="x", padx=12, pady=(10, 2))

            ctk.CTkLabel(top_l, text=title, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

            sw = ctk.CTkSwitch(
                top_l,
                text="",
                width=42,
                height=22,
                switch_width=38,
                switch_height=20,
                progress_color=APPLE_GREEN,
                button_color=TEXT_PRIMARY,
                command=callback
            )
            sw.pack(side="right")
            if default_val:
                sw.select()
            else:
                sw.deselect()
            self.switches[title] = sw

            ctk.CTkLabel(c_frame, text=desc, font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED, wraplength=280, justify="left").pack(anchor="w", padx=12, pady=(0, 10))

    # ==========================================
    # Hotkey & Event Handlers
    # ==========================================
    def _init_hotkeys(self):
        try:
            self.hotkey_mgr = GlobalHotKeyManager(callback=self._on_hotkey_triggered)
            self.hotkey_mgr.start()
        except Exception as e:
            print(f"[TYPO Hotkey] Global Hotkey Manager init warning: {e}")

    def _on_hotkey_triggered(self):
        self._ui_queue.put(("hotkey_pressed", {}))

    def _on_wpm_change(self, val):
        wpm = round(float(val))
        self.engine.wpm = float(wpm)
        if hasattr(self, "lbl_wpm_val"):
            self.lbl_wpm_val.configure(text=f"{wpm} WPM")
        self.lbl_tele_speed.configure(text=f"{wpm:.1f} WPM")

    def _on_jitter_change(self, val):
        jitter = float(val)
        self.engine.variance = jitter
        if hasattr(self, "lbl_jitter_val"):
            self.lbl_jitter_val.configure(text=f"{int(jitter * 100)}%")

    def _on_mistake_rate_change(self, val):
        rate = float(val)
        self.engine.mistake_rate = rate
        self.lbl_mistake_val.configure(text=f"{rate * 100:.1f}%")

    def _on_delay_change(self, val):
        delay = float(val)
        self.engine.safety_delay = delay
        self.lbl_delay_val.configure(text=f"{delay:.1f}s")

    def _on_toggle_cursor_wandering(self):
        self.engine.cursor_wandering_enabled = bool(self.switches["Simulated Cursor Wandering"].get())

    def _on_toggle_complexity_throttler(self):
        self.engine.complexity_throttler_enabled = bool(self.switches["Complexity Cadence Throttler"].get())

    def _on_toggle_incremental(self):
        self.engine.incremental_construction_mode = bool(self.switches["Incremental Code Construction"].get())

    def _on_toggle_refactoring(self):
        self.engine.refactoring_simulation_enabled = bool(self.switches["Selection & Refactoring Simulation"].get())

    def _on_toggle_focus(self):
        self.engine.auto_pause_on_focus_loss = bool(self.switches["Target Focus Guard"].get())

    def _on_toggle_bracket_neutralizer(self):
        enabled = bool(self.switches["Smart Auto-Indent & Dedent Sync"].get())
        self.engine.smart_auto_indent = enabled
        self.engine.neutralize_auto_closing_brackets = enabled

    def _on_toggle_biometrics(self):
        self.engine.biometric_dynamics_enabled = bool(self.switches["Biometric Keystroke Dynamics"].get())

    def _on_toggle_mistakes(self):
        self.engine.mistake_injection_enabled = bool(self.switches["Autonomous Mistake Injection"].get())

    def _toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        if self.sound_enabled:
            self.btn_sound.configure(text="🔊 Audio On", text_color=TEXT_PRIMARY)
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass
        else:
            self.btn_sound.configure(text="🔇 Audio Off", text_color=TEXT_MUTED)

    def _toggle_ghost_hud(self):
        from typo.ghost_hud import GhostHUD
        if self.ghost_hud is None or not self.ghost_hud.winfo_exists():
            self.ghost_hud = GhostHUD(self, on_close_callback=self._on_ghost_hud_closed)
            self.ghost_hud.show_hud()
            self.btn_ghost_hud.configure(text="👻 Hide HUD", fg_color=GLASS_PILL_ACTIVE, border_color=GLASS_PILL_ACTIVE_BORDER)
        else:
            if self.ghost_hud.winfo_viewable():
                self.ghost_hud.hide_hud()
                self.btn_ghost_hud.configure(text="👻 Ghost HUD", fg_color=GLASS_CARD, border_color=GLASS_CARD_BORDER)
            else:
                self.ghost_hud.show_hud()
                self.btn_ghost_hud.configure(text="👻 Hide HUD", fg_color=GLASS_PILL_ACTIVE, border_color=GLASS_PILL_ACTIVE_BORDER)

    def _on_ghost_hud_closed(self):
        if hasattr(self, "btn_ghost_hud") and self.btn_ghost_hud.winfo_exists():
            self.btn_ghost_hud.configure(text="👻 Ghost HUD", fg_color=GLASS_CARD, border_color=GLASS_CARD_BORDER)

    def _trigger_start(self):
        self.engine.trigger_from_clipboard()

    def _trigger_pause_resume(self):
        self.engine.toggle_pause()

    def _trigger_emergency_stop(self):
        self.engine.stop()

    def _load_sample_code(self):
        sample = (
            'class Solution {\n'
            'public:\n'
            '    vector<int> twoSum(vector<int>& nums, int target) {\n'
            '        unordered_map<int, int> seen;\n'
            '        for (int i = 0; i < nums.size(); ++i) {\n'
            '            int complement = target - nums[i];\n'
            '            if (seen.count(complement)) {\n'
            '                return {seen[complement], i};\n'
            '            }\n'
            '            seen[nums[i]] = i;\n'
            '        }\n'
            '        return {};\n'
            '    }\n'
            '};'
        )
        set_test_clipboard_text(sample)
        self._refresh_clipboard_view()
        if self.sound_enabled:
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _periodic_clipboard_check(self):
        if getattr(self, "_is_closing", False) or not self.winfo_exists():
            return
        if self.engine.state == EngineState.IDLE:
            text, is_empty, err_msg = get_current_clipboard()
            fp = (len(text), hash(text[:1024]), hash(text[-1024:]) if len(text) > 1024 else 0)
            if fp != self._last_clipboard_fingerprint:
                self._last_clipboard_fingerprint = fp
                self._update_clipboard_display(text, is_empty, err_msg)
        if not getattr(self, "_is_closing", False) and self.winfo_exists():
            self._schedule(1000, self._periodic_clipboard_check)

    def _refresh_clipboard_view(self):
        if getattr(self, "_is_closing", False) or not self.winfo_exists():
            return
        text, is_empty, err_msg = get_current_clipboard()
        self._last_clipboard_fingerprint = (len(text), hash(text[:1024]), hash(text[-1024:]) if len(text) > 1024 else 0)
        self._update_clipboard_display(text, is_empty, err_msg)

    def _update_clipboard_display(self, text: str, is_empty: bool, err_msg: str = ""):
        if getattr(self, "_is_closing", False) or not self.winfo_exists():
            return
        stats = analyze_clipboard_content(text)

        self.clip_textbox.configure(state="normal")
        self.clip_textbox.delete("1.0", "end")

        if is_empty:
            self.clip_textbox.insert("1.0", "Windows clipboard buffer is empty.\n\nCopy source code from your IDE, or click 'Load Sample Code' above.")
            self.lbl_clip_meta.configure(text="Clipboard empty", text_color=AMBER_GOLD)
        else:
            self.clip_textbox.insert("1.0", stats["preview"])
            code_tag = " • Code detected" if stats.get("has_code", False) else ""
            lines = stats.get("line_count", stats.get("lines", 0))
            words = stats.get("word_count", stats.get("words", 0))
            self.lbl_clip_meta.configure(
                text=f"{stats.get('char_count', 0)} characters • {lines} lines • {words} tokens{code_tag}",
                text_color=APPLE_BLUE
            )

        self.clip_textbox.configure(state="disabled")

    # ==========================================
    # Engine Telemetry & State Handlers
    # ==========================================
    def _queue_state_change(self, state: str, details: dict):
        self._ui_queue.put(("state_change", {"state": state, "details": details}))

    def _queue_progress(self, pct, typed, total, elapsed, remaining, char):
        self._ui_queue.put(("progress", {
            "pct": pct,
            "typed": typed,
            "total": total,
            "elapsed": elapsed,
            "remaining": remaining,
            "char": char
        }))

    def _queue_countdown(self, seconds_left):
        self._ui_queue.put(("countdown", {"seconds": seconds_left}))

    def _queue_error(self, message):
        self._ui_queue.put(("error", {"message": message}))

    def _process_ui_queue(self):
        if getattr(self, "_is_closing", False) or not self.winfo_exists():
            return
        try:
            while True:
                event_type, data = self._ui_queue.get_nowait()
                if event_type == "hotkey_pressed":
                    self.engine.trigger_from_clipboard()
                elif event_type == "state_change":
                    self._handle_state_change(data["state"], data["details"])
                elif event_type == "progress":
                    self._handle_progress(data)
                elif event_type == "countdown":
                    self._handle_countdown(data["seconds"])
                elif event_type == "error":
                    self._handle_error(data["message"])
        except queue.Empty:
            pass

        if not getattr(self, "_is_closing", False) and self.winfo_exists():
            self._schedule(30, self._process_ui_queue)

    def _handle_state_change(self, state: str, details: dict):
        if state == EngineState.IDLE:
            self._target_progress = 0.0
            self.status_pill.configure(text="● Ready", fg_color="#241B13", text_color=TEXT_PRIMARY)
            self.status_desc_lbl.configure(text=f"Focus your target editor and press {self.current_hotkey_label}", text_color=TEXT_SECONDARY)
            self.btn_start.configure(state="normal", text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]", fg_color=AMBER_GOLD)
            self.btn_pause.configure(state="disabled", text="⏸ Pause", fg_color="#241B13", text_color=TEXT_MUTED)
            self.progress_bar.configure(progress_color=AMBER_GOLD)
            self.lbl_target_window.configure(text="Target: Standby")
            self.lbl_target_dot.configure(text_color=APPLE_GREEN)

        elif state == EngineState.COUNTDOWN:
            delay = details.get("delay", self.engine.safety_delay)
            self.status_pill.configure(text=f"⏳ {delay:.1f}s", fg_color=AMBER_PILL_BG, text_color=AMBER_GOLD_BRIGHT)
            self.status_desc_lbl.configure(text=f"Armed — Switch to target editor! Starting in {delay:.1f}s...", text_color=AMBER_GOLD_BRIGHT)
            self.btn_start.configure(state="disabled", text="Counting Down...", fg_color="#6B3E12")
            self.btn_pause.configure(state="disabled")
            self._target_progress = 0.0
            self.progress_bar.configure(progress_color=AMBER_GOLD_BRIGHT)

        elif state == EngineState.TYPING:
            target = details.get("target", {})
            title = target.get("title", "Active Editor")[:22]
            proc = target.get("process_name", "App")
            self.status_pill.configure(text="⚡ Typing", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)
            self.status_desc_lbl.configure(text=f"Typing into: {title} ({proc})", text_color=APPLE_GREEN)
            self.lbl_target_window.configure(text=f"Target: {proc.upper()}")
            self.lbl_target_dot.configure(text_color=AMBER_GOLD)
            self.btn_start.configure(state="disabled", text="⚡ Typing Active", fg_color="#17502B")
            self.btn_pause.configure(state="normal", text="⏸ Pause", fg_color="#241B13", text_color=TEXT_PRIMARY)
            self.progress_bar.configure(progress_color=APPLE_GREEN)

        elif state == EngineState.PAUSED:
            reason = details.get("reason", "Paused")[:30]
            self.status_pill.configure(text="⏸ Paused", fg_color=AMBER_PILL_BG, text_color=AMBER_GOLD)
            self.status_desc_lbl.configure(text=f"Paused: {reason}", text_color=AMBER_GOLD)
            self.btn_pause.configure(state="normal", text="▶ Resume", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)
            self.progress_bar.configure(progress_color=AMBER_GOLD)

        elif state == EngineState.STOPPED:
            self.status_pill.configure(text="🛑 Stopped", fg_color=APPLE_CORAL_GLOW, text_color=APPLE_CORAL)
            self.status_desc_lbl.configure(text="Emergency stop triggered (Esc pressed)", text_color=APPLE_CORAL)
            self.btn_start.configure(state="normal", text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]", fg_color=AMBER_GOLD)
            self.btn_pause.configure(state="disabled", text="⏸ Pause", fg_color="#241B13", text_color=TEXT_MUTED)
            self.progress_bar.configure(progress_color=APPLE_CORAL)

        elif state == EngineState.COMPLETED:
            typed = details.get("total_typed", self.engine.chars_typed)
            sec = details.get("elapsed_sec", 0.0)
            self.status_pill.configure(text="✔ Done", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)
            self.status_desc_lbl.configure(text=f"Completed {typed} actions in {sec:.1f}s!", text_color=APPLE_GREEN)
            self.btn_start.configure(state="normal", text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]", fg_color=AMBER_GOLD)
            self.btn_pause.configure(state="disabled", text="⏸ Pause", fg_color="#241B13", text_color=TEXT_MUTED)
            self._target_progress = 1.0
            self.progress_bar.configure(progress_color=APPLE_GREEN)

        # Forward to Ghost HUD if active
        if getattr(self, "ghost_hud", None) and self.ghost_hud.winfo_exists():
            try:
                self.ghost_hud.update_state(state, details)
            except Exception:
                pass

    def _handle_countdown(self, seconds_left: float):
        if seconds_left > 0:
            self.status_pill.configure(text=f"⏳ {seconds_left:.1f}s", fg_color=AMBER_PILL_BG, text_color=AMBER_GOLD_BRIGHT)
            self.status_desc_lbl.configure(text=f"Armed — Switch to target editor! Starting in {seconds_left:.1f}s...")
        else:
            self.status_pill.configure(text="⚡ Typing", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)
            self.status_desc_lbl.configure(text="Typing active...")

        if getattr(self, "ghost_hud", None) and self.ghost_hud.winfo_exists():
            try:
                self.ghost_hud.update_countdown(seconds_left)
            except Exception:
                pass

    def _handle_progress(self, data: dict):
        pct = data["pct"]
        typed = data["typed"]
        total = data["total"]
        elapsed = data["elapsed"]
        remaining = data["remaining"]
        char = data.get("char", "")

        # Set lerp animation target
        self._target_progress = min(1.0, max(0.0, pct / 100.0))
        self.lbl_tele_progress.configure(text=f"{typed} / {total} ({pct:.0f}%)")

        mins_el = int(elapsed) // 60
        secs_el = int(elapsed) % 60
        mins_rem = int(remaining) // 60
        secs_rem = int(remaining) % 60
        self.lbl_tele_time.configure(text=f"{mins_el:02d}:{secs_el:02d} / {mins_rem:02d}:{secs_rem:02d}")

        if char:
            clean_ch = char if char not in ("\n", "\t", "\r") else ("↵" if char == "\n" else "⇥")
            self.lbl_tele_token.configure(text=f"[ {clean_ch} ]")

        if getattr(self, "ghost_hud", None) and self.ghost_hud.winfo_exists():
            try:
                self.ghost_hud.update_progress(pct, typed, total, elapsed, remaining, char)
            except Exception:
                pass

    def _handle_error(self, message: str):
        self.status_pill.configure(text="⚠️ Notice", fg_color=APPLE_CORAL_GLOW, text_color=APPLE_CORAL)
        self.status_desc_lbl.configure(text=message, text_color=APPLE_CORAL)

    def _on_close(self):
        """Graceful shutdown with zero timer leaks and memory release."""
        self._is_closing = True

        for after_id in list(self._after_ids):
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self._after_ids.clear()

        self.engine.stop()
        if self.hotkey_mgr:
            self.hotkey_mgr.stop()

        if getattr(self, "ghost_hud", None) and self.ghost_hud.winfo_exists():
            try:
                self.ghost_hud.destroy()
            except Exception:
                pass
            self.ghost_hud = None

        try:
            self.destroy()
        except Exception:
            pass

        try:
            import gc
            gc.collect()
        except Exception:
            pass
