"""
TYPO® — Studio Glass Edition (Apple visionOS & macOS Liquid Glass)
High-fidelity, responsive CustomTkinter UI for precision keystroke automation.

Design Specs:
- Translucent obsidian glass palette with optical specular borders
- Dynamic responsiveness (auto-adjusts columns & padding on window resize)
- True Apple visionOS switch toggles, capsule faders, and segmented status deck
- Monospace inset code buffer with real-time statistics
- Global hotkey, engine callbacks, and full test_ui.py compatibility
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
# Apple Glass Tokens & Color Space
# ==========================================
GLASS_BG = "#0B0E14"               # Deep obsidian canvas
GLASS_SIDEBAR = "#0F131C"          # Frosted glass sidebar bay
GLASS_CARD = "#141924"             # Elevated frosted squircle card
GLASS_CARD_HOVER = "#1A2130"       # Responsive hover highlight
GLASS_CARD_BORDER = "#232A3B"      # 1px hairline specular edge
GLASS_CARD_BORDER_GLOW = "#343E56" # Elevated specular highlight
GLASS_INSET = "#0D1017"            # Inset glass well
GLASS_INSET_BORDER = "#1A1F2C"     # Inset hairline border

# Capsule & Pill Material
GLASS_PILL_CONTAINER = "#131722"
GLASS_PILL_BORDER = "#252C3D"
GLASS_PILL_ACTIVE_BORDER = "#266B3F"

# Apple Accent Palette
APPLE_GREEN = "#30D158"            # visionOS Electric Green (Active / Ready)
APPLE_GREEN_HOVER = "#38E662"
APPLE_GREEN_TINT = "#112618"       # Ambient glow well
APPLE_BLUE = "#0A84FF"             # System Blue (Metrics / Telemetry)
APPLE_BLUE_TINT = "#0E223D"
APPLE_CORAL = "#FF453A"            # System Red / Coral (Abort)
APPLE_CORAL_TINT = "#2D1416"
APPLE_AMBER = "#FF9F0A"            # Warning / Paused
APPLE_AMBER_TINT = "#2D1E09"
APPLE_PURPLE = "#BF5AF2"           # Secondary Accents
APPLE_PURPLE_TINT = "#261536"
APPLE_TRACK = "#1E2433"            # Slider recessed track

# High-Legibility Typography
TEXT_PRIMARY = "#F5F5F7"           # Apple Off-White
TEXT_SECONDARY = "#98A1B2"         # Secondary descriptive text
TEXT_MUTED = "#5A6478"             # Metadata & bounds
TEXT_DIM = "#373E4F"

FONT_FAMILY = "Segoe UI"
FONT_MONO_FAMILY = "Consolas"


def apply_dwm_glass(window):
    """Enables Windows 11 DWM dark titlebar with rounded squircle composition."""
    try:
        if not getattr(window, "winfo_exists", None) or not window.winfo_exists():
            return
        window.update_idletasks()
        inner_hwnd = window.winfo_id()
        top_hwnd = ctypes.windll.user32.GetAncestor(inner_hwnd, 2)  # GA_ROOT
        if top_hwnd:
            dwmapi = ctypes.windll.dwmapi
            dark_val = ctypes.c_int(1)
            dwmapi.DwmSetWindowAttribute(top_hwnd, 20, ctypes.byref(dark_val), ctypes.sizeof(dark_val))
            round_val = ctypes.c_int(2)
            dwmapi.DwmSetWindowAttribute(top_hwnd, 33, ctypes.byref(round_val), ctypes.sizeof(round_val))
    except Exception:
        pass


class TypoApp(ctk.CTk):
    def __init__(self, init_hotkeys: bool = True):
        super().__init__()

        # Window Setup
        self.title("Typo — Studio Glass Edition")
        self.geometry("1120x860")
        self.minsize(860, 680)
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

        # Responsive Layout State
        self._last_window_width = 1120
        self._is_compact_mode = False

        # Bind Engine Callbacks
        self.engine.on_state_change = self._queue_state_change
        self.engine.on_progress = self._queue_progress
        self.engine.on_countdown = self._queue_countdown
        self.engine.on_error = self._queue_error

        # Main Layout: Sidebar + Canvas Workspace
        self._build_main_shell()

        # Bind Window Resize for Dynamic Adaptation
        self.bind("<Configure>", self._on_window_resize)

        # Initialize Global Hotkey
        if init_hotkeys:
            self._init_hotkeys()

        # Tracked background loops (zero leak timer dispatch)
        self._schedule(35, self._process_ui_queue)
        self._schedule(1000, self._periodic_clipboard_check)
        self._schedule(400, self._refresh_clipboard_view)
        self._schedule(150, lambda: apply_dwm_glass(self))

        # Close hook
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

    # ==========================================
    # Responsive Architecture & Window Sizing
    # ==========================================
    def _on_window_resize(self, event):
        """Dynamically adapt layout when resizing the window."""
        if event.widget != self:
            return

        width = event.width
        # Only trigger reflow on significant width changes
        if abs(width - self._last_window_width) < 25:
            return

        self._last_window_width = width
        should_compact = width < 980

        if should_compact != self._is_compact_mode:
            self._is_compact_mode = should_compact
            self._reflow_responsive_layout(should_compact)

    def _reflow_responsive_layout(self, compact: bool):
        """Adapts grids and paddings between standard dual-column and compact single-column."""
        if compact:
            # Collapse grids into 1 column for tight widths
            self.faders_grid.grid_columnconfigure(1, weight=0)
            self.f2_card.grid(row=1, column=0, sticky="ew", padx=0, pady=4)
            self.f3_card.grid(row=2, column=0, sticky="ew", padx=0, pady=4)
            self.f4_card.grid(row=3, column=0, sticky="ew", padx=0, pady=4)

            self.sw_grid.grid_columnconfigure(1, weight=0)
            for idx, sw_frame in enumerate(self.toggle_frames):
                sw_frame.grid(row=idx, column=0, sticky="ew", padx=0, pady=3)
        else:
            # Restore spacious 2-column layout
            self.faders_grid.grid_columnconfigure(1, weight=1)
            self.f1_card.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)
            self.f2_card.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=4)
            self.f3_card.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=4)
            self.f4_card.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=4)

            self.sw_grid.grid_columnconfigure(1, weight=1)
            for idx, sw_frame in enumerate(self.toggle_frames):
                row = idx // 2
                col = idx % 2
                sw_frame.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 6, 6 if col == 0 else 0), pady=3)

    # ==========================================
    # Main Shell Architecture
    # ==========================================
    def _build_main_shell(self):
        self.root_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.root_container.pack(fill="both", expand=True)

        # ------------------------------------------
        # 1. Frosted Glass Sidebar Bay
        # ------------------------------------------
        self.sidebar = ctk.CTkFrame(
            self.root_container,
            width=250,
            fg_color=GLASS_SIDEBAR,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # App Brand Capsule
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=18, pady=(22, 14))

        app_card = ctk.CTkFrame(
            brand_frame,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=16,
            height=48
        )
        app_card.pack(fill="x")
        app_card.pack_propagate(False)

        logo_box = ctk.CTkFrame(
            app_card,
            width=32,
            height=32,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER_GLOW,
            border_width=1,
            corner_radius=10
        )
        logo_box.pack(side="left", padx=(8, 10))
        logo_box.pack_propagate(False)

        ctk.CTkLabel(
            logo_box,
            text="⌥",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=APPLE_GREEN
        ).place(relx=0.5, rely=0.5, anchor="center")

        id_text = ctk.CTkFrame(app_card, fg_color="transparent")
        id_text.pack(side="left", fill="y", pady=5)

        ctk.CTkLabel(
            id_text,
            text="Typo Studio",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            id_text,
            text="Glass Automation",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=TEXT_SECONDARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            app_card,
            text="●",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=APPLE_GREEN
        ).pack(side="right", padx=(0, 12))

        # Cadence Glance Widget
        v_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=16
        )
        v_card.pack(fill="x", padx=16, pady=(8, 14))

        v_inner = ctk.CTkFrame(v_card, fg_color="transparent")
        v_inner.pack(fill="x", padx=14, pady=12)

        v_head = ctk.CTkFrame(v_inner, fg_color="transparent")
        v_head.pack(fill="x")

        ctk.CTkLabel(
            v_head,
            text="Current Pace",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left")

        ctk.CTkLabel(
            v_head,
            text="STANDBY",
            font=ctk.CTkFont(family=FONT_FAMILY, size=8, weight="bold"),
            text_color=APPLE_GREEN,
            fg_color=APPLE_GREEN_TINT,
            corner_radius=5,
            padx=6,
            pady=1
        ).pack(side="right")

        self.lbl_sidebar_wpm = ctk.CTkLabel(
            v_inner,
            text="80 WPM",
            font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.lbl_sidebar_wpm.pack(anchor="w", pady=(4, 1))

        ctk.CTkLabel(
            v_inner,
            text="Smooth Human Profile",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=TEXT_MUTED
        ).pack(anchor="w")

        # Sidebar Navigation Pill Bay
        nav_menu = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_menu.pack(fill="x", padx=14, pady=(2, 0))

        nav_items = [
            ("Sequencer Deck", True),
            ("Biometrics & Noise", False),
            ("Code Memory", False),
            ("Session Telemetry", False),
        ]

        for title, active in nav_items:
            pill = ctk.CTkFrame(
                nav_menu,
                fg_color=GLASS_CARD if active else "transparent",
                border_color=GLASS_CARD_BORDER_GLOW if active else GLASS_SIDEBAR,
                border_width=1 if active else 0,
                corner_radius=12,
                height=36
            )
            pill.pack(fill="x", pady=2)
            pill.pack_propagate(False)

            ctk.CTkLabel(
                pill,
                text="—" if active else "·",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=APPLE_GREEN if active else TEXT_MUTED
            ).pack(side="left", padx=(12, 8))

            ctk.CTkLabel(
                pill,
                text=title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold" if active else "normal"),
                text_color=TEXT_PRIMARY if active else TEXT_SECONDARY,
                anchor="w"
            ).pack(side="left", fill="both", expand=True)

        # Bottom Shortcut Island
        btm_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=16
        )
        btm_card.pack(side="bottom", fill="x", padx=14, pady=16)

        ctk.CTkLabel(
            btm_card,
            text="GLOBAL TRIGGER",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            btm_card,
            text=f"  {self.current_hotkey_label}  ",
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=7,
            pady=3
        ).pack(anchor="w", padx=12, pady=(0, 6))

        ctk.CTkLabel(
            btm_card,
            text="Abort typing anytime with Esc",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=TEXT_SECONDARY
        ).pack(anchor="w", padx=12, pady=(0, 10))

        # ------------------------------------------
        # 2. Glass Canvas Workspace
        # ------------------------------------------
        self.workspace = ctk.CTkFrame(self.root_container, fg_color=GLASS_BG, corner_radius=0)
        self.workspace.pack(side="right", fill="both", expand=True)

        # Header Bar
        self._build_top_bar()

        # Responsive Scrollable Body
        self.body_scroll = ctk.CTkScrollableFrame(
            self.workspace,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#1F2636",
            scrollbar_button_hover_color="#2D374D"
        )
        self.body_scroll.pack(fill="both", expand=True, padx=22, pady=(0, 16))

        # Glass Modular Slices
        self._build_hero_status_card()
        self._build_precision_sliders_card()
        self._build_clipboard_card()
        self._build_feature_matrix_card()

    # ==========================================
    # Top Application Bar
    # ==========================================
    def _build_top_bar(self):
        bar = ctk.CTkFrame(self.workspace, fg_color="transparent", height=56)
        bar.pack(fill="x", padx=22, pady=(14, 6))
        bar.pack_propagate(False)

        left_meta = ctk.CTkFrame(bar, fg_color="transparent")
        left_meta.pack(side="left")

        ctk.CTkLabel(
            left_meta,
            text="SEQUENCER DECK",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=TEXT_MUTED
        ).pack(anchor="w")

        self.lbl_view_title = ctk.CTkLabel(
            left_meta,
            text="Interactive Keystroke Studio",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.lbl_view_title.pack(anchor="w")

        right_tools = ctk.CTkFrame(bar, fg_color="transparent")
        right_tools.pack(side="right")

        self.lbl_target_window = ctk.CTkLabel(
            right_tools,
            text="Target: Standby",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_SECONDARY,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=14,
            padx=12,
            pady=4
        )
        self.lbl_target_window.pack(side="left", padx=(0, 8))

        self.btn_sound = ctk.CTkButton(
            right_tools,
            text="Audio On",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=30,
            corner_radius=15,
            fg_color=GLASS_CARD,
            hover_color=GLASS_CARD_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._toggle_sound
        )
        self.btn_sound.pack(side="left", padx=(0, 8))

        self.btn_ghost_hud = ctk.CTkButton(
            right_tools,
            text="Floating HUD",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=30,
            corner_radius=15,
            fg_color=GLASS_CARD,
            hover_color=GLASS_CARD_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._toggle_ghost_hud
        )
        self.btn_ghost_hud.pack(side="left")

    # ==========================================
    # 1. Hero Dispatch & Telemetry Deck
    # ==========================================
    def _build_hero_status_card(self):
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=20
        )
        card.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        # Control Row
        ctrl_row = ctk.CTkFrame(inner, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=(0, 12))

        pill_left = ctk.CTkFrame(ctrl_row, fg_color="transparent")
        pill_left.pack(side="left", fill="x", expand=True)

        self.status_pill = ctk.CTkLabel(
            pill_left,
            text="● Ready",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=GLASS_INSET,
            border_color=GLASS_CARD_BORDER_GLOW,
            border_width=1,
            corner_radius=13,
            padx=12,
            pady=5
        )
        self.status_pill.pack(side="left")

        self.status_desc_lbl = ctk.CTkLabel(
            pill_left,
            text=f"Switch to target editor and press {self.current_hotkey_label}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY
        )
        self.status_desc_lbl.pack(side="left", padx=10)

        # Action Buttons
        btn_grp = ctk.CTkFrame(ctrl_row, fg_color="transparent")
        btn_grp.pack(side="right")

        self.btn_start = ctk.CTkButton(
            btn_grp,
            text=f"Execute  [{self.current_hotkey_label}]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=34,
            corner_radius=17,
            fg_color=APPLE_GREEN,
            hover_color=APPLE_GREEN_HOVER,
            text_color="#000000",
            command=self._trigger_start
        )
        self.btn_start.pack(side="left", padx=(0, 6))

        self.btn_pause = ctk.CTkButton(
            btn_grp,
            text="Pause",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=34,
            width=70,
            corner_radius=17,
            fg_color=GLASS_INSET,
            hover_color=GLASS_CARD_HOVER,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            text_color=TEXT_MUTED,
            state="disabled",
            command=self._trigger_pause_resume
        )
        self.btn_pause.pack(side="left", padx=(0, 6))

        self.btn_stop = ctk.CTkButton(
            btn_grp,
            text="Stop [Esc]",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            height=34,
            width=82,
            corner_radius=17,
            fg_color=APPLE_CORAL_TINT,
            hover_color="#3D181A",
            border_color=APPLE_CORAL,
            border_width=1,
            text_color=APPLE_CORAL,
            command=self._trigger_emergency_stop
        )
        self.btn_stop.pack(side="left")

        # Smooth Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            inner,
            height=5,
            corner_radius=3,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_GREEN
        )
        self.progress_bar.pack(fill="x", pady=(2, 14))
        self.progress_bar.set(0.0)

        # 4 Responsive Metric Pills
        self.metrics_grid = ctk.CTkFrame(inner, fg_color="transparent")
        self.metrics_grid.pack(fill="x")
        self.metrics_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def make_metric(col, label, default_val, text_col=TEXT_PRIMARY):
            card = ctk.CTkFrame(
                self.metrics_grid,
                fg_color=GLASS_INSET,
                corner_radius=12,
                border_color=GLASS_INSET_BORDER,
                border_width=1
            )
            card.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 3, 0 if col == 3 else 3))
            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=8, weight="bold"),
                text_color=TEXT_MUTED
            ).pack(anchor="w", padx=10, pady=(6, 1))

            lbl = ctk.CTkLabel(
                card,
                text=default_val,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                text_color=text_col
            )
            lbl.pack(anchor="w", padx=10, pady=(0, 7))
            return lbl

        self.lbl_tele_progress = make_metric(0, "PROGRESS", "0 / 0 (0%)")
        self.lbl_tele_speed = make_metric(1, "CADENCE", "80.0 WPM", APPLE_GREEN)
        self.lbl_tele_time = make_metric(2, "ELAPSED / REMAIN", "00:00 / 00:00")
        self.lbl_tele_token = make_metric(3, "RECENT TOKEN", "Ready", APPLE_BLUE)

    # ==========================================
    # 2. Apple Glass Precision Faders
    # ==========================================
    def _build_precision_sliders_card(self):
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=20
        )
        card.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            hdr,
            text="Cadence & Timing Calibration",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            hdr,
            text="Natural Gaussian distribution",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED
        ).pack(side="right")

        # Responsive Dual-Column Grid
        self.faders_grid = ctk.CTkFrame(inner, fg_color="transparent")
        self.faders_grid.pack(fill="x")
        self.faders_grid.grid_columnconfigure((0, 1), weight=1)

        # --- Fader 1: Typing Speed ---
        self.f1_card = ctk.CTkFrame(self.faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=14)
        self.f1_card.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=4)

        f1_h = ctk.CTkFrame(self.f1_card, fg_color="transparent")
        f1_h.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(f1_h, text="Typing Speed", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        self.lbl_wpm_val_pill = ctk.CTkLabel(
            f1_h,
            text="80.0 WPM",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=APPLE_GREEN,
            fg_color=APPLE_GREEN_TINT,
            border_color=GLASS_PILL_ACTIVE_BORDER,
            border_width=1,
            corner_radius=7,
            padx=7,
            pady=1
        )
        self.lbl_wpm_val_pill.pack(side="right")
        self.lbl_wpm = self.lbl_wpm_val_pill

        self.slider_wpm = ctk.CTkSlider(
            self.f1_card,
            from_=30,
            to=180,
            number_of_steps=150,
            height=13,
            corner_radius=6,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_GREEN,
            button_color=TEXT_PRIMARY,
            button_hover_color=TEXT_PRIMARY,
            button_corner_radius=6,
            button_length=13,
            command=self._on_wpm_change
        )
        self.slider_wpm.set(80)
        self.slider_wpm.pack(fill="x", padx=12, pady=(4, 3))

        f1_sub = ctk.CTkFrame(self.f1_card, fg_color="transparent")
        f1_sub.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(f1_sub, text="30 WPM (Relaxed)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f1_sub, text="180 WPM (Extreme)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="right")

        # --- Fader 2: Jitter Variance ---
        self.f2_card = ctk.CTkFrame(self.faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=14)
        self.f2_card.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=4)

        f2_h = ctk.CTkFrame(self.f2_card, fg_color="transparent")
        f2_h.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(f2_h, text="Human Cadence Jitter", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        self.lbl_jitter_val_pill = ctk.CTkLabel(
            f2_h,
            text="±25 %",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=APPLE_BLUE,
            fg_color=APPLE_BLUE_TINT,
            border_color="#183B6B",
            border_width=1,
            corner_radius=7,
            padx=7,
            pady=1
        )
        self.lbl_jitter_val_pill.pack(side="right")
        self.lbl_jitter = self.lbl_jitter_val_pill

        self.slider_jitter = ctk.CTkSlider(
            self.f2_card,
            from_=0,
            to=60,
            number_of_steps=60,
            height=13,
            corner_radius=6,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_BLUE,
            button_color=TEXT_PRIMARY,
            button_hover_color=TEXT_PRIMARY,
            button_corner_radius=6,
            button_length=13,
            command=self._on_jitter_change
        )
        self.slider_jitter.set(25)
        self.slider_jitter.pack(fill="x", padx=12, pady=(4, 3))

        f2_sub = ctk.CTkFrame(self.f2_card, fg_color="transparent")
        f2_sub.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(f2_sub, text="0% (Strict)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f2_sub, text="60% (Organic)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="right")

        # --- Fader 3: Typo Rate ---
        self.f3_card = ctk.CTkFrame(self.faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=14)
        self.f3_card.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=4)

        f3_h = ctk.CTkFrame(self.f3_card, fg_color="transparent")
        f3_h.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(f3_h, text="Typo & Correction Rate", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        self.lbl_mistake_val_pill = ctk.CTkLabel(
            f3_h,
            text="1.5 %",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=APPLE_AMBER,
            fg_color=APPLE_AMBER_TINT,
            border_color="#4F330D",
            border_width=1,
            corner_radius=7,
            padx=7,
            pady=1
        )
        self.lbl_mistake_val_pill.pack(side="right")
        self.lbl_mistake = self.lbl_mistake_val_pill

        self.slider_mistake = ctk.CTkSlider(
            self.f3_card,
            from_=0.0,
            to=5.0,
            number_of_steps=50,
            height=13,
            corner_radius=6,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_AMBER,
            button_color=TEXT_PRIMARY,
            button_hover_color=TEXT_PRIMARY,
            button_corner_radius=6,
            button_length=13,
            command=self._on_mistake_rate_change
        )
        self.slider_mistake.set(1.5)
        self.slider_mistake.pack(fill="x", padx=12, pady=(4, 3))

        f3_sub = ctk.CTkFrame(self.f3_card, fg_color="transparent")
        f3_sub.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(f3_sub, text="0.0% (Flawless)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f3_sub, text="5.0% (Natural Typos)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="right")

        # --- Fader 4: Safety Countdown Delay ---
        self.f4_card = ctk.CTkFrame(self.faders_grid, fg_color=GLASS_INSET, border_color=GLASS_INSET_BORDER, border_width=1, corner_radius=14)
        self.f4_card.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=4)

        f4_h = ctk.CTkFrame(self.f4_card, fg_color="transparent")
        f4_h.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(f4_h, text="Safety Focus Countdown", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")

        self.lbl_delay_val_pill = ctk.CTkLabel(
            f4_h,
            text="3.0 s",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=APPLE_PURPLE,
            fg_color=APPLE_PURPLE_TINT,
            border_color="#4F266E",
            border_width=1,
            corner_radius=7,
            padx=7,
            pady=1
        )
        self.lbl_delay_val_pill.pack(side="right")
        self.lbl_delay = self.lbl_delay_val_pill

        self.slider_delay = ctk.CTkSlider(
            self.f4_card,
            from_=1.0,
            to=8.0,
            number_of_steps=70,
            height=13,
            corner_radius=6,
            fg_color=APPLE_TRACK,
            progress_color=APPLE_PURPLE,
            button_color=TEXT_PRIMARY,
            button_hover_color=TEXT_PRIMARY,
            button_corner_radius=6,
            button_length=13,
            command=self._on_delay_change
        )
        self.slider_delay.set(3.0)
        self.slider_delay.pack(fill="x", padx=12, pady=(4, 3))

        f4_sub = ctk.CTkFrame(self.f4_card, fg_color="transparent")
        f4_sub.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(f4_sub, text="1.0s (Fast Switch)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(f4_sub, text="8.0s (Relaxed)", font=ctk.CTkFont(family=FONT_FAMILY, size=8), text_color=TEXT_MUTED).pack(side="right")

    # ==========================================
    # 3. Clean Inset Code Buffer
    # ==========================================
    def _build_clipboard_card(self):
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=20
        )
        card.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        left_hdr = ctk.CTkFrame(header, fg_color="transparent")
        left_hdr.pack(side="left")

        ctk.CTkLabel(
            left_hdr,
            text="Clipboard Code Memory",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w")

        self.lbl_clip_meta = ctk.CTkLabel(
            left_hdr,
            text="Standby — No content loaded",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED
        )
        self.lbl_clip_meta.pack(anchor="w", pady=(1, 0))

        btn_grp = ctk.CTkFrame(header, fg_color="transparent")
        btn_grp.pack(side="right")

        btn_sample = ctk.CTkButton(
            btn_grp,
            text="Load Sample",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            height=28,
            corner_radius=14,
            fg_color=GLASS_INSET,
            hover_color=GLASS_CARD_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._load_sample_code
        )
        btn_sample.pack(side="left", padx=(0, 6))

        btn_refresh = ctk.CTkButton(
            btn_grp,
            text="Sync Clipboard",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            height=28,
            corner_radius=14,
            fg_color=GLASS_INSET,
            hover_color=GLASS_CARD_HOVER,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            command=self._refresh_clipboard_view
        )
        btn_refresh.pack(side="left")

        self.clip_textbox = ctk.CTkTextbox(
            inner,
            height=110,
            font=ctk.CTkFont(family=FONT_MONO_FAMILY, size=11),
            fg_color=GLASS_INSET,
            text_color=TEXT_PRIMARY,
            border_color=GLASS_INSET_BORDER,
            border_width=1,
            corner_radius=12,
            wrap="none"
        )
        self.clip_textbox.pack(fill="x")

    # ==========================================
    # 4. Apple Glass Capabilities & Responsive Toggles
    # ==========================================
    def _build_feature_matrix_card(self):
        card = ctk.CTkFrame(
            self.body_scroll,
            fg_color=GLASS_CARD,
            border_color=GLASS_CARD_BORDER,
            border_width=1,
            corner_radius=20
        )
        card.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            hdr,
            text="Stealth & Anti-Detection Capabilities",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            hdr,
            text="8 Active Modules",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=APPLE_GREEN,
            fg_color=APPLE_GREEN_TINT,
            corner_radius=6,
            padx=8,
            pady=2
        ).pack(side="right")

        self.sw_grid = ctk.CTkFrame(inner, fg_color="transparent")
        self.sw_grid.pack(fill="x")
        self.sw_grid.grid_columnconfigure((0, 1), weight=1)

        self.toggle_frames = []

        def make_toggle(row, col, title, desc, default_on, callback):
            frame = ctk.CTkFrame(
                self.sw_grid,
                fg_color=GLASS_INSET,
                border_color=GLASS_INSET_BORDER,
                border_width=1,
                corner_radius=12
            )
            frame.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 6, 6 if col == 0 else 0), pady=3)
            self.toggle_frames.append(frame)

            t_box = ctk.CTkFrame(frame, fg_color="transparent")
            t_box.pack(side="left", fill="both", expand=True, padx=12, pady=7)

            ctk.CTkLabel(
                t_box,
                text=title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                text_color=TEXT_PRIMARY
            ).pack(anchor="w")

            ctk.CTkLabel(
                t_box,
                text=desc,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                text_color=TEXT_MUTED
            ).pack(anchor="w")

            sw = ctk.CTkSwitch(
                frame,
                text="",
                width=40,
                switch_width=34,
                switch_height=18,
                progress_color=APPLE_GREEN,
                button_color=TEXT_PRIMARY,
                button_hover_color=TEXT_PRIMARY,
                fg_color=APPLE_TRACK,
                command=callback
            )
            sw.pack(side="right", padx=(0, 12))
            if default_on:
                sw.select()
            else:
                sw.deselect()
            return sw

        # Toggles registered for auto-reflow
        self.chk_cursor_wandering = make_toggle(0, 0, "Simulated Cursor Wandering", "Random micro-mouse drifting to defeat eye/gaze tracking", True, self._on_toggle_cursor_wandering)
        self.chk_complexity_throttler = make_toggle(0, 1, "Complexity Cadence Throttler", "Speed through boilerplate, slow down through dense logic", True, self._on_toggle_complexity_throttler)
        self.chk_incremental = make_toggle(1, 0, "Incremental Code Construction", "Types function signatures first, then iteratively fills bodies", self.engine.incremental_construction_mode, self._on_toggle_incremental)
        self.chk_refactoring = make_toggle(1, 1, "Refactoring & Selection Drift", "Simulates cursor navigation, highlighting, and variable renaming", True, self._on_toggle_refactoring)
        self.chk_biometrics = make_toggle(2, 0, "Biometric Gaussian Dynamics", "Variable key dwell & inter-keystroke intervals", True, self._on_toggle_biometrics)
        self.chk_mistakes = make_toggle(2, 1, "Organic Typos & Backspace", "QWERTY neighbor substitutions with natural backspace recovery", True, self._on_toggle_mistakes)
        self.chk_brackets = make_toggle(3, 0, "Bracket & Indent Neutralizer", "Neutralizes Monaco / VS Code auto-closing pairs & duplicate tabs", True, self._on_toggle_bracket_neutralizer)
        self.chk_focus = make_toggle(3, 1, "Focus Loss Auto-Pause", "Immediately suspends keystrokes if the target window blurs", True, self._on_toggle_focus)

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
        self.lbl_wpm_val_pill.configure(text=f"{wpm:.1f} WPM")
        self.lbl_tele_speed.configure(text=f"{wpm:.1f} WPM")
        self.lbl_sidebar_wpm.configure(text=f"{wpm} WPM")
        self.engine.wpm = float(wpm)

    def _on_jitter_change(self, val):
        jitter = round(val)
        self.lbl_jitter_val_pill.configure(text=f"±{jitter} %")
        self.engine.variance = float(jitter) / 100.0

    def _on_mistake_rate_change(self, val):
        rate_pct = round(val, 1)
        self.lbl_mistake_val_pill.configure(text=f"{rate_pct:.1f} %")
        self.engine.mistake_rate = float(rate_pct) / 100.0

    def _on_delay_change(self, val):
        delay = round(val, 1)
        self.lbl_delay_val_pill.configure(text=f"{delay:.1f} s")
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
            text="Audio On" if self.sound_enabled else "Audio Off",
            text_color=TEXT_PRIMARY if self.sound_enabled else TEXT_MUTED
        )

    def _toggle_ghost_hud(self):
        if not getattr(self, "ghost_hud", None) or not self.ghost_hud.winfo_exists():
            from typo.ghost_hud import GhostHUD
            self.ghost_hud = GhostHUD(self, on_close_callback=self._on_ghost_hud_closed)
            self.btn_ghost_hud.configure(text="HUD Active", fg_color=APPLE_GREEN_TINT, text_color=APPLE_GREEN)
            self.ghost_hud.update_state(self.engine.state, {"delay": self.engine.safety_delay, "target": self.engine.target_window})
        else:
            if self.ghost_hud.winfo_viewable():
                self.ghost_hud.hide_hud()
                self.btn_ghost_hud.configure(text="Floating HUD", fg_color=GLASS_CARD, text_color=TEXT_PRIMARY)
            else:
                self.ghost_hud.show_hud()
                self.btn_ghost_hud.configure(text="HUD Active", fg_color=APPLE_GREEN_TINT, text_color=APPLE_GREEN)

    def _on_ghost_hud_closed(self):
        if hasattr(self, "btn_ghost_hud"):
            self.btn_ghost_hud.configure(text="Floating HUD", fg_color=GLASS_CARD, text_color=TEXT_PRIMARY)

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
            # Calculate lightweight O(1) fingerprint instead of caching massive text buffers
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
            self.clip_textbox.insert("1.0", "Windows clipboard buffer is empty.\n\nCopy source code from your IDE, or click 'Load Sample' above.")
            self.lbl_clip_meta.configure(text="Clipboard empty", text_color=APPLE_AMBER)
        else:
            self.clip_textbox.insert("1.0", stats["preview"])
            code_tag = " • Code detected" if stats.get("has_code", False) else ""
            lines = stats.get("line_count", stats.get("lines", 0))
            words = stats.get("word_count", stats.get("words", 0))
            self.lbl_clip_meta.configure(
                text=f"{stats.get('char_count', 0)} chars • {lines} lines • {words} tokens{code_tag}",
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
            self.status_pill.configure(text="● Ready", fg_color=GLASS_INSET, text_color=TEXT_PRIMARY)
            self.status_desc_lbl.configure(text=f"Switch to target editor and press {self.current_hotkey_label}", text_color=TEXT_SECONDARY)
            self.btn_start.configure(state="normal", text=f"Execute  [{self.current_hotkey_label}]", fg_color=APPLE_GREEN)
            self.btn_pause.configure(state="disabled", text="Pause", fg_color=GLASS_INSET, text_color=TEXT_MUTED)
            self.progress_bar.configure(progress_color=APPLE_GREEN)
            self.lbl_target_window.configure(text="Target: Standby")

        elif state == EngineState.COUNTDOWN:
            delay = details.get("delay", self.engine.safety_delay)
            self.status_pill.configure(text=f"⏳ {delay:.1f}s", fg_color=APPLE_AMBER_TINT, text_color=APPLE_AMBER)
            self.status_desc_lbl.configure(text=f"Armed — Switch to target editor! Starting in {delay:.1f}s...", text_color=APPLE_AMBER)
            self.btn_start.configure(state="disabled", text="Counting down...", fg_color="#7A4A0B")
            self.btn_pause.configure(state="disabled")
            self.progress_bar.set(0.0)
            self.progress_bar.configure(progress_color=APPLE_AMBER)

        elif state == EngineState.TYPING:
            target = details.get("target", {})
            title = target.get("title", "Active Editor")[:22]
            proc = target.get("process_name", "App")
            self.status_pill.configure(text="⚡ Typing", fg_color=APPLE_GREEN_TINT, text_color=APPLE_GREEN)
            self.status_desc_lbl.configure(text=f"Active in {title} ({proc})", text_color=APPLE_GREEN)
            self.lbl_target_window.configure(text=f"Target: {proc.upper()}")
            self.btn_start.configure(state="disabled", text="Typing Active", fg_color="#17502B")
            self.btn_pause.configure(state="normal", text="Pause", fg_color=GLASS_INSET, text_color=TEXT_PRIMARY)
            self.progress_bar.configure(progress_color=APPLE_GREEN)

        elif state == EngineState.PAUSED:
            reason = details.get("reason", "Paused")[:30]
            self.status_pill.configure(text="⏸ Paused", fg_color=APPLE_AMBER_TINT, text_color=APPLE_AMBER)
            self.status_desc_lbl.configure(text=f"Paused: {reason}", text_color=APPLE_AMBER)
            self.btn_pause.configure(state="normal", text="Resume", fg_color=APPLE_GREEN_TINT, text_color=APPLE_GREEN)
            self.progress_bar.configure(progress_color=APPLE_AMBER)

        elif state == EngineState.STOPPED:
            self.status_pill.configure(text="🛑 Stopped", fg_color=APPLE_CORAL_TINT, text_color=APPLE_CORAL)
            self.status_desc_lbl.configure(text="Execution stopped via Esc key", text_color=APPLE_CORAL)
            self.btn_start.configure(state="normal", text=f"Execute  [{self.current_hotkey_label}]", fg_color=APPLE_GREEN)
            self.btn_pause.configure(state="disabled", text="Pause", fg_color=GLASS_INSET, text_color=TEXT_MUTED)
            self.progress_bar.configure(progress_color=APPLE_CORAL)

        elif state == EngineState.COMPLETED:
            typed = details.get("total_typed", self.engine.chars_typed)
            sec = details.get("elapsed_sec", 0.0)
            self.status_pill.configure(text="✔ Done", fg_color=APPLE_GREEN_TINT, text_color=APPLE_GREEN)
            self.status_desc_lbl.configure(text=f"Completed {typed} actions in {sec:.1f}s", text_color=APPLE_GREEN)
            self.btn_start.configure(state="normal", text=f"Execute  [{self.current_hotkey_label}]", fg_color=APPLE_GREEN)
            self.btn_pause.configure(state="disabled", text="Pause", fg_color=GLASS_INSET, text_color=TEXT_MUTED)
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
            self.status_pill.configure(text=f"⏳ {seconds_left:.1f}s", fg_color=APPLE_AMBER_TINT, text_color=APPLE_AMBER)
            self.status_desc_lbl.configure(text=f"Armed — Switch to target window! Starting in {seconds_left:.1f}s...")
        else:
            self.status_pill.configure(text="⚡ Typing", fg_color=APPLE_GREEN_TINT, text_color=APPLE_GREEN)
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
            self.lbl_tele_token.configure(text=f"{clean_ch}")

        if getattr(self, "ghost_hud", None) and self.ghost_hud.winfo_exists():
            try:
                self.ghost_hud.update_progress(pct, typed, total, elapsed, remaining, char)
            except Exception:
                pass

    def _handle_error(self, message: str):
        self.status_pill.configure(text="Notice", fg_color=APPLE_CORAL_TINT, text_color=APPLE_CORAL)
        self.status_desc_lbl.configure(text=message, text_color=APPLE_CORAL)

    def _on_close(self):
        """Graceful shutdown with zero timer leaks and memory release."""
        self._is_closing = True

        # Cancel all pending after timer callbacks immediately
        for after_id in list(self._after_ids):
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self._after_ids.clear()

        # Stop automation engine and unhook global low-level listeners
        self.engine.stop()
        if self.hotkey_mgr:
            self.hotkey_mgr.stop()

        # Safely teardown Ghost HUD if open
        if getattr(self, "ghost_hud", None) and self.ghost_hud.winfo_exists():
            try:
                self.ghost_hud.destroy()
            except Exception:
                pass
            self.ghost_hud = None

        # Destroy window widgets
        try:
            self.destroy()
        except Exception:
            pass

        # Explicit garbage collection pass
        try:
            import gc
            gc.collect()
        except Exception:
            pass
