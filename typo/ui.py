"""
TYPO® — Studio Glass Edition (Apple visionOS & macOS Liquid Glass)
High-fidelity, responsive CustomTkinter UI for precision keystroke automation.

Engineered with:
- Native Windows 10 & 11 Acrylic Frosted Blur via SetWindowCompositionAttribute & DWM
- Translucent obsidian glass palette with specular rim refraction borders
- Fluid 60 FPS progress bar linear interpolation (lerp) animation
- Clean, proportional Apple typography hierarchy (Segoe UI & Consolas)
- Zero-leak timer lifecycle tracking and O(1) clipboard memory fingerprinting
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

from typo.typing_engine import TypingEngine, EngineState
from typo.win32_api import GlobalHotKeyManager, PRIMARY_HOTKEY_LABEL
from typo.clipboard import get_current_clipboard, analyze_clipboard_content, set_test_clipboard_text

# ==========================================
# Apple Liquid Glass Tokens & Color Space
# ==========================================
# Translucent Obsidian Glass Bases
GLASS_BG = "#070A12"               # Deep obsidian liquid canvas
GLASS_SIDEBAR = "#0C101A"          # Frosted glass sidebar bay
GLASS_SIDEBAR_BORDER = "#1F2638"   # Sidebar glass divider

# Frosted Glass Cards (Squircle Slices)
GLASS_CARD = "#121725"             # Frosted visionOS squircle card
GLASS_CARD_HOVER = "#181E30"       # Elevated glass refraction on hover
GLASS_CARD_BORDER = "#252F45"      # Specular glass bevel border (1px hairline)
GLASS_CARD_BORDER_GLOW = "#3A4768" # Specular rim highlight

# Inset Glass Wells (Code Buffer & Telemetry)
GLASS_INSET = "#080B12"            # Recessed dark glass well
GLASS_INSET_BORDER = "#1A2132"     # Inset boundary

# Floating Glass Pill Bar & Capsules
GLASS_PILL_BAR = "#131826"         # Floating capsule bar
GLASS_PILL_BAR_BORDER = "#242D42"  # Capsule bar rim
GLASS_PILL = "#161C2C"             # Standby capsule item
GLASS_PILL_BORDER = "#28334A"
GLASS_PILL_ACTIVE = "#0F2619"      # Active Apple Electric Green pill
GLASS_PILL_ACTIVE_BORDER = "#205C36"

# Apple visionOS Luminous Accents
APPLE_GREEN = "#30D158"            # Apple visionOS electric neon green
APPLE_GREEN_HOVER = "#38E564"
APPLE_GREEN_GLOW = "#0E2916"       # Luminous green glow well
APPLE_BLUE = "#0A84FF"             # Apple system electric blue
APPLE_BLUE_GLOW = "#0D2240"
APPLE_AMBER = "#FF9F0A"            # Apple system warning amber
APPLE_AMBER_GLOW = "#33200B"
APPLE_CORAL = "#FF453A"            # Apple system coral / abort
APPLE_CORAL_GLOW = "#331518"
APPLE_PURPLE = "#BF5AF2"           # Apple system electric purple
APPLE_PURPLE_GLOW = "#281335"
APPLE_TRACK = "#181E2E"            # Recessed capsule slider track

# Apple Modern High-Legibility Typography Colors
TEXT_PRIMARY = "#FFFFFF"           # Crisp pure white
TEXT_SECONDARY = "#A1A8BA"         # Apple secondary system text
TEXT_MUTED = "#636C82"             # Muted annotations & technical indicators
TEXT_DIM = "#323B50"               # Subtle glass grooves

# Typography Stack (Native High-Resolution Typography)
FONT_FAMILY = "Segoe UI"
FONT_MONO_FAMILY = "Consolas"


# ==========================================
# Native Windows 10 & 11 Acrylic Blur Engine
# ==========================================
class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),      # 4 = ACCENT_ENABLE_ACRYLICBLURBEHIND, 3 = ACCENT_ENABLE_BLURBEHIND
        ("AccentFlags", ctypes.c_int),      # 2
        ("GradientColor", ctypes.c_int),    # ARGB (e.g. 0xCC090C14: CC alpha, 090C14 dark tint)
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
            # AccentState = 4 (ACCENT_ENABLE_ACRYLICBLURBEHIND) with dark obsidian tint
            # 0xCC080B14 -> alpha ~80%, RGB #080B14
            policy = ACCENT_POLICY(4, 2, 0xCC080B14, 0)
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
        self.title("TYPO® — Studio Glass Edition")
        self.geometry("1100x820")
        self.minsize(980, 700)
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

        # Smooth Animation Engine State (60 FPS Progress Lerp)
        self._target_progress = 0.0
        self._current_progress = 0.0

        # Bind Engine Callbacks
        self.engine.on_state_change = self._queue_state_change
        self.engine.on_progress = self._queue_progress
        self.engine.on_countdown = self._queue_countdown
        self.engine.on_error = self._queue_error

        # Build Studio Glass Layout (Sidebar + Fluid Workspace)
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
            self.progress_bar.set(self._current_progress)

        self._schedule(16, self._animate_tick)

    # ==========================================
    # Main Shell Architecture (Sidebar + Canvas)
    # ==========================================
    def _build_main_shell(self):
        self.root_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.root_container.pack(fill="both", expand=True)

        # ------------------------------------------
        # 1. Frosted Glass Sidebar (Island Navigation)
        # ------------------------------------------
        self.sidebar = ctk.CTkFrame(
            self.root_container,
            width=255,
            fg_color=GLASS_SIDEBAR,
            border_color=GLASS_SIDEBAR_BORDER,
            border_width=1,
            corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Sidebar Header: Apple Vision Brand & Studio Identity
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=18, pady=(20, 14))

        # Profile Pill Box
        profile_row = ctk.CTkFrame(
            brand_frame,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=18,
            height=48
        )
        profile_row.pack(fill="x", pady=(0, 12))
        profile_row.pack_propagate(False)

        # Logo Avatar Circle
        avatar_box = ctk.CTkFrame(
            profile_row,
            width=34,
            height=34,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER_GLOW,
            border_width=1,
            corner_radius=17
        )
        avatar_box.pack(side="left", padx=(8, 10))
        avatar_box.pack_propagate(False)

        ctk.CTkLabel(
            avatar_box,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY
        ).place(relx=0.5, rely=0.5, anchor="center")

        user_text_frame = ctk.CTkFrame(profile_row, fg_color="transparent")
        user_text_frame.pack(side="left", fill="y", pady=5)

        ctk.CTkLabel(
            user_text_frame,
            text="TYPO STUDIO",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=APPLE_GREEN
        ).pack(anchor="w")

        ctk.CTkLabel(
            user_text_frame,
            text="Vision Liquid Glass",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        # Live Status Beacon Dot
        ctk.CTkLabel(
            profile_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=APPLE_GREEN
        ).pack(side="right", padx=(0, 14))

        # Large Section Headline
        title_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_box.pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(
            title_box,
            text="Control Deck",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="PRECISION INPUT ENGINE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w", pady=(2, 0))

        # Specular Hairline Glass Divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color=GLASS_CARD_BORDER).pack(fill="x", padx=16, pady=(10, 14))

        # Live Velocity Glass Card
        cadence_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=18
        )
        cadence_card.pack(fill="x", padx=16, pady=(0, 16))

        cad_inner = ctk.CTkFrame(cadence_card, fg_color="transparent")
        cad_inner.pack(fill="x", padx=14, pady=12)

        cad_hdr = ctk.CTkFrame(cad_inner, fg_color="transparent")
        cad_hdr.pack(fill="x")

        ctk.CTkLabel(
            cad_hdr,
            text="Active Velocity",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left")

        # Luminous Green Status Pill
        glow_pill = ctk.CTkLabel(
            cad_hdr,
            text="● LIVE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=APPLE_GREEN,
            fg_color=APPLE_GREEN_GLOW,
            border_color=GLASS_PILL_ACTIVE_BORDER,
            border_width=1,
            corner_radius=8,
            padx=7,
            pady=2
        )
        glow_pill.pack(side="right")

        self.lbl_sidebar_wpm = ctk.CTkLabel(
            cad_inner,
            text="80 WPM",
            font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.lbl_sidebar_wpm.pack(anchor="w", pady=(6, 2))

        # Velocity Scale Annotation
        scale_row = ctk.CTkFrame(cad_inner, fg_color="transparent")
        scale_row.pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(scale_row, text="40", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(scale_row, text="60", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="left", expand=True)
        ctk.CTkLabel(scale_row, text="80", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=APPLE_GREEN).pack(side="left", expand=True)
        ctk.CTkLabel(scale_row, text="120", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="left", expand=True)
        ctk.CTkLabel(scale_row, text="180", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="right")

        # Sidebar Navigation Pill Menu
        nav_menu = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_menu.pack(fill="x", padx=14)

        nav_items = [
            ("Sequencer Deck", True, "🎛"),
            ("Biometrics Lab", False, "⚡"),
            ("Code Memory", False, "📋"),
            ("Session Telemetry", False, "📊"),
        ]

        for text, is_active, icon in nav_items:
            bg_col = GLASS_CARD if is_active else "transparent"
            text_col = TEXT_PRIMARY if is_active else TEXT_SECONDARY
            border_col = GLASS_CARD_BORDER_GLOW if is_active else GLASS_SIDEBAR
            border_w = 1 if is_active else 0

            row_frame = ctk.CTkFrame(
                nav_menu,
                fg_color=bg_col,
                border_color=border_col,
                border_width=border_w,
                corner_radius=14,
                height=40
            )
            row_frame.pack(fill="x", pady=3)
            row_frame.pack_propagate(False)

            icon_col = APPLE_GREEN if is_active else TEXT_MUTED
            ctk.CTkLabel(
                row_frame,
                text=icon,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=icon_col
            ).pack(side="left", padx=(12, 6))

            btn = ctk.CTkLabel(
                row_frame,
                text=text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold" if is_active else "normal"),
                text_color=text_col,
                anchor="w",
                cursor="hand2"
            )
            btn.pack(side="left", fill="both", expand=True)

            if is_active:
                ctk.CTkLabel(
                    row_frame,
                    text="●",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                    text_color=APPLE_GREEN
                ).pack(side="right", padx=(0, 12))

        # Bottom Hardware Trigger Card
        bottom_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=18
        )
        bottom_card.pack(side="bottom", fill="x", padx=14, pady=16)

        ctk.CTkLabel(
            bottom_card,
            text="HARDWARE HOTKEY",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=14, pady=(12, 4))

        lbl_hk = ctk.CTkLabel(
            bottom_card,
            text=f"[ {self.current_hotkey_label} ]",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=10,
            padx=10,
            pady=4
        )
        lbl_hk.pack(anchor="w", padx=14, pady=(0, 6))

        ctk.CTkLabel(
            bottom_card,
            text="Emergency Abort: [ Esc ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=APPLE_CORAL
        ).pack(anchor="w", padx=14, pady=(0, 12))

        # ------------------------------------------
        # 2. Fluid Canvas Workspace (Apple Vision Glass Deck)
        # ------------------------------------------
        self.workspace = ctk.CTkFrame(self.root_container, fg_color="transparent", corner_radius=0)
        self.workspace.pack(side="right", fill="both", expand=True)

        # Top Navigation Bar
        self._build_top_bar()

        # Floating Liquid Glass Capsule Bar
        self._build_floating_capsule_bar()

        # Responsive Scrollable Content Deck
        self.body_scroll = ctk.CTkScrollableFrame(
            self.workspace,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#1F2638",
            scrollbar_button_hover_color="#2D3852"
        )
        self.body_scroll.pack(fill="both", expand=True, padx=22, pady=(0, 16))

        # Build Studio Glass Cards
        self._build_hero_status_card()
        self._build_precision_sliders_card()
        self._build_clipboard_card()
        self._build_feature_matrix_card()

    # ==========================================
    # Top Application Bar
    # ==========================================
    def _build_top_bar(self):
        bar = ctk.CTkFrame(self.workspace, fg_color="transparent", height=58)
        bar.pack(fill="x", padx=22, pady=(14, 8))
        bar.pack_propagate(False)

        left_meta = ctk.CTkFrame(bar, fg_color="transparent")
        left_meta.pack(side="left")

        ctk.CTkLabel(
            left_meta,
            text="VISION OS // AUTOMATION STUDIO",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w")

        self.lbl_view_title = ctk.CTkLabel(
            left_meta,
            text="Control Deck · Dynamic Glass Sequencer",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.lbl_view_title.pack(anchor="w")

        right_tools = ctk.CTkFrame(bar, fg_color="transparent")
        right_tools.pack(side="right")

        self.btn_ghost_hud = ctk.CTkButton(
            right_tools,
            text="👻 Ghost HUD",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
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

        self.btn_sound = ctk.CTkButton(
            right_tools,
            text="🔊 Audio On",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
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

        self.lbl_target_window = ctk.CTkLabel(
            right_tools,
            text="Target: Standby",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=18,
            padx=14,
            pady=6
        )
        self.lbl_target_window.pack(side="right")

    # ==========================================
    # Floating Liquid Glass Capsule Bar
    # ==========================================
    def _build_floating_capsule_bar(self):
        capsule_bar = ctk.CTkFrame(
            self.workspace,
            height=46,
            fg_color=GLASS_PILL_BAR,
            border_color=GLASS_PILL_BAR_BORDER,
            border_width=1,
            corner_radius=23
        )
        capsule_bar.pack(fill="x", padx=22, pady=(0, 14))
        capsule_bar.pack_propagate(False)

        caps_inner = ctk.CTkFrame(capsule_bar, fg_color="transparent")
        caps_inner.pack(fill="both", expand=True, padx=6, pady=4)

        add_pill = ctk.CTkLabel(
            caps_inner,
            text="+",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=19,
            width=38,
            height=38,
            cursor="hand2"
        )
        add_pill.pack(side="left", padx=(2, 8))

        active_pill = ctk.CTkFrame(
            caps_inner,
            fg_color=GLASS_PILL_ACTIVE,
            border_color=GLASS_PILL_ACTIVE_BORDER,
            border_width=1,
            corner_radius=19,
            height=38
        )
        active_pill.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            active_pill,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=APPLE_GREEN
        ).pack(side="left", padx=(12, 4))

        ctk.CTkLabel(
            active_pill,
            text="Primary Studio",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left", padx=(0, 14))

        pills = ["Biometrics", "Code Buffer", "Telemetry Log", "Anti-Gaze"]
        for p in pills:
            pill_lbl = ctk.CTkLabel(
                caps_inner,
                text=p,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_SECONDARY,
                fg_color="transparent",
                corner_radius=19,
                padx=12,
                cursor="hand2"
            )
            pill_lbl.pack(side="left", padx=2)

        lens_badge = ctk.CTkLabel(
            caps_inner,
            text="💧 Liquid Glass",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color="#182030",
            border_color=GLASS_CARD_BORDER_GLOW,
            border_width=1,
            corner_radius=15,
            padx=12,
            pady=4
        )
        lens_badge.pack(side="right", padx=(0, 4))

    # ==========================================
    # 1. Hero Telemetry & Action Deck Card
    # ==========================================
    def _build_hero_status_card(self):
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=22
        )
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=20)

        # Header Row
        hdr_row = ctk.CTkFrame(inner, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            hdr_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=APPLE_GREEN
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hdr_row,
            text="Telemetry & Dispatch Engine",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            hdr_row,
            text="visionOS Liquid Glass",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(side="right")

        # Status & Action Buttons Row
        ctrl_row = ctk.CTkFrame(inner, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=(0, 14))

        pill_frame = ctk.CTkFrame(ctrl_row, fg_color="transparent")
        pill_frame.pack(side="left")

        self.status_pill = ctk.CTkLabel(
            pill_frame,
            text="● Ready",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color="#181D2C",
            border_color=GLASS_CARD_BORDER_GLOW,
            border_width=1,
            corner_radius=14,
            padx=14,
            pady=5
        )
        self.status_pill.pack(side="left")

        self.status_desc_lbl = ctk.CTkLabel(
            pill_frame,
            text=f"Focus your target editor and press {self.current_hotkey_label}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY
        )
        self.status_desc_lbl.pack(side="left", padx=12)

        btn_frame = ctk.CTkFrame(ctrl_row, fg_color="transparent")
        btn_frame.pack(side="right")

        self.btn_start = ctk.CTkButton(
            btn_frame,
            text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            height=38,
            corner_radius=19,
            fg_color=APPLE_GREEN,
            hover_color=APPLE_GREEN_HOVER,
            text_color="#000000",
            command=self._trigger_start
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_pause = ctk.CTkButton(
            btn_frame,
            text="⏸ Pause",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            height=38,
            width=84,
            corner_radius=19,
            fg_color="#181D2C",
            hover_color="#242B40",
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            text_color=TEXT_MUTED,
            state="disabled",
            command=self._trigger_pause_resume
        )
        self.btn_pause.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            btn_frame,
            text="■ Esc / Abort",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            height=38,
            width=104,
            corner_radius=19,
            fg_color=APPLE_CORAL_GLOW,
            hover_color="#45181C",
            border_color=APPLE_CORAL,
            border_width=1,
            text_color=APPLE_CORAL,
            command=self._trigger_emergency_stop
        )
        self.btn_stop.pack(side="left")

        # 60 FPS Smooth Interpolated Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            inner,
            height=6,
            corner_radius=3,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_GREEN
        )
        self.progress_bar.pack(fill="x", pady=(2, 16))
        self.progress_bar.set(0.0)

        # 4-Column Metric Grid
        tele_grid = ctk.CTkFrame(inner, fg_color="transparent")
        tele_grid.pack(fill="x")
        tele_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        c1 = ctk.CTkFrame(tele_grid, fg_color=GLASS_INSET, corner_radius=14, border_color=GLASS_INSET_BORDER, border_width=1)
        c1.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=2)
        ctk.CTkLabel(c1, text="PROGRESS", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_tele_progress = ctk.CTkLabel(c1, text="0 / 0 (0%)", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_tele_progress.pack(anchor="w", padx=14, pady=(0, 10))

        c2 = ctk.CTkFrame(tele_grid, fg_color=GLASS_INSET, corner_radius=14, border_color=GLASS_INSET_BORDER, border_width=1)
        c2.grid(row=0, column=1, sticky="ew", padx=3, pady=2)
        ctk.CTkLabel(c2, text="VELOCITY", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_tele_speed = ctk.CTkLabel(c2, text="80.0 WPM", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=APPLE_GREEN)
        self.lbl_tele_speed.pack(anchor="w", padx=14, pady=(0, 10))

        c3 = ctk.CTkFrame(tele_grid, fg_color=GLASS_INSET, corner_radius=14, border_color=GLASS_INSET_BORDER, border_width=1)
        c3.grid(row=0, column=2, sticky="ew", padx=3, pady=2)
        ctk.CTkLabel(c3, text="ELAPSED / REMAIN", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_tele_time = ctk.CTkLabel(c3, text="00:00 / 00:00", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_tele_time.pack(anchor="w", padx=14, pady=(0, 10))

        c4 = ctk.CTkFrame(tele_grid, fg_color=GLASS_INSET, corner_radius=14, border_color=GLASS_INSET_BORDER, border_width=1)
        c4.grid(row=0, column=3, sticky="ew", padx=(5, 0), pady=2)
        ctk.CTkLabel(c4, text="LAST TOKEN // DWELL", font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_tele_token = ctk.CTkLabel(c4, text="[ ↵ ] ~55ms", font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=13, weight="bold"), text_color=APPLE_BLUE)
        self.lbl_tele_token.pack(anchor="w", padx=14, pady=(0, 10))

    # ==========================================
    # 2. Precision Faders Card
    # ==========================================
    def _build_precision_sliders_card(self):
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=22
        )
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=20)

        hdr_row = ctk.CTkFrame(inner, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            hdr_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=APPLE_BLUE
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hdr_row,
            text="Tactile Cadence & Velocity Faders",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        faders_grid = ctk.CTkFrame(inner, fg_color="transparent")
        faders_grid.pack(fill="x")
        faders_grid.grid_columnconfigure((0, 1), weight=1)

        # Fader 1: Velocity WPM
        f1_card = ctk.CTkFrame(faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=16)
        f1_card.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)

        f1_h = ctk.CTkFrame(f1_card, fg_color="transparent")
        f1_h.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(f1_h, text="Typing Velocity", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        self.lbl_wpm_val = ctk.CTkLabel(
            f1_h,
            text="80 WPM",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=12, weight="bold"),
            text_color=APPLE_GREEN,
            fg_color=APPLE_GREEN_GLOW,
            border_color=GLASS_PILL_ACTIVE_BORDER,
            border_width=1,
            corner_radius=8,
            padx=8,
            pady=2
        )
        self.lbl_wpm_val.pack(side="right")

        self.slider_wpm = ctk.CTkSlider(
            f1_card,
            from_=30,
            to=180,
            number_of_steps=150,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_GREEN,
            button_color=APPLE_GREEN,
            button_hover_color=APPLE_GREEN_HOVER,
            command=self._on_wpm_change
        )
        self.slider_wpm.set(80)
        self.slider_wpm.pack(fill="x", padx=16, pady=(4, 6))

        f1_sub = ctk.CTkFrame(f1_card, fg_color="transparent")
        f1_sub.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(f1_sub, text="30 WPM (Relaxed)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f1_sub, text="180 WPM (Extreme)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="right")

        # Fader 2: Jitter Variance
        f2_card = ctk.CTkFrame(faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=16)
        f2_card.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=4)

        f2_h = ctk.CTkFrame(f2_card, fg_color="transparent")
        f2_h.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(f2_h, text="Human Cadence Jitter", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        self.lbl_jitter_val = ctk.CTkLabel(
            f2_h,
            text="25%",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=12, weight="bold"),
            text_color=APPLE_BLUE,
            fg_color=APPLE_BLUE_GLOW,
            border_color="#1E3C66",
            border_width=1,
            corner_radius=8,
            padx=8,
            pady=2
        )
        self.lbl_jitter_val.pack(side="right")

        self.slider_jitter = ctk.CTkSlider(
            f2_card,
            from_=0.0,
            to=0.60,
            number_of_steps=60,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_BLUE,
            button_color=APPLE_BLUE,
            button_hover_color="#3399FF",
            command=self._on_jitter_change
        )
        self.slider_jitter.set(0.25)
        self.slider_jitter.pack(fill="x", padx=16, pady=(4, 6))

        f2_sub = ctk.CTkFrame(f2_card, fg_color="transparent")
        f2_sub.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(f2_sub, text="0% (Strict)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f2_sub, text="60% (Organic)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="right")

        # Fader 3: Typo & Mistake Injection
        f3_card = ctk.CTkFrame(faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=16)
        f3_card.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=4)

        f3_h = ctk.CTkFrame(f3_card, fg_color="transparent")
        f3_h.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(f3_h, text="Typo & Mistake Rate", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        self.lbl_mistake_val = ctk.CTkLabel(
            f3_h,
            text="1.5%",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=12, weight="bold"),
            text_color=APPLE_AMBER,
            fg_color=APPLE_AMBER_GLOW,
            border_color="#593A14",
            border_width=1,
            corner_radius=8,
            padx=8,
            pady=2
        )
        self.lbl_mistake_val.pack(side="right")

        self.slider_mistake = ctk.CTkSlider(
            f3_card,
            from_=0.0,
            to=0.05,
            number_of_steps=50,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_AMBER,
            button_color=APPLE_AMBER,
            button_hover_color="#FFB338",
            command=self._on_mistake_rate_change
        )
        self.slider_mistake.set(0.015)
        self.slider_mistake.pack(fill="x", padx=16, pady=(4, 6))

        f3_sub = ctk.CTkFrame(f3_card, fg_color="transparent")
        f3_sub.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(f3_sub, text="0.0% (Flawless)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f3_sub, text="5.0% (Natural Typos)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="right")

        # Fader 4: Safety Focus Countdown
        f4_card = ctk.CTkFrame(faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=16)
        f4_card.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=4)

        f4_h = ctk.CTkFrame(f4_card, fg_color="transparent")
        f4_h.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(f4_h, text="Safety Focus Countdown", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        self.lbl_delay_val = ctk.CTkLabel(
            f4_h,
            text="3.0s",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=12, weight="bold"),
            text_color=APPLE_PURPLE,
            fg_color=APPLE_PURPLE_GLOW,
            border_color="#4F2668",
            border_width=1,
            corner_radius=8,
            padx=8,
            pady=2
        )
        self.lbl_delay_val.pack(side="right")

        self.slider_delay = ctk.CTkSlider(
            f4_card,
            from_=1.0,
            to=8.0,
            number_of_steps=70,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_PURPLE,
            button_color=APPLE_PURPLE,
            button_hover_color="#CC70FF",
            command=self._on_delay_change
        )
        self.slider_delay.set(3.0)
        self.slider_delay.pack(fill="x", padx=16, pady=(4, 6))

        f4_sub = ctk.CTkFrame(f4_card, fg_color="transparent")
        f4_sub.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(f4_sub, text="1.0s (Fast Switch)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f4_sub, text="8.0s (Relaxed)", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_MUTED).pack(side="right")

    # ==========================================
    # 3. Live Code Buffer & Telemetry
    # ==========================================
    def _build_clipboard_card(self):
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=22
        )
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=20)

        hdr_row = ctk.CTkFrame(inner, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            hdr_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=APPLE_GREEN
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hdr_row,
            text="Live Code Buffer & Non-Destructive Inspection",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        btn_box = ctk.CTkFrame(hdr_row, fg_color="transparent")
        btn_box.pack(side="right")

        btn_sample = ctk.CTkButton(
            btn_box,
            text="Load Sample Code",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=30,
            corner_radius=15,
            fg_color=GLASS_INSET,
            hover_color=GLASS_CARD_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._load_sample_code
        )
        btn_sample.pack(side="right", padx=(6, 0))

        btn_refresh = ctk.CTkButton(
            btn_box,
            text="⟳ Refresh",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=30,
            width=70,
            corner_radius=15,
            fg_color=GLASS_INSET,
            hover_color=GLASS_CARD_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._refresh_clipboard_view
        )
        btn_refresh.pack(side="right")

        # Monospace Inset Code Box
        self.clip_textbox = ctk.CTkTextbox(
            inner,
            height=140,
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=12),
            fg_color=GLASS_INSET,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_INSET_BORDER,
            border_width=1,
            corner_radius=14,
            wrap="none"
        )
        self.clip_textbox.pack(fill="x", pady=(2, 10))

        self.lbl_clip_meta = ctk.CTkLabel(
            inner,
            text="0 characters · 0 lines · 0 tokens",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY
        )
        self.lbl_clip_meta.pack(anchor="w")

    # ==========================================
    # 4. Anti-Detection Stealth Feature Matrix
    # ==========================================
    def _build_feature_matrix_card(self):
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=22
        )
        card.pack(fill="x", pady=(0, 20))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=20)

        hdr_row = ctk.CTkFrame(inner, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            hdr_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=APPLE_GREEN
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hdr_row,
            text="Anti-Detection & Algorithmic Stealth Matrix",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        features_grid = ctk.CTkFrame(inner, fg_color="transparent")
        features_grid.pack(fill="x")
        features_grid.grid_columnconfigure((0, 1), weight=1)

        matrix = [
            ("Simulated Cursor Wandering", "Subtle mouse drift with cubic easing defeats webcam gaze & mouse anomaly sensors", self._on_toggle_cursor_wandering, True, 0, 0),
            ("Complexity Cadence Throttler", "Throttles to 35-50 WPM on nested DP & bitwise logic; fast on boilerplate", self._on_toggle_complexity_throttler, True, 0, 1),
            ("Incremental Code Construction", "Outlines signature stub first, then navigates back inside function body", self._on_toggle_incremental, False, 1, 0),
            ("Selection & Refactoring Simulation", "Simulates Shift+Left selection & backspace replacement of variable tokens", self._on_toggle_refactoring, True, 1, 1),
            ("Target Focus Guard", "Auto-pauses typing if target window loses focus (prevents cross-window leaks)", self._on_toggle_focus, True, 2, 0),
            ("Smart Auto-Indent & Dedent Sync", "Zero spacebars for code indent; syncs with editor auto-indentation", self._on_toggle_bracket_neutralizer, True, 2, 1),
            ("Biometric Keystroke Dynamics", "Non-uniform Gaussian dwell times (~55ms) bypass 0ms virtual key hold detection", self._on_toggle_biometrics, True, 3, 0),
            ("Autonomous Mistake Injection", "Types adjacent QWERTY keys with human visual hesitation & backspace recovery", self._on_toggle_mistakes, True, 3, 1),
        ]

        self.switches = {}
        for title, desc, callback, default_val, row, col in matrix:
            pad_x = (0, 6) if col == 0 else (6, 0)
            cell = ctk.CTkFrame(features_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=14)
            cell.grid(row=row, column=col, sticky="ew", padx=pad_x, pady=4)

            top_line = ctk.CTkFrame(cell, fg_color="transparent")
            top_line.pack(fill="x", padx=14, pady=(12, 2))

            ctk.CTkLabel(
                top_line,
                text=title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                text_color=TEXT_PRIMARY
            ).pack(side="left")

            sw = ctk.CTkSwitch(
                top_line,
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

            ctk.CTkLabel(
                cell,
                text=desc,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_SECONDARY,
                wraplength=340,
                justify="left"
            ).pack(anchor="w", padx=14, pady=(0, 12))

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
        self.lbl_wpm_val.configure(text=f"{wpm} WPM")
        self.lbl_sidebar_wpm.configure(text=f"{wpm} WPM")
        self.lbl_tele_speed.configure(text=f"{wpm:.1f} WPM")

    def _on_jitter_change(self, val):
        jitter = float(val)
        self.engine.variance = jitter
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
            self.lbl_clip_meta.configure(text="Clipboard empty", text_color=APPLE_AMBER)
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
            self.status_pill.configure(text="● Ready", fg_color="#181D2C", text_color=TEXT_PRIMARY)
            self.status_desc_lbl.configure(text=f"Focus your target editor and press {self.current_hotkey_label}", text_color=TEXT_SECONDARY)
            self.btn_start.configure(state="normal", text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]", fg_color=APPLE_GREEN)
            self.btn_pause.configure(state="disabled", text="⏸ Pause", fg_color="#181D2C", text_color=TEXT_MUTED)
            self.progress_bar.configure(progress_color=APPLE_GREEN)
            self.lbl_target_window.configure(text="Target: Standby")

        elif state == EngineState.COUNTDOWN:
            delay = details.get("delay", self.engine.safety_delay)
            self.status_pill.configure(text=f"⏳ {delay:.1f}s", fg_color=APPLE_AMBER_GLOW, text_color=APPLE_AMBER)
            self.status_desc_lbl.configure(text=f"Armed — Switch to target editor! Starting in {delay:.1f}s...", text_color=APPLE_AMBER)
            self.btn_start.configure(state="disabled", text="Counting Down...", fg_color="#7A4A0B")
            self.btn_pause.configure(state="disabled")
            self._target_progress = 0.0
            self.progress_bar.configure(progress_color=APPLE_AMBER)

        elif state == EngineState.TYPING:
            target = details.get("target", {})
            title = target.get("title", "Active Editor")[:22]
            proc = target.get("process_name", "App")
            self.status_pill.configure(text="⚡ Typing", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)
            self.status_desc_lbl.configure(text=f"Typing into: {title} ({proc})", text_color=APPLE_GREEN)
            self.lbl_target_window.configure(text=f"Target: {proc.upper()}")
            self.btn_start.configure(state="disabled", text="⚡ Typing Active", fg_color="#17502B")
            self.btn_pause.configure(state="normal", text="⏸ Pause", fg_color="#181D2C", text_color=TEXT_PRIMARY)
            self.progress_bar.configure(progress_color=APPLE_GREEN)

        elif state == EngineState.PAUSED:
            reason = details.get("reason", "Paused")[:30]
            self.status_pill.configure(text="⏸ Paused", fg_color=APPLE_AMBER_GLOW, text_color=APPLE_AMBER)
            self.status_desc_lbl.configure(text=f"Paused: {reason}", text_color=APPLE_AMBER)
            self.btn_pause.configure(state="normal", text="▶ Resume", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)
            self.progress_bar.configure(progress_color=APPLE_AMBER)

        elif state == EngineState.STOPPED:
            self.status_pill.configure(text="🛑 Stopped", fg_color=APPLE_CORAL_GLOW, text_color=APPLE_CORAL)
            self.status_desc_lbl.configure(text="Emergency stop triggered (Esc pressed)", text_color=APPLE_CORAL)
            self.btn_start.configure(state="normal", text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]", fg_color=APPLE_GREEN)
            self.btn_pause.configure(state="disabled", text="⏸ Pause", fg_color="#181D2C", text_color=TEXT_MUTED)
            self.progress_bar.configure(progress_color=APPLE_CORAL)

        elif state == EngineState.COMPLETED:
            typed = details.get("total_typed", self.engine.chars_typed)
            sec = details.get("elapsed_sec", 0.0)
            self.status_pill.configure(text="✔ Done", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)
            self.status_desc_lbl.configure(text=f"Completed {typed} actions in {sec:.1f}s!", text_color=APPLE_GREEN)
            self.btn_start.configure(state="normal", text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]", fg_color=APPLE_GREEN)
            self.btn_pause.configure(state="disabled", text="⏸ Pause", fg_color="#181D2C", text_color=TEXT_MUTED)
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
            self.status_pill.configure(text=f"⏳ {seconds_left:.1f}s", fg_color=APPLE_AMBER_GLOW, text_color=APPLE_AMBER)
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
