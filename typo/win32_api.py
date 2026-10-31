"""
TYPO - Windows Native Automation API Module
Provides low-level Windows API integration via ctypes:
- SendInput with KEYEVENTF_UNICODE (bypasses keyboard layouts, IME, and shift states)
- UTF-16 surrogate pair support for emojis and astral symbols
- Dedicated Global HotKey detection (Alt + Z + T)
- Safe Unicode clipboard retrieval without modification
- Foreground window tracking, title detection, and process identification
- Instant millisecond emergency abort hook via GetAsyncKeyState (VK_ESCAPE)
"""

import sys
import ctypes
from ctypes import wintypes
import threading
import queue
import time
import random
from typing import Optional
from pynput.keyboard import Key, KeyCode, Listener


if sys.platform != "win32":
    raise OSError("TYPO Windows Automation API requires Microsoft Windows.")

# Win32 DLL references
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
try:
    psapi = ctypes.windll.psapi
except Exception:
    psapi = None

# ==========================================
# Win32 Constants
# ==========================================
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_DELETE = 0x2E

PRIMARY_HOTKEY_LABEL = "Alt + Z + T"


PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

# Extended Window Styles & Ghost HUD Constants
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000

GWL_EXSTYLE = -20
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002


# ==========================================
# Ctypes Struct Definitions for 64-bit / 32-bit
# ==========================================
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUT_UNION)
    ]

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

LONG_PTR = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long

if hasattr(user32, "GetWindowLongPtrW"):
    _GetWindowLongPtr = user32.GetWindowLongPtrW
    _SetWindowLongPtr = user32.SetWindowLongPtrW
else:
    _GetWindowLongPtr = user32.GetWindowLongW
    _SetWindowLongPtr = user32.SetWindowLongW

_GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
_GetWindowLongPtr.restype = LONG_PTR
_SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
_SetWindowLongPtr.restype = LONG_PTR

# Setup Win32 function signatures
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL

user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL

user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = wintypes.SHORT

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL

user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL

user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE

user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND

user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND

user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.COLORREF, wintypes.BYTE, wintypes.DWORD]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL

user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL

if hasattr(user32, "GetClipboardSequenceNumber"):
    user32.GetClipboardSequenceNumber.argtypes = []
    user32.GetClipboardSequenceNumber.restype = wintypes.DWORD

user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL

user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL

kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p

kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL

kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalFree.restype = wintypes.HGLOBAL

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

if psapi:
    psapi.GetModuleBaseNameW.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    psapi.GetModuleBaseNameW.restype = wintypes.DWORD


# ==========================================
# Clipboard Management
# ==========================================
def read_clipboard_unicode(retries=3, delay_between=0.05) -> tuple[str, bool, str]:
    """
    Safely retrieves unicode text from the Windows clipboard without modifying it.
    Returns: (text, is_empty, error_message)
    """
    for attempt in range(retries):
        if user32.OpenClipboard(None):
            try:
                h_glb = user32.GetClipboardData(CF_UNICODETEXT)
                if not h_glb:
                    return ("", True, "Clipboard contains no text data.")
                
                ptr = kernel32.GlobalLock(h_glb)
                if not ptr:
                    return ("", True, "Failed to lock clipboard memory.")
                
                try:
                    text = ctypes.c_wchar_p(ptr).value
                    if text is None or len(text) == 0:
                        return ("", True, "Clipboard is empty.")
                    return (text, False, "")
                finally:
                    kernel32.GlobalUnlock(h_glb)
            finally:
                user32.CloseClipboard()
        time.sleep(delay_between)
    
    return ("", True, "Could not open Windows clipboard (locked by another application).")


def get_clipboard_sequence_number() -> int:
    """
    Returns the Windows clipboard sequence number.
    Increments whenever clipboard contents change.
    Extremely fast, non-locking, and zero-allocation.
    """
    try:
        if hasattr(user32, "GetClipboardSequenceNumber"):
            return int(user32.GetClipboardSequenceNumber())
    except Exception:
        pass
    return 0


