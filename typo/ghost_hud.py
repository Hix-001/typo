"""
TYPO® — Zero-Focus Transparent Ghost HUD
Nothing OS 5.0 Edition

Engineered with Win32 Extended Window Styles:
- WS_EX_NOACTIVATE (0x08000000): NEVER steals keyboard/window focus from Monaco, Chrome, or LeetCode
- WS_EX_TOPMOST (0x00000008): Floats above all windows including full-screen browsers
- WS_EX_TOOLWINDOW (0x00000080): Completely hidden from Alt+Tab and Windows Taskbar
- WS_EX_LAYERED (0x00080000): Hardware-accelerated alpha transparency
- Draggable anywhere on desktop without triggering browser 'window.blur' or 'visibilitychange'
- Designed with Nothing OS 5.0 pure OLED dark aesthetic and authentic Ndot / NType typography
"""

import sys
import ctypes
import customtkinter as ctk

from typo.win32_api import (
    user32,
    WS_EX_TOPMOST,
    WS_EX_TOOLWINDOW,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    GWL_EXSTYLE,
    HWND_TOPMOST,
    SWP_NOMOVE,
    SWP_NOSIZE,
    SWP_NOACTIVATE,
    SWP_SHOWWINDOW,
    LWA_ALPHA,
    PRIMARY_HOTKEY_LABEL
)
from typo.typing_engine import EngineState
from typo.fonts import register_fonts, FONT_DOT, FONT_BODY, FONT_MONO

register_fonts()

# Nothing OS HUD Design Tokens
HUD_BG = "#08090C"
HUD_BORDER = "#1E2028"
HUD_TEXT_WHITE = "#FFFFFF"
HUD_TEXT_MUTED = "#8A8F9E"
HUD_TRACK = "#181A22"

# State Accents
COLOR_IDLE = "#1C1E26"
COLOR_COUNTDOWN = "#FFB020"
COLOR_TYPING = "#D71921"
COLOR_PAUSED = "#FFB020"
COLOR_STOPPED = "#D71921"
COLOR_COMPLETED = "#00D68F"


