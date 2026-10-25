"""
TYPO® — Precision Keystroke Automation
Apple Glass UI (visionOS / Liquid Glass Edition)

Design Philosophy:
- Translucent dark glassmorphism inspired by Apple visionOS & iOS Liquid Glass
- Deep obsidian liquid background (#060709) with frosted glass squircle cards (#12151D)
- Specular rim refraction borders (#252A38 / #383F54) that evoke physical beveled glass
- Luminous Apple Electric Green (#30D158) glow accents on active switches and execution pills
- Fluid pill navigation capsules, floating island controls, and smooth pill faders
- Clean, refined Apple typography (Segoe UI / Inter) with high-contrast legibility
- Full integration of all stealth capabilities: Cursor Wandering, Incremental Construction,
  Selection & Refactoring Simulation, Complexity Cadence Throttler, and Biometric Dynamics
"""

import os
import sys
import time
import queue
import winsound
import ctypes
from typing import Optional
import customtkinter as ctk

from typo.typing_engine import TypingEngine, EngineState
from typo.win32_api import GlobalHotKeyManager, PRIMARY_HOTKEY_LABEL
from typo.clipboard import get_current_clipboard, analyze_clipboard_content, set_test_clipboard_text

# ==========================================
# Apple Glass UI Color Palette & Glass Tokens
# ==========================================
# Liquid Obsidian Base
GLASS_BG = "#060709"               # Deep obsidian fluid backdrop
GLASS_SURFACE = "#0A0D13"          # Soft dark glass canvas
GLASS_SIDEBAR = "#0D1017"          # Frosted glass sidebar island

# Glass Card & Pill Materials (Squircle Slices)
GLASS_CARD = "#12151D"             # Frosted dark glass container
GLASS_CARD_HOVER = "#181C26"       # Luminous glass hover
GLASS_CARD_BORDER = "#252A38"      # Specular glass bevel border (1px hairline)
GLASS_CARD_BORDER_GLOW = "#3A4258" # Elevated rim highlight
GLASS_INSET = "#090B10"            # Inset glass well (for code & telemetry)
GLASS_INSET_BORDER = "#1A1D28"     # Inset boundary

# Floating Glass Pill Bar
GLASS_PILL_BAR = "#141720"         # Capsule container
GLASS_PILL_BAR_BORDER = "#262C3D"  # Capsule glass border
GLASS_PILL_INACTIVE = "#1A1E29"    # Inactive capsule item
GLASS_PILL_ACTIVE = "#102619"      # Active green glass pill
GLASS_PILL_ACTIVE_BORDER = "#205C35"

# Apple visionOS Luminous Accents
APPLE_GREEN = "#30D158"            # Apple visionOS electric neon green
APPLE_GREEN_HOVER = "#38E564"
APPLE_GREEN_GLOW = "#0E2916"       # Ambient green glow well
APPLE_BLUE = "#0A84FF"             # Apple system electric blue
APPLE_BLUE_GLOW = "#0C2344"
APPLE_CORAL = "#FF453A"            # Apple system coral / abort
APPLE_CORAL_GLOW = "#2E1416"
APPLE_AMBER = "#FF9F0A"            # Apple system warning amber
APPLE_AMBER_GLOW = "#2F1E08"
APPLE_PURPLE = "#BF5AF2"           # Apple system electric purple
APPLE_TRACK = "#181B26"            # Recessed capsule slider track

# Apple Modern High-Legibility Typography
TEXT_PRIMARY = "#FFFFFF"           # Crisp pure white
TEXT_SECONDARY = "#98989F"         # Apple secondary system text
TEXT_MUTED = "#555A6B"             # Muted annotations & technical indicators
TEXT_DIM = "#323746"               # Subtle glass grooves

# Typography Stack
FONT_FAMILY = "Segoe UI"
FONT_MONO_FAMILY = "Consolas"


def apply_dwm_glass(window):
    """Enables Windows 11 DWM dark titlebar with rounded glass composition."""
    try:
        if not getattr(window, "winfo_exists", None) or not window.winfo_exists():
            return
        window.update_idletasks()
        inner_hwnd = window.winfo_id()
        top_hwnd = ctypes.windll.user32.GetAncestor(inner_hwnd, 2)  # GA_ROOT
        if top_hwnd:
            dwmapi = ctypes.windll.dwmapi
            # Immersive Dark Mode (DWMWA_USE_IMMERSIVE_DARK_MODE = 20)
            dark_val = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(top_hwnd, 20, ctypes.byref(dark_val), ctypes.sizeof(dark_val))
            # Smooth rounded squircle corners (DWMWCP_ROUND = 2)
            round_val = ctypes.c_int(2)
            dwmapi.DwmSetWindowAttribute(top_hwnd, 33, ctypes.byref(round_val), ctypes.sizeof(round_val))
    except Exception:
        pass