# ==========================================
# Window & Process Inspection
# ==========================================
def get_foreground_window_info() -> dict:
    """
    Returns information regarding the currently active foreground window.
    {
        'hwnd': int,
        'title': str,
        'pid': int,
        'process_name': str
    }
    """
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return {"hwnd": 0, "title": "No Active Window", "pid": 0, "process_name": "Unknown"}
    
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    title = buf.value.strip() or "Untitled Window"
    
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    process_name = "Unknown"
    if psapi and pid.value:
        h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value)
        if h_process:
            try:
                proc_buf = ctypes.create_unicode_buffer(260)
                if psapi.GetModuleBaseNameW(h_process, None, proc_buf, 260):
                    process_name = proc_buf.value
            finally:
                kernel32.CloseHandle(h_process)
                
    return {
        "hwnd": hwnd,
        "title": title,
        "pid": pid.value,
        "process_name": process_name
    }


def is_escape_pressed() -> bool:
    """
    Non-blocking check if Escape key is currently physically held down.
    High bit is set if the key is down.
    """
    return bool(user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000)


# ==========================================
# Keystroke Simulation (SendInput + Biometrics)
# ==========================================
def send_unicode_down(code_unit: int) -> bool:
    """Sends KeyDown for a UTF-16 code unit."""
    inp = (INPUT * 1)()
    inp[0].type = INPUT_KEYBOARD
    inp[0].u.ki.wVk = 0
    inp[0].u.ki.wScan = code_unit
    inp[0].u.ki.dwFlags = KEYEVENTF_UNICODE
    inp[0].u.ki.time = 0
    inp[0].u.ki.dwExtraInfo = 0
    return user32.SendInput(1, inp, ctypes.sizeof(INPUT)) == 1


def send_unicode_up(code_unit: int) -> bool:
    """Sends KeyUp for a UTF-16 code unit."""
    inp = (INPUT * 1)()
    inp[0].type = INPUT_KEYBOARD
    inp[0].u.ki.wVk = 0
    inp[0].u.ki.wScan = code_unit
    inp[0].u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    inp[0].u.ki.time = 0
    inp[0].u.ki.dwExtraInfo = 0
    return user32.SendInput(1, inp, ctypes.sizeof(INPUT)) == 1


def send_virtual_key_down(vk_code: int) -> bool:
    """Sends KeyDown for a standard virtual key code."""
    inp = (INPUT * 1)()
    inp[0].type = INPUT_KEYBOARD
    inp[0].u.ki.wVk = vk_code
    inp[0].u.ki.wScan = 0
    inp[0].u.ki.dwFlags = 0
    inp[0].u.ki.time = 0
    inp[0].u.ki.dwExtraInfo = 0
    return user32.SendInput(1, inp, ctypes.sizeof(INPUT)) == 1


def send_virtual_key_up(vk_code: int) -> bool:
    """Sends KeyUp for a standard virtual key code."""
    inp = (INPUT * 1)()
    inp[0].type = INPUT_KEYBOARD
    inp[0].u.ki.wVk = vk_code
    inp[0].u.ki.wScan = 0
    inp[0].u.ki.dwFlags = KEYEVENTF_KEYUP
    inp[0].u.ki.time = 0
    inp[0].u.ki.dwExtraInfo = 0
    return user32.SendInput(1, inp, ctypes.sizeof(INPUT)) == 1


def send_unicode_codepoint(code_unit: int) -> bool:
    """
    Sends a single UTF-16 code unit using SendInput with KEYEVENTF_UNICODE.
    Bypasses keyboard layouts, CapsLock, and shift modifiers.
    """
    inputs = (INPUT * 2)()
    
    # Key down
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].u.ki.wVk = 0
    inputs[0].u.ki.wScan = code_unit
    inputs[0].u.ki.dwFlags = KEYEVENTF_UNICODE
    inputs[0].u.ki.time = 0
    inputs[0].u.ki.dwExtraInfo = 0
    
    # Key up
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].u.ki.wVk = 0
    inputs[1].u.ki.wScan = code_unit
    inputs[1].u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    inputs[1].u.ki.time = 0
    inputs[1].u.ki.dwExtraInfo = 0
    
    sent = user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
    return sent == 2