class GhostHUD(ctk.CTkToplevel):
    """
    Zero-Focus Floating Telemetry HUD.
    Floats over target code editor and monitors progress without stealing focus.
    """
    def __init__(self, master=None, on_close_callback=None):
        super().__init__(master)

        self.on_close_callback = on_close_callback
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._target_hwnd = 0

        # Window Configuration
        self.title("TYPO Ghost HUD")
        self.geometry("380x92+100+100")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=HUD_BG)

        # Build Nothing OS Shell
        self._build_ui()

        # Apply Win32 WS_EX_NOACTIVATE Ghost Styles
        self.after(50, self._apply_win32_ghost_styles)

        # Position at top-right by default
        self.after(100, self._snap_to_top_right)

    def _build_ui(self):
        # Outer Border Frame (Nothing OS Pill Card)
        self.outer_frame = ctk.CTkFrame(
            self,
            fg_color=HUD_BG,
            border_color=HUD_BORDER,
            border_width=1,
            corner_radius=14
        )
        self.outer_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # Top Row
        top_row = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(8, 2))

        # Grip Icon & Title
        title_box = ctk.CTkFrame(top_row, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="■",
            font=ctk.CTkFont(family=FONT_BODY, size=9),
            text_color=COLOR_TYPING
        ).pack(side="left", padx=(0, 4))

        self.lbl_grip = ctk.CTkLabel(
            title_box,
            text="GHOST HUD",
            font=ctk.CTkFont(family=FONT_DOT, size=11),
            text_color=HUD_TEXT_WHITE,
            cursor="fleur"
        )
        self.lbl_grip.pack(side="left")

        # State Indicator Pill
        self.lbl_state_pill = ctk.CTkLabel(
            top_row,
            text="● IDLE",
            font=ctk.CTkFont(family=FONT_MONO, size=10, weight="bold"),
            text_color=HUD_TEXT_WHITE,
            fg_color=COLOR_IDLE,
            border_color=HUD_BORDER,
            border_width=1,
            corner_radius=8,
            padx=8,
            pady=2
        )
        self.lbl_state_pill.pack(side="left", padx=8)

        # Hotkey Hint Badge
        self.lbl_hotkey_hint = ctk.CTkLabel(
            top_row,
            text=f"[{PRIMARY_HOTKEY_LABEL}]",
            font=ctk.CTkFont(family=FONT_MONO, size=9, weight="bold"),
            text_color=HUD_TEXT_MUTED
        )
        self.lbl_hotkey_hint.pack(side="left", padx=4)

        # Close / Hide Button
        btn_close = ctk.CTkLabel(
            top_row,
            text="✕",
            font=ctk.CTkFont(family=FONT_BODY, size=11, weight="bold"),
            text_color=HUD_TEXT_MUTED,
            cursor="hand2"
        )
        btn_close.pack(side="right")
        btn_close.bind("<Button-1>", lambda e: self.hide_hud())

        # Middle Row: Progress Metrics
        mid_row = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        mid_row.pack(fill="x", padx=12, pady=(0, 2))

        self.lbl_metrics = ctk.CTkLabel(
            mid_row,
            text="Ready • Alt+Z+T to Arm • Esc to Abort",
            font=ctk.CTkFont(family=FONT_BODY, size=10),
            text_color=HUD_TEXT_WHITE
        )
        self.lbl_metrics.pack(side="left")

        self.lbl_stats = ctk.CTkLabel(
            mid_row,
            text="0 / 0 (0%)",
            font=ctk.CTkFont(family=FONT_DOT, size=11),
            text_color=HUD_TEXT_MUTED
        )
        self.lbl_stats.pack(side="right")

        # Bottom Row: Nothing OS Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self.outer_frame,
            height=4,
            corner_radius=2,
            fg_color=HUD_TRACK,
            progress_color=COLOR_TYPING
        )
        self.progress_bar.pack(fill="x", padx=12, pady=(4, 8))
        self.progress_bar.set(0.0)

        # Enable Draggability without Focus Stealing
        self._bind_drag(self.outer_frame)
        self._bind_drag(top_row)
        self._bind_drag(title_box)
        self._bind_drag(self.lbl_grip)
        self._bind_drag(mid_row)
        self._bind_drag(self.lbl_metrics)

    def _bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self._on_drag_start)
        widget.bind("<B1-Motion>", self._on_drag_motion)

    def _on_drag_start(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag_motion(self, event):
        x = self.winfo_x() + (event.x - self._drag_start_x)
        y = self.winfo_y() + (event.y - self._drag_start_y)
        self.geometry(f"+{x}+{y}")

    def _apply_win32_ghost_styles(self):
        """
        Applies low-level Win32 styles to guarantee zero focus stealing.
        """
        try:
            hwnd = self.winfo_id()
            parent = user32.GetParent(hwnd)
            root = user32.GetAncestor(hwnd, 2)  # GA_ROOT
            self._target_hwnd = root if root else (parent if parent else hwnd)

            ex_style = user32.GetWindowLongW(self._target_hwnd, GWL_EXSTYLE)
            ghost_style = ex_style | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_LAYERED
            user32.SetWindowLongW(self._target_hwnd, GWL_EXSTYLE, ghost_style)

            # Hardware alpha transparency (238 / 255 = ~93% opacity)
            user32.SetLayeredWindowAttributes(self._target_hwnd, 0, 238, LWA_ALPHA)

            user32.SetWindowPos(
                self._target_hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
        except Exception as e:
            print(f"[Ghost HUD] Style application error: {e}")

    def _snap_to_top_right(self):
        try:
            screen_width = self.winfo_screenwidth()
            hud_width = 380
            x = screen_width - hud_width - 32
            y = 36
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def update_state(self, state: str, details: dict):
        """Updates the Ghost HUD display based on engine state."""
        if state == EngineState.IDLE:
            self.lbl_state_pill.configure(text="● IDLE", fg_color=COLOR_IDLE)
            self.lbl_metrics.configure(text="Ready • Alt+Z+T to Arm • Esc to Abort")
            self.progress_bar.set(0.0)
            self.progress_bar.configure(progress_color=COLOR_TYPING)

        elif state == EngineState.COUNTDOWN:
            delay = details.get("delay", 3.0)
            self.lbl_state_pill.configure(text=f"⏳ {delay:.1f}s", fg_color="#2A1E0A")
            self.lbl_metrics.configure(text="Focus target editor now...")
            self.progress_bar.configure(progress_color=COLOR_COUNTDOWN)

        elif state == EngineState.TYPING:
            target = details.get("target", {})
            title = target.get("title", "Target")[:22]
            self.lbl_state_pill.configure(text="⌨ TYPING", fg_color="#07261C")
            self.lbl_metrics.configure(text=f"Target: {title}")
            self.progress_bar.configure(progress_color=COLOR_COMPLETED)

        elif state == EngineState.PAUSED:
            reason = details.get("reason", "Paused")[:28]
            self.lbl_state_pill.configure(text="⏸ PAUSED", fg_color="#2A1E0A")
            self.lbl_metrics.configure(text=reason)
            self.progress_bar.configure(progress_color=COLOR_PAUSED)

        elif state == EngineState.STOPPED:
            self.lbl_state_pill.configure(text="🛑 STOPPED", fg_color="#2A0E11")
            self.lbl_metrics.configure(text="Aborted (Esc Pressed)")
            self.progress_bar.configure(progress_color=COLOR_STOPPED)

        elif state == EngineState.COMPLETED:
            self.lbl_state_pill.configure(text="✔ COMPLETED", fg_color="#07261C")
            self.lbl_metrics.configure(text="All tokens typed successfully")
            self.progress_bar.set(1.0)
            self.progress_bar.configure(progress_color=COLOR_COMPLETED)

    def update_countdown(self, seconds_left: float):
        if seconds_left > 0:
            self.lbl_state_pill.configure(text=f"⏳ {seconds_left:.1f}s", fg_color="#2A1E0A")
            self.lbl_metrics.configure(text="Switch to target editor...")
        else:
            self.lbl_state_pill.configure(text="⌨ TYPING", fg_color="#07261C")

    def update_progress(self, pct: float, typed: int, total: int, elapsed_s: float, remaining_s: float, char: str):
        self.progress_bar.set(min(1.0, max(0.0, pct / 100.0)))
        self.lbl_stats.configure(text=f"{typed}/{total} ({pct:.0f}%)")

        char_disp = f"'{char}'" if char.strip() else f"[{char}]"
        self.lbl_metrics.configure(
            text=f"Typing: {char_disp} • Left: {remaining_s:.1f}s • {pct:.0f}%"
        )

    def show_hud(self):
        self.deiconify()
        self._apply_win32_ghost_styles()

    def hide_hud(self):
        self.withdraw()
        if self.on_close_callback:
            self.on_close_callback()