class TypoApp(ctk.CTk):
    def __init__(self, init_hotkeys: bool = True):
        super().__init__()

        # Window Setup
        self.title("TYPO — Apple Glass UI Edition")
        self.geometry("1060x820")
        self.minsize(980, 720)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=GLASS_BG)

        # Core Engine & Automation Pipeline
        self.engine = TypingEngine()
        self.hotkey_mgr: Optional[GlobalHotKeyManager] = None
        self.current_hotkey_label = PRIMARY_HOTKEY_LABEL
        self._ui_queue = queue.Queue()
        self._last_clipboard_text = ""
        self.sound_enabled = True
        self.ghost_hud = None

        # Bind Callbacks
        self.engine.on_state_change = self._queue_state_change
        self.engine.on_progress = self._queue_progress
        self.engine.on_countdown = self._queue_countdown
        self.engine.on_error = self._queue_error

        # Main Layout: Sidebar + Canvas Workspace
        self._build_main_shell()

        # Initialize Global Hotkey (Alt + Z + T)
        if init_hotkeys:
            self._init_hotkeys()

        # Background loops
        self.after(35, self._process_ui_queue)
        self.after(1000, self._periodic_clipboard_check)
        self.after(400, self._refresh_clipboard_view)
        self.after(150, lambda: apply_dwm_glass(self))

        # Close hook
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ==========================================
    # Main Shell Architecture (Sidebar + Canvas)
    # ==========================================
    def _build_main_shell(self):
        self.root_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.root_container.pack(fill="both", expand=True)

        # ------------------------------------------
        # 1. Frosted Glass Sidebar Bay (Floating Squircle Island)
        # ------------------------------------------
        self.sidebar = ctk.CTkFrame(
            self.root_container,
            width=255,
            fg_color=GLASS_SIDEBAR,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Sidebar Header (Apple Vision Brand & Profile Capsule)
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=20, pady=(24, 16))

        # Top User Avatar / Status Capsule (like Image 1 "Hello, Michael")
        profile_row = ctk.CTkFrame(
            brand_frame,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=20,
            height=46
        )
        profile_row.pack(fill="x", pady=(0, 14))
        profile_row.pack_propagate(False)

        # Avatar circle icon with green status dot
        avatar_box = ctk.CTkFrame(
            profile_row,
            width=32,
            height=32,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER_GLOW,
            border_width=1,
            corner_radius=16
        )
        avatar_box.pack(side="left", padx=(8, 10))
        avatar_box.pack_propagate(False)

        ctk.CTkLabel(
            avatar_box,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_PRIMARY
        ).place(relx=0.5, rely=0.5, anchor="center")

        user_text_frame = ctk.CTkFrame(profile_row, fg_color="transparent")
        user_text_frame.pack(side="left", fill="y", pady=4)

        ctk.CTkLabel(
            user_text_frame,
            text="TYPO INSTRUMENT",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            user_text_frame,
            text="Vision Pro Glass",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        # Green glowing live status dot
        ctk.CTkLabel(
            profile_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=APPLE_GREEN
        ).pack(side="right", padx=(0, 12))

        # Large Headline Title
        title_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_box.pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(
            title_box,
            text="Control Studio",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="PRECISION INPUT ENGINE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=8, weight="bold"),
            text_color=APPLE_GREEN
        ).pack(anchor="w", pady=(1, 0))

        # Hairline glass divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color=GLASS_CARD_BORDER).pack(fill="x", padx=18, pady=(10, 14))

        # Live Cadence Glass Card (Inspired by Image 1 "Air Conditioner 22°" card)
        cadence_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=20
        )
        cadence_card.pack(fill="x", padx=16, pady=(0, 16))

        cad_inner = ctk.CTkFrame(cadence_card, fg_color="transparent")
        cad_inner.pack(fill="x", padx=14, pady=12)

        cad_hdr = ctk.CTkFrame(cad_inner, fg_color="transparent")
        cad_hdr.pack(fill="x")

        ctk.CTkLabel(
            cad_hdr,
            text="Active Velocity",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left")

        # Glowing green status capsule
        glow_pill = ctk.CTkLabel(
            cad_hdr,
            text="● LIVE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=8, weight="bold"),
            text_color=APPLE_GREEN,
            fg_color=APPLE_GREEN_GLOW,
            border_color=GLASS_PILL_ACTIVE_BORDER,
            border_width=1,
            corner_radius=8,
            padx=6,
            pady=2
        )
        glow_pill.pack(side="right")

        self.lbl_sidebar_wpm = ctk.CTkLabel(
            cad_inner,
            text="80 WPM",
            font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.lbl_sidebar_wpm.pack(anchor="w", pady=(4, 2))

        # Horizontal subtle scale (like 16° 18° 20° 22° in Image 1)
        scale_row = ctk.CTkFrame(cad_inner, fg_color="transparent")
        scale_row.pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(scale_row, text="40", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(scale_row, text="60", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left", expand=True)
        ctk.CTkLabel(scale_row, text="80", font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"), text_color=APPLE_GREEN).pack(side="left", expand=True)
        ctk.CTkLabel(scale_row, text="120", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left", expand=True)
        ctk.CTkLabel(scale_row, text="180", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="right")

        # Navigation Bay Slots (Image 1 Style Glass Pill Rows)
        nav_menu = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_menu.pack(fill="x", padx=14)

        nav_items = [
            ("Control Deck", True, "🎛"),
            ("Biometrics Lab", False, "⚡"),
            ("Code Buffer", False, "📋"),
            ("System Telemetry", False, "📊"),
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
                corner_radius=16,
                height=38
            )
            row_frame.pack(fill="x", pady=3)
            row_frame.pack_propagate(False)

            # Icon pill
            icon_col = APPLE_GREEN if is_active else TEXT_MUTED
            ctk.CTkLabel(
                row_frame,
                text=icon,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=icon_col
            ).pack(side="left", padx=(12, 4))

            btn = ctk.CTkLabel(
                row_frame,
                text=text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold" if is_active else "normal"),
                text_color=text_col,
                anchor="w",
                cursor="hand2"
            )
            btn.pack(side="left", fill="both", expand=True)

            if is_active:
                ctk.CTkLabel(
                    row_frame,
                    text="●",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=8),
                    text_color=APPLE_GREEN
                ).pack(side="right", padx=(0, 12))

        # Sidebar Bottom Hardware / Hotkey Card (Glass Island)
        bottom_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=20
        )
        bottom_card.pack(side="bottom", fill="x", padx=14, pady=18)

        ctk.CTkLabel(
            bottom_card,
            text="HARDWARE TRIGGER",
            font=ctk.CTkFont(family=FONT_FAMILY, size=8, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=14, pady=(12, 4))

        lbl_hk = ctk.CTkLabel(
            bottom_card,
            text=f"[ {self.current_hotkey_label} ]",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=12,
            padx=10,
            pady=4
        )
        lbl_hk.pack(anchor="w", padx=14, pady=(0, 6))

        ctk.CTkLabel(
            bottom_card,
            text="Emergency Abort: [ Esc ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=APPLE_CORAL
        ).pack(anchor="w", padx=14, pady=(0, 12))

        # ------------------------------------------
        # 2. Canvas Workspace (Apple Vision Glass Deck)
        # ------------------------------------------
        self.workspace = ctk.CTkFrame(self.root_container, fg_color=GLASS_BG, corner_radius=0)
        self.workspace.pack(side="right", fill="both", expand=True)

        # Top App Bar
        self._build_top_bar()

        # Scrollable Content Body
        self.body_scroll = ctk.CTkScrollableFrame(
            self.workspace,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#1F2330",
            scrollbar_button_hover_color="#2D3346"
        )
        self.body_scroll.pack(fill="both", expand=True, padx=22, pady=(0, 16))

        # Build Apple Glass Slices
        self._build_hero_status_card()
        self._build_precision_sliders_card()
        self._build_clipboard_card()
        self._build_feature_matrix_card()

    # ==========================================
    # Top Application Bar (Apple Glass Navigation)
    # ==========================================
    def _build_top_bar(self):
        bar = ctk.CTkFrame(self.workspace, fg_color="transparent", height=60)
        bar.pack(fill="x", padx=22, pady=(14, 8))
        bar.pack_propagate(False)

        # Left: Clean Apple Vision Breadcrumb & Title
        left_meta = ctk.CTkFrame(bar, fg_color="transparent")
        left_meta.pack(side="left")

        ctk.CTkLabel(
            left_meta,
            text="VISION OS // AUTOMATION STUDIO",
            font=ctk.CTkFont(family=FONT_FAMILY, size=8, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w")

        self.lbl_view_title = ctk.CTkLabel(
            left_meta,
            text="Control Deck · Dynamic Glass Sequencer",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.lbl_view_title.pack(anchor="w")

        # Right: Floating Glass Tool Pills
        right_tools = ctk.CTkFrame(bar, fg_color="transparent")
        right_tools.pack(side="right")

        self.btn_ghost_hud = ctk.CTkButton(
            right_tools,
            text="👻 Ghost HUD",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=34,
            corner_radius=17,
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
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=34,
            corner_radius=17,
            fg_color=GLASS_CARD,
            hover_color=GLASS_CARD_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._toggle_sound
        )
        self.btn_sound.pack(side="right", padx=(8, 0))

        # Target Window Pill
        self.lbl_target_window = ctk.CTkLabel(
            right_tools,
            text="Target // [ Waiting ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_SECONDARY,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=17,
            padx=14,
            pady=6
        )
        self.lbl_target_window.pack(side="right")

    # ==========================================
    # 1. Hero Telemetry & Action Deck (Apple Glass Widget)
    # ==========================================
    def _build_hero_status_card(self):
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=24
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
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=APPLE_GREEN
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hdr_row,
            text="Telemetry & Dispatch Engine",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            hdr_row,
            text="Apple Liquid Glass",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(side="right")

        # Top Controls Row: Status Capsule + Action Buttons
        ctrl_row = ctk.CTkFrame(inner, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=(0, 14))

        # Left: Live Status Pill
        pill_frame = ctk.CTkFrame(ctrl_row, fg_color="transparent")
        pill_frame.pack(side="left")

        self.status_pill = ctk.CTkLabel(
            pill_frame,
            text="● Ready",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color="#181B26",
            border_color=GLASS_CARD_BORDER_GLOW,
            border_width=1,
            corner_radius=14,
            padx=14,
            pady=5
        )
        self.status_pill.pack(side="left")

        self.status_desc_lbl = ctk.CTkLabel(
            pill_frame,
            text=f"Focus your target code editor and press {self.current_hotkey_label}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY
        )
        self.status_desc_lbl.pack(side="left", padx=12)

        # Right: Primary Action Buttons (Glowing Glass Pills)
        btn_frame = ctk.CTkFrame(ctrl_row, fg_color="transparent")
        btn_frame.pack(side="right")

        # Apple Electric Green Execution Pill
        self.btn_start = ctk.CTkButton(
            btn_frame,
            text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
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
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=38,
            width=80,
            corner_radius=19,
            fg_color="#181B26",
            hover_color="#242838",
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
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=38,
            width=100,
            corner_radius=19,
            fg_color=APPLE_CORAL_GLOW,
            hover_color="#3D181A",
            border_color=APPLE_CORAL,
            border_width=1,
            text_color=APPLE_CORAL,
            command=self._trigger_emergency_stop
        )
        self.btn_stop.pack(side="left")

        # Progress Bar (Apple Capsule Glass Track)
        self.progress_bar = ctk.CTkProgressBar(
            inner,
            height=6,
            corner_radius=3,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_GREEN
        )
        self.progress_bar.pack(fill="x", pady=(2, 16))
        self.progress_bar.set(0.0)

        # 4-Column Metric Grid (Apple Vision Glass Micro-Widgets)
        tele_grid = ctk.CTkFrame(inner, fg_color="transparent")
        tele_grid.pack(fill="x")
        tele_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Col 1: Progress
        c1 = ctk.CTkFrame(tele_grid, fg_color=GLASS_INSET, corner_radius=16, border_color=GLASS_INSET_BORDER, border_width=1)
        c1.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=2)
        ctk.CTkLabel(c1, text="PROGRESS", font=ctk.CTkFont(family=FONT_FAMILY, size=8, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 1))
        self.lbl_tele_progress = ctk.CTkLabel(c1, text="0 / 0 (0%)", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_tele_progress.pack(anchor="w", padx=14, pady=(0, 10))

        # Col 2: Speed
        c2 = ctk.CTkFrame(tele_grid, fg_color=GLASS_INSET, corner_radius=16, border_color=GLASS_INSET_BORDER, border_width=1)
        c2.grid(row=0, column=1, sticky="ew", padx=3, pady=2)
        ctk.CTkLabel(c2, text="VELOCITY", font=ctk.CTkFont(family=FONT_FAMILY, size=8, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 1))
        self.lbl_tele_speed = ctk.CTkLabel(c2, text="80.0 WPM", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=APPLE_GREEN)
        self.lbl_tele_speed.pack(anchor="w", padx=14, pady=(0, 10))

        # Col 3: Time
        c3 = ctk.CTkFrame(tele_grid, fg_color=GLASS_INSET, corner_radius=16, border_color=GLASS_INSET_BORDER, border_width=1)
        c3.grid(row=0, column=2, sticky="ew", padx=3, pady=2)
        ctk.CTkLabel(c3, text="ELAPSED / REMAIN", font=ctk.CTkFont(family=FONT_FAMILY, size=8, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 1))
        self.lbl_tele_time = ctk.CTkLabel(c3, text="00:00 / 00:00", font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"), text_color=TEXT_PRIMARY)
        self.lbl_tele_time.pack(anchor="w", padx=14, pady=(0, 10))

        # Col 4: Last Token
        c4 = ctk.CTkFrame(tele_grid, fg_color=GLASS_INSET, corner_radius=16, border_color=GLASS_INSET_BORDER, border_width=1)
        c4.grid(row=0, column=3, sticky="ew", padx=(5, 0), pady=2)
        ctk.CTkLabel(c4, text="LAST TOKEN // DWELL", font=ctk.CTkFont(family=FONT_FAMILY, size=8, weight="bold"), text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 1))
        self.lbl_tele_token = ctk.CTkLabel(c4, text="[ ↵ ] ~55ms", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=APPLE_BLUE)
        self.lbl_tele_token.pack(anchor="w", padx=14, pady=(0, 10))

    # ==========================================
    # 2. Apple Glass Precision Sliders
    # ==========================================
    def _build_precision_sliders_card(self):
        """
        Apple visionOS Glass Faders:
        - Sleek rounded capsule tracks with frosted glass value pills
        - Apple Green, Blue, Amber, and Purple accents
        - Ultra-smooth responsive millimeter calibration ticks
        """
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=24
        )
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=20)

        hdr_row = ctk.CTkFrame(inner, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            hdr_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=APPLE_BLUE
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hdr_row,
            text="Tactile Cadence & Velocity Faders",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        # 2-Column Grid for Horizontal Glass Faders
        faders_grid = ctk.CTkFrame(inner, fg_color="transparent")
        faders_grid.pack(fill="x")
        faders_grid.grid_columnconfigure((0, 1), weight=1)

        # ----------------------------------------------------
        # Fader 1: Typing Velocity (WPM)
        # ----------------------------------------------------
        f1_card = ctk.CTkFrame(faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=18)
        f1_card.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)

        f1_hdr = ctk.CTkFrame(f1_card, fg_color="transparent")
        f1_hdr.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            f1_hdr,
            text="PARAM 01 // TYPING VELOCITY",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left")

        self.lbl_wpm_val_pill = ctk.CTkLabel(
            f1_hdr,
            text="[ 80.0 WPM ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=APPLE_GREEN,
            fg_color=APPLE_GREEN_GLOW,
            border_color=GLASS_PILL_ACTIVE_BORDER,
            border_width=1,
            corner_radius=10,
            padx=10,
            pady=2
        )
        self.lbl_wpm_val_pill.pack(side="right")
        self.lbl_wpm = self.lbl_wpm_val_pill

        self.slider_wpm = ctk.CTkSlider(
            f1_card,
            from_=30,
            to=180,
            number_of_steps=150,
            height=14,
            corner_radius=7,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_GREEN,
            button_color=TEXT_PRIMARY,
            button_hover_color=TEXT_PRIMARY,
            button_corner_radius=8,
            button_length=16,
            command=self._on_wpm_change
        )
        self.slider_wpm.set(80)
        self.slider_wpm.pack(fill="x", padx=16, pady=(6, 4))

        f1_ticks = ctk.CTkFrame(f1_card, fg_color="transparent")
        f1_ticks.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(f1_ticks, text="30 WPM (Relaxed)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f1_ticks, text="80 [Nominal]", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left", expand=True)
        ctk.CTkLabel(f1_ticks, text="180 WPM (Extreme)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="right")

        # ----------------------------------------------------
        # Fader 2: Gaussian Jitter Variance
        # ----------------------------------------------------
        f2_card = ctk.CTkFrame(faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=18)
        f2_card.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=4)

        f2_hdr = ctk.CTkFrame(f2_card, fg_color="transparent")
        f2_hdr.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            f2_hdr,
            text="PARAM 02 // BIOLOGICAL JITTER",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left")

        self.lbl_jitter_val_pill = ctk.CTkLabel(
            f2_hdr,
            text="[ ±25 % ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=APPLE_BLUE,
            fg_color=APPLE_BLUE_GLOW,
            border_color="#183B6B",
            border_width=1,
            corner_radius=10,
            padx=10,
            pady=2
        )
        self.lbl_jitter_val_pill.pack(side="right")
        self.lbl_jitter = self.lbl_jitter_val_pill

        self.slider_jitter = ctk.CTkSlider(
            f2_card,
            from_=0,
            to=60,
            number_of_steps=60,
            height=14,
            corner_radius=7,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_BLUE,
            button_color=TEXT_PRIMARY,
            button_hover_color=TEXT_PRIMARY,
            button_corner_radius=8,
            button_length=16,
            command=self._on_jitter_change
        )
        self.slider_jitter.set(25)
        self.slider_jitter.pack(fill="x", padx=16, pady=(6, 4))

        f2_ticks = ctk.CTkFrame(f2_card, fg_color="transparent")
        f2_ticks.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(f2_ticks, text="0% (Machine)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f2_ticks, text="25% [Human]", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left", expand=True)
        ctk.CTkLabel(f2_ticks, text="60% (Chaotic)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="right")

        # ----------------------------------------------------
        # Fader 3: Autonomous Error Rate
        # ----------------------------------------------------
        f3_card = ctk.CTkFrame(faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=18)
        f3_card.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=4)

        f3_hdr = ctk.CTkFrame(f3_card, fg_color="transparent")
        f3_hdr.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            f3_hdr,
            text="PARAM 03 // ERROR INJECTION RATE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left")

        self.lbl_mistake_val_pill = ctk.CTkLabel(
            f3_hdr,
            text="[ 1.5 % ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=APPLE_AMBER,
            fg_color=APPLE_AMBER_GLOW,
            border_color="#4F330D",
            border_width=1,
            corner_radius=10,
            padx=10,
            pady=2
        )
        self.lbl_mistake_val_pill.pack(side="right")
        self.lbl_mistake = self.lbl_mistake_val_pill

        self.slider_mistake = ctk.CTkSlider(
            f3_card,
            from_=0.0,
            to=5.0,
            number_of_steps=50,
            height=14,
            corner_radius=7,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_AMBER,
            button_color=TEXT_PRIMARY,
            button_hover_color=TEXT_PRIMARY,
            button_corner_radius=8,
            button_length=16,
            command=self._on_mistake_rate_change
        )
        self.slider_mistake.set(1.5)
        self.slider_mistake.pack(fill="x", padx=16, pady=(6, 4))

        f3_ticks = ctk.CTkFrame(f3_card, fg_color="transparent")
        f3_ticks.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(f3_ticks, text="0.0% (Flawless)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f3_ticks, text="1.5% [Natural]", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left", expand=True)
        ctk.CTkLabel(f3_ticks, text="5.0% (Frequent)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="right")

        # ----------------------------------------------------
        # Fader 4: Arming Countdown Delay
        # ----------------------------------------------------
        f4_card = ctk.CTkFrame(faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=18)
        f4_card.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=4)

        f4_hdr = ctk.CTkFrame(f4_card, fg_color="transparent")
        f4_hdr.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            f4_hdr,
            text="PARAM 04 // ARMING COUNTDOWN",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left")

        self.lbl_delay_val_pill = ctk.CTkLabel(
            f4_hdr,
            text="[ 3.0 s ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=APPLE_PURPLE,
            fg_color="#2D173E",
            border_color="#4F266E",
            border_width=1,
            corner_radius=10,
            padx=10,
            pady=2
        )
        self.lbl_delay_val_pill.pack(side="right")
        self.lbl_delay = self.lbl_delay_val_pill

        self.slider_delay = ctk.CTkSlider(
            f4_card,
            from_=1.0,
            to=8.0,
            number_of_steps=70,
            height=14,
            corner_radius=7,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_PURPLE,
            button_color=TEXT_PRIMARY,
            button_hover_color=TEXT_PRIMARY,
            button_corner_radius=8,
            button_length=16,
            command=self._on_delay_change
        )
        self.slider_delay.set(3.0)
        self.slider_delay.pack(fill="x", padx=16, pady=(6, 4))

        f4_ticks = ctk.CTkFrame(f4_card, fg_color="transparent")
        f4_ticks.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(f4_ticks, text="1.0s (Rapid)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f4_ticks, text="3.0s [Nominal]", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left", expand=True)
        ctk.CTkLabel(f4_ticks, text="8.0s (Extended)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="right")

    # ==========================================
    # 3. Inset Glass Code Buffer
    # ==========================================
    def _build_clipboard_card(self):
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=24
        )
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=20)

        # Header Row
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        left_hdr = ctk.CTkFrame(header, fg_color="transparent")
        left_hdr.pack(side="left")

        title_row = ctk.CTkFrame(left_hdr, fg_color="transparent")
        title_row.pack(anchor="w")

        ctk.CTkLabel(
            title_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=APPLE_PURPLE
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            title_row,
            text="Volatile Code Memory Buffer",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        self.lbl_clip_meta = ctk.CTkLabel(
            left_hdr,
            text="0 Characters • 0 Lines • Standby",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_SECONDARY
        )
        self.lbl_clip_meta.pack(anchor="w", pady=(2, 0))

        # Right Action Buttons
        btn_grp = ctk.CTkFrame(header, fg_color="transparent")
        btn_grp.pack(side="right")

        btn_sample = ctk.CTkButton(
            btn_grp,
            text="[ Sample Code ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            height=30,
            corner_radius=15,
            fg_color="#181B26",
            hover_color="#242838",
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._load_sample_code
        )
        btn_sample.pack(side="left", padx=(0, 6))

        btn_refresh = ctk.CTkButton(
            btn_grp,
            text="[ Refresh ]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            height=30,
            corner_radius=15,
            fg_color="#181B26",
            hover_color="#242838",
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._refresh_clipboard_view
        )
        btn_refresh.pack(side="left")

        # Inset Code Textbox (Dark Obsidian Glass Inset)
        self.clip_textbox = ctk.CTkTextbox(
            inner,
            height=130,
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=11),
            fg_color=GLASS_INSET,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_INSET_BORDER,
            border_width=1,
            corner_radius=16,
            wrap="none"
        )
        self.clip_textbox.pack(fill="x")

    # ==========================================
    # 4. Apple Glass Feature Matrix & Switches
    # ==========================================
    def _build_feature_matrix_card(self):
        """
        Apple visionOS Glass Hardware Switches:
        - 5. Simulated Cursor Wandering
        - 15. Incremental Code Construction
        - 18. Selection & Refactoring Simulation
        - 17. Complexity Cadence Throttler
        - Biometric dynamics, autonomous mistake engine, auto-indent & bracket neutralizer
        """
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=24
        )
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=20)

        hdr_row = ctk.CTkFrame(inner, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            hdr_row,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=APPLE_GREEN
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            hdr_row,
            text="Stealth Capabilities & Biometric Simulation",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            hdr_row,
            text="8 Active Modules",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(side="right")

        sw_grid = ctk.CTkFrame(inner, fg_color="transparent")
        sw_grid.pack(fill="x")
        sw_grid.grid_columnconfigure((0, 1), weight=1)

        # Row 0: Feature 5 & Feature 17
        self.chk_cursor_wandering = ctk.CTkCheckBox(
            sw_grid,
            text="Simulated Cursor Wandering (Feat 5) — Anti-gaze drift",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=APPLE_GREEN,
            hover_color=APPLE_GREEN_HOVER,
            corner_radius=6,
            command=self._on_toggle_cursor_wandering
        )
        self.chk_cursor_wandering.select()
        self.chk_cursor_wandering.grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))

        self.chk_complexity_throttler = ctk.CTkCheckBox(
            sw_grid,
            text="Complexity Cadence Throttler (Feat 17) — Fast boilerplate, slow DP",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=APPLE_GREEN,
            hover_color=APPLE_GREEN_HOVER,
            corner_radius=6,
            command=self._on_toggle_complexity_throttler
        )
        self.chk_complexity_throttler.select()
        self.chk_complexity_throttler.grid(row=0, column=1, sticky="w", pady=6)

        # Row 1: Feature 15 & Feature 18
        self.chk_incremental = ctk.CTkCheckBox(
            sw_grid,
            text="Incremental Code Construct (Feat 15) — Signature & stub -> fill",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=APPLE_GREEN,
            hover_color=APPLE_GREEN_HOVER,
            corner_radius=6,
            command=self._on_toggle_incremental
        )
        if self.engine.incremental_construction_mode:
            self.chk_incremental.select()
        else:
            self.chk_incremental.deselect()
        self.chk_incremental.grid(row=1, column=0, sticky="w", pady=6, padx=(0, 10))

        self.chk_refactoring = ctk.CTkCheckBox(
            sw_grid,
            text="Selection & Refactoring Sim (Feat 18) — Word select & rename drift",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=APPLE_GREEN,
            hover_color=APPLE_GREEN_HOVER,
            corner_radius=6,
            command=self._on_toggle_refactoring
        )
        self.chk_refactoring.select()
        self.chk_refactoring.grid(row=1, column=1, sticky="w", pady=6)

        # Row 2: Biometrics & Mistakes
        self.chk_biometrics = ctk.CTkCheckBox(
            sw_grid,
            text="Biometric Key Dynamics — Gaussian dwell times (anti-tracker)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=APPLE_GREEN,
            hover_color=APPLE_GREEN_HOVER,
            corner_radius=6,
            command=self._on_toggle_biometrics
        )
        self.chk_biometrics.select()
        self.chk_biometrics.grid(row=2, column=0, sticky="w", pady=6, padx=(0, 10))

        self.chk_mistakes = ctk.CTkCheckBox(
            sw_grid,
            text="Autonomous Mistakes Engine — QWERTY typos & backspace engine",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=APPLE_GREEN,
            hover_color=APPLE_GREEN_HOVER,
            corner_radius=6,
            command=self._on_toggle_mistakes
        )
        self.chk_mistakes.select()
        self.chk_mistakes.grid(row=2, column=1, sticky="w", pady=6)

        # Row 3: Auto-Indent & Bracket Neutralizer
        self.chk_brackets = ctk.CTkCheckBox(
            sw_grid,
            text="Zero-Space Auto-Indent & Bracket Neutralizer — Monaco fix",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=APPLE_GREEN,
            hover_color=APPLE_GREEN_HOVER,
            corner_radius=6,
            command=self._on_toggle_bracket_neutralizer
        )
        self.chk_brackets.select()
        self.chk_brackets.grid(row=3, column=0, sticky="w", pady=6, padx=(0, 10))

        self.chk_focus = ctk.CTkCheckBox(
            sw_grid,
            text="Target Focus Auto-Pause — Suspends typing on window blur",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=APPLE_GREEN,
            hover_color=APPLE_GREEN_HOVER,
            corner_radius=6,
            command=self._on_toggle_focus
        )
        self.chk_focus.select()
        self.chk_focus.grid(row=3, column=1, sticky="w", pady=6)

    # ==========================================
    # Global Hotkey Manager & Callback Bindings
    # ==========================================
    def _init_hotkeys(self):
        def hotkey_callback():
            self._ui_queue.put(("hotkey_pressed", {}))

        self.hotkey_mgr = GlobalHotKeyManager(callback=hotkey_callback)
        registered = self.hotkey_mgr.start()
        if not registered:
            self._queue_error(self.hotkey_mgr.last_error or f"{PRIMARY_HOTKEY_LABEL} could not be registered.")

    def _on_wpm_change(self, val):
        wpm = round(val)
        self.lbl_wpm_val_pill.configure(text=f"[ {wpm:.1f} WPM ]")
        self.lbl_tele_speed.configure(text=f"{wpm:.1f} WPM")
        self.lbl_sidebar_wpm.configure(text=f"{wpm} WPM")
        self.engine.wpm = float(wpm)

    def _on_jitter_change(self, val):
        jitter = round(val)
        self.lbl_jitter_val_pill.configure(text=f"[ ±{jitter} % ]")
        self.engine.variance = float(jitter) / 100.0

    def _on_mistake_rate_change(self, val):
        rate_pct = round(val, 1)
        self.lbl_mistake_val_pill.configure(text=f"[ {rate_pct:.1f} % ]")
        self.engine.mistake_rate = float(rate_pct) / 100.0

    def _on_delay_change(self, val):
        delay = round(val, 1)
        self.lbl_delay_val_pill.configure(text=f"[ {delay:.1f} s ]")
        self.engine.safety_delay = float(delay)

    # Feature Toggles
    def _on_toggle_cursor_wandering(self):
        self.engine.cursor_wandering_enabled = bool(self.chk_cursor_wandering.get())

    def _on_toggle_complexity_throttler(self):
        self.engine.complexity_throttler_enabled = bool(self.chk_complexity_throttler.get())

    def _on_toggle_incremental(self):
        self.engine.incremental_construction_mode = bool(self.chk_incremental.get())

    def _on_toggle_refactoring(self):
        self.engine.refactoring_simulation_enabled = bool(self.chk_refactoring.get())

    def _on_toggle_focus(self):
        self.engine.auto_pause_on_focus_loss = bool(self.chk_focus.get())

    def _on_toggle_bracket_neutralizer(self):
        self.engine.neutralize_auto_closing_brackets = bool(self.chk_brackets.get())

    def _on_toggle_biometrics(self):
        self.engine.biometric_dynamics_enabled = bool(self.chk_biometrics.get())

    def _on_toggle_mistakes(self):
        self.engine.mistake_injection_enabled = bool(self.chk_mistakes.get())

    def _toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        self.btn_sound.configure(
            text="🔊 Audio On" if self.sound_enabled else "🔇 Audio Off",
            text_color=TEXT_PRIMARY if self.sound_enabled else TEXT_MUTED
        )

    def _toggle_ghost_hud(self):
        if not getattr(self, "ghost_hud", None) or not self.ghost_hud.winfo_exists():
            from typo.ghost_hud import GhostHUD
            self.ghost_hud = GhostHUD(self, on_close_callback=self._on_ghost_hud_closed)
            self.btn_ghost_hud.configure(text="👻 HUD Active", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)
            self.ghost_hud.update_state(self.engine.state, {"delay": self.engine.safety_delay, "target": self.engine.target_window})
        else:
            if self.ghost_hud.winfo_viewable():
                self.ghost_hud.hide_hud()
                self.btn_ghost_hud.configure(text="👻 Ghost HUD", fg_color=GLASS_CARD, text_color=TEXT_PRIMARY)
            else:
                self.ghost_hud.show_hud()
                self.btn_ghost_hud.configure(text="👻 HUD Active", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)

    def _on_ghost_hud_closed(self):
        if hasattr(self, "btn_ghost_hud"):
            self.btn_ghost_hud.configure(text="👻 Ghost HUD", fg_color=GLASS_CARD, text_color=TEXT_PRIMARY)

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
        if not getattr(self, "winfo_exists", None) or not self.winfo_exists():
            return
        if self.engine.state == EngineState.IDLE:
            text, is_empty, _ = get_current_clipboard()
            if text != self._last_clipboard_text:
                self._update_clipboard_display(text, is_empty)
        if self.winfo_exists():
            self.after(1000, self._periodic_clipboard_check)

    def _refresh_clipboard_view(self):
        if not getattr(self, "winfo_exists", None) or not self.winfo_exists():
            return
        text, is_empty, err_msg = get_current_clipboard()
        self._update_clipboard_display(text, is_empty, err_msg)

    def _update_clipboard_display(self, text: str, is_empty: bool, err_msg: str = ""):
        if not getattr(self, "winfo_exists", None) or not self.winfo_exists():
            return
        self._last_clipboard_text = text
        stats = analyze_clipboard_content(text)

        self.clip_textbox.configure(state="normal")
        self.clip_textbox.delete("1.0", "end")

        if is_empty:
            self.clip_textbox.insert("1.0", "(Windows Clipboard buffer is currently empty)\n\nCopy code from LeetCode or your IDE, or click '[ Sample Code ]' above.")
            self.lbl_clip_meta.configure(text="⚠️ Empty Clipboard Buffer", text_color=APPLE_AMBER)
        else:
            self.clip_textbox.insert("1.0", stats["preview"])
            code_tag = " • Code Detected" if stats.get("has_code", False) else ""
            lines = stats.get("line_count", stats.get("lines", 0))
            words = stats.get("word_count", stats.get("words", 0))
            self.lbl_clip_meta.configure(
                text=f"{stats.get('char_count', 0)} Characters • {lines} Lines • {words} Tokens{code_tag}",
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
        if not getattr(self, "winfo_exists", None) or not self.winfo_exists():
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

        if self.winfo_exists():
            self.after(30, self._process_ui_queue)

    def _handle_state_change(self, state: str, details: dict):
        if state == EngineState.IDLE:
            self.status_pill.configure(text="● Ready", fg_color="#181B26", text_color=TEXT_PRIMARY)
            self.status_desc_lbl.configure(text=f"Focus your target editor and press {self.current_hotkey_label}", text_color=TEXT_SECONDARY)
            self.btn_start.configure(state="normal", text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]", fg_color=APPLE_GREEN)
            self.btn_pause.configure(state="disabled", text="⏸ Pause", fg_color="#181B26", text_color=TEXT_MUTED)
            self.progress_bar.configure(progress_color=APPLE_GREEN)
            self.lbl_target_window.configure(text="Target // [ Waiting ]")

        elif state == EngineState.COUNTDOWN:
            delay = details.get("delay", self.engine.safety_delay)
            self.status_pill.configure(text=f"⏳ {delay:.1f}s", fg_color=APPLE_AMBER_GLOW, text_color=APPLE_AMBER)
            self.status_desc_lbl.configure(text=f"Armed — Switch to target editor! Starting in {delay:.1f}s...", text_color=APPLE_AMBER)
            self.btn_start.configure(state="disabled", text="⏳ Counting Down...", fg_color="#7A4A0B")
            self.btn_pause.configure(state="disabled")
            self.progress_bar.set(0.0)
            self.progress_bar.configure(progress_color=APPLE_AMBER)

        elif state == EngineState.TYPING:
            target = details.get("target", {})
            title = target.get("title", "Active Editor")[:22]
            proc = target.get("process_name", "App")
            self.status_pill.configure(text="⚡ Typing", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)
            self.status_desc_lbl.configure(text=f"Typing into: {title} ({proc})", text_color=APPLE_GREEN)
            self.lbl_target_window.configure(text=f"Target // {proc.upper()}")
            self.btn_start.configure(state="disabled", text="⚡ Typing Active...", fg_color="#17502B")
            self.btn_pause.configure(state="normal", text="⏸ Pause", fg_color="#181B26", text_color=TEXT_PRIMARY)
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
            self.btn_pause.configure(state="disabled", text="⏸ Pause", fg_color="#181B26", text_color=TEXT_MUTED)
            self.progress_bar.configure(progress_color=APPLE_CORAL)

        elif state == EngineState.COMPLETED:
            typed = details.get("total_typed", self.engine.chars_typed)
            sec = details.get("elapsed_sec", 0.0)
            self.status_pill.configure(text="✔ Completed", fg_color=APPLE_GREEN_GLOW, text_color=APPLE_GREEN)
            self.status_desc_lbl.configure(text=f"Completed {typed} actions in {sec:.1f}s!", text_color=APPLE_GREEN)
            self.btn_start.configure(state="normal", text=f"▶ Arm & Execute  [ {self.current_hotkey_label} ]", fg_color=APPLE_GREEN)
            self.btn_pause.configure(state="disabled", text="⏸ Pause", fg_color="#181B26", text_color=TEXT_MUTED)
            self.progress_bar.set(1.0)
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
            self.status_desc_lbl.configure(text=f"Armed — Focus target field now! Starting in {seconds_left:.1f}s...")
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

        self.progress_bar.set(pct / 100.0)
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
        """Graceful shutdown."""
        self.engine.stop()
        if self.hotkey_mgr:
            self.hotkey_mgr.stop()
        if getattr(self, "ghost_hud", None) and self.ghost_hud.winfo_exists():
            try:
                self.ghost_hud.destroy()
            except Exception:
                pass
        self.destroy()