def send_virtual_key(vk_code: int) -> bool:
    """
    Sends a standard virtual key (e.g. VK_RETURN, VK_TAB, VK_BACK).
    """
    inputs = (INPUT * 2)()
    
    # Key down
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].u.ki.wVk = vk_code
    inputs[0].u.ki.wScan = 0
    inputs[0].u.ki.dwFlags = 0
    inputs[0].u.ki.time = 0
    inputs[0].u.ki.dwExtraInfo = 0
    
    # Key up
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].u.ki.wVk = vk_code
    inputs[1].u.ki.wScan = 0
    inputs[1].u.ki.dwFlags = KEYEVENTF_KEYUP
    inputs[1].u.ki.time = 0
    inputs[1].u.ki.dwExtraInfo = 0
    
    sent = user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
    return sent == 2


def send_unicode_with_dwell(code_unit: int, dwell_s: float = 0.05) -> bool:
    """
    Simulates genuine human key dwell time:
    Sends KeyDown -> sleeps dwell_s seconds -> sends KeyUp.
    Defeats anti-cheat systems that measure 0ms virtual key hold durations.
    """
    ok_down = send_unicode_down(code_unit)
    if dwell_s > 0.001:
        time.sleep(dwell_s)
    ok_up = send_unicode_up(code_unit)
    return ok_down and ok_up


_pynput_ctrl = None

def _get_pynput_controller():
    global _pynput_ctrl
    if _pynput_ctrl is None:
        try:
            from pynput.keyboard import Controller
            _pynput_ctrl = Controller()
        except Exception:
            pass
    return _pynput_ctrl


def send_virtual_key_with_dwell(vk_code: int, dwell_s: float = 0.05) -> bool:
    """
    Simulates genuine human virtual key dwell time (Enter, Tab, Backspace).
    """
    ok_down = send_virtual_key_down(vk_code)
    if dwell_s > 0.001:
        time.sleep(dwell_s)
    ok_up = send_virtual_key_up(vk_code)
    ok = ok_down and ok_up
    if not ok:
        ctrl = _get_pynput_controller()
        if ctrl:
            try:
                from pynput.keyboard import Key
                vk_map = {
                    VK_RETURN: Key.enter,
                    VK_TAB: Key.tab,
                    VK_BACK: Key.backspace,
                    VK_DELETE: Key.delete,
                    VK_UP: Key.up,
                    VK_DOWN: Key.down,
                    VK_LEFT: Key.left,
                    VK_RIGHT: Key.right,
                    VK_ESCAPE: Key.esc,
                }
                k = vk_map.get(vk_code)
                if k:
                    ctrl.press(k)
                    if dwell_s > 0.001:
                        time.sleep(dwell_s)
                    ctrl.release(k)
                    return True
            except Exception:
                pass
    return ok


def type_character_native(char: str) -> bool:
    """
    Types a single character with full Unicode and surrogate pair support.
    Handles BMP characters and astral plane (e.g. emojis) characters safely.
    """
    if char == "\n":
        return send_virtual_key(VK_RETURN)
    elif char == "\t":
        return send_virtual_key(VK_TAB)
    elif char == "\r":
        return True
    
    codepoint = ord(char)
    if codepoint <= 0xFFFF:
        return send_unicode_codepoint(codepoint)
    else:
        utf16_bytes = char.encode("utf-16le")
        high_surrogate = int.from_bytes(utf16_bytes[0:2], "little")
        low_surrogate = int.from_bytes(utf16_bytes[2:4], "little")
        
        ok_high = send_unicode_codepoint(high_surrogate)
        ok_low = send_unicode_codepoint(low_surrogate)
        ok = ok_high and ok_low

    if not ok:
        ctrl = _get_pynput_controller()
        if ctrl:
            try:
                ctrl.type(char)
                return True
            except Exception:
                pass
    return ok


def type_character_biometric(char: str, dwell_s: float = 0.05) -> bool:
    """
    Types a single character with authentic human dwell time simulation.
    Key remain pressed for dwell_s before being released.
    """
    if char == "\n":
        return send_virtual_key_with_dwell(VK_RETURN, dwell_s)
    elif char == "\t":
        return send_virtual_key_with_dwell(VK_TAB, dwell_s)
    elif char == "\r":
        return True

    codepoint = ord(char)
    if codepoint <= 0xFFFF:
        ok = send_unicode_with_dwell(codepoint, dwell_s)
    else:
        utf16_bytes = char.encode("utf-16le")
        high_surrogate = int.from_bytes(utf16_bytes[0:2], "little")
        low_surrogate = int.from_bytes(utf16_bytes[2:4], "little")
        
        ok_high = send_unicode_with_dwell(high_surrogate, dwell_s / 2.0)
        ok_low = send_unicode_with_dwell(low_surrogate, dwell_s / 2.0)
        ok = ok_high and ok_low

    if not ok:
        ctrl = _get_pynput_controller()
        if ctrl:
            try:
                ctrl.type(char)
                return True
            except Exception:
                pass
    return ok


def make_window_ghost(hwnd: int, alpha: int = 240) -> bool:
    """
    Applies Win32 extended window styles to make a window a Zero-Focus Ghost HUD:
    - WS_EX_NOACTIVATE: Windows NEVER transfers keyboard focus or activates it on click
    - WS_EX_TOPMOST: Floats above all full-screen windows (browser, IDE, proctor)
    - WS_EX_TOOLWINDOW: Hidden from Alt+Tab switcher and Windows Taskbar
    - WS_EX_LAYERED: Enables per-pixel / alpha blending (0-255)
    """
    try:
        parent = user32.GetParent(hwnd)
        root = user32.GetAncestor(hwnd, 2)  # GA_ROOT
        target_hwnd = root if root else (parent if parent else hwnd)

        ex_style = _GetWindowLongPtr(target_hwnd, GWL_EXSTYLE)
        ghost_style = ex_style | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_LAYERED
        _SetWindowLongPtr(target_hwnd, GWL_EXSTYLE, ghost_style)

        if alpha < 255:
            user32.SetLayeredWindowAttributes(target_hwnd, 0, alpha, LWA_ALPHA)

        user32.SetWindowPos(
            target_hwnd,
            HWND_TOPMOST,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        )
        return True
    except Exception as e:
        print(f"[TYPO Win32] make_window_ghost error: {e}")
        return False


# ==========================================
# Simulated Cursor Wandering & Selection Refactoring
# ==========================================


def get_cursor_pos() -> tuple[int, int]:
    """Retrieves physical cursor desktop coordinates (X, Y)."""
    pt = POINT()
    if user32.GetCursorPos(ctypes.byref(pt)):
        return (pt.x, pt.y)
    return (0, 0)


def set_cursor_pos(x: int, y: int) -> bool:
    """Sets physical cursor desktop coordinates (X, Y)."""
    return bool(user32.SetCursorPos(x, y))


def smooth_cursor_drift(dx: int, dy: int, duration_s: float = 0.25, steps: int = 12) -> bool:
    """
    Smoothly wanders mouse cursor by (dx, dy) with natural cubic easing.
    Simulates human eye/hand micro-drifting across code lines during pauses,
    defeating webcam gaze tracking and static mouse anomaly sensors in proctored OAs.
    """
    try:
        start_x, start_y = get_cursor_pos()
        sleep_interval = max(0.005, duration_s / max(1, steps))

        for i in range(1, steps + 1):
            t = i / steps
            ease = t * t * (3.0 - 2.0 * t)
            curr_x = int(start_x + dx * ease)
            curr_y = int(start_y + dy * ease)
            set_cursor_pos(curr_x, curr_y)
            time.sleep(sleep_interval)

        return True
    except Exception as e:
        print(f"[TYPO Win32] smooth_cursor_drift error: {e}")
        return False


def simulate_select_and_replace(back_count: int, replace_text: str, dwell_s: float = 0.04) -> bool:
    """
    Simulates authentic developer refactoring:
    1. Holds Shift and presses LeftArrow back_count times to highlight the token.
    2. Inspection hesitation pause (120ms - 220ms).
    3. Sends Backspace to clear selection.
    4. Small recovery pause (60ms - 110ms).
    5. Types the replacement / refactored token.
    """
    try:
        send_virtual_key_down(VK_SHIFT)
        time.sleep(0.02)
        for _ in range(back_count):
            send_virtual_key_with_dwell(VK_LEFT, dwell_s)
            time.sleep(0.015)
        send_virtual_key_up(VK_SHIFT)
        time.sleep(0.02)

        time.sleep(random.uniform(0.12, 0.22))

        send_virtual_key_with_dwell(VK_BACK, dwell_s)
        time.sleep(random.uniform(0.06, 0.11))

        for ch in replace_text:
            type_character_biometric(ch, dwell_s)
            time.sleep(0.035)

        return True
    except Exception as e:
        print(f"[TYPO Win32] simulate_select_and_replace error: {e}")
        return False


# ==========================================
# Dedicated Global Hotkey Manager (Alt + Z + T)
# ==========================================

class GlobalHotKeyManager:
    """
    Dedicated Global Hotkey Manager for Alt + Z + T and emergency abort via Esc.
    Uses a low-level keyboard listener to detect:
    1) Simultaneous chord: Alt, 'Z', and 'T' all held down.
    2) Sequential chord: Alt is held, and 'Z' then 'T' are pressed in succession.
    3) Escape key: Immediately triggers emergency abort.
    """
    def __init__(self, callback=None, abort_callback=None):
        self.callback = callback
        self.abort_callback = abort_callback
        self._listener: Optional[Listener] = None
        self._pressed_keys = set()
        self._triggered = False
        self._last_z_time = 0.0
        self._lock = threading.Lock()
        self.is_registered = False
        self.last_error = ""

    def _normalize_key(self, key):
        if key in (Key.alt, Key.alt_l, Key.alt_r, Key.alt_gr):
            return "ALT"
        if hasattr(key, "vk") and key.vk:
            if key.vk in (0x12, 0xA4, 0xA5):
                return "ALT"
            elif key.vk in (0x5A, ord('Z'), ord('z')):
                return "z"
            elif key.vk in (0x54, ord('T'), ord('t')):
                return "t"
        if hasattr(key, "char") and key.char:
            c = key.char.lower()
            if c in ("z", "t"):
                return c
        return None

    def _on_press(self, key):
        # 1. Emergency Abort Key Check (Esc)
        if key == Key.esc or (hasattr(key, "vk") and key.vk == 0x1B):
            if self.abort_callback:
                try:
                    self.abort_callback()
                except Exception as e:
                    print(f"[TYPO HotKey] Abort callback error: {e}")
            return

        k = self._normalize_key(key)
        if k:
            with self._lock:
                self._pressed_keys.add(k)
                now = time.time()

                if k == "z" and "ALT" in self._pressed_keys:
                    self._last_z_time = now

                simultaneous = {"ALT", "z", "t"}.issubset(self._pressed_keys)
                sequential = ("ALT" in self._pressed_keys) and (k == "t") and (now - self._last_z_time <= 1.5)

                if simultaneous or sequential:
                    if not self._triggered:
                        self._triggered = True
                        if self.callback:
                            try:
                                self.callback()
                            except Exception as e:
                                print(f"[TYPO HotKey] Callback error: {e}")

    def _on_release(self, key):
        k = self._normalize_key(key)
        if k:
            with self._lock:
                if k in self._pressed_keys:
                    self._pressed_keys.remove(k)
                if not {"ALT", "z", "t"}.issubset(self._pressed_keys):
                    self._triggered = False

    def start(self):
        """Starts the low-level keyboard listener for Alt + Z + T."""
        try:
            with self._lock:
                self._pressed_keys.clear()
                self._triggered = False
            self._listener = Listener(on_press=self._on_press, on_release=self._on_release)
            self._listener.daemon = True
            self._listener.start()
            self.is_registered = True
            self.last_error = ""
            return True
        except Exception as e:
            self.is_registered = False
            self.last_error = str(e)
            return False

    def stop(self):
        """Stops the keyboard listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self.is_registered = False
        with self._lock:
            self._pressed_keys.clear()
            self._triggered = False
