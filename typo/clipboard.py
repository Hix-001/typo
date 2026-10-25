"""
TYPO - Clipboard Analytics & Helpers
Provides non-destructive Unicode clipboard inspection, character analytics,
code syntax detection, and preview formatting.
"""

import re
import ctypes
from ctypes import wintypes
from typo.win32_api import read_clipboard_unicode, user32, kernel32, CF_UNICODETEXT, GMEM_MOVEABLE

# Ensure 64-bit compatible ctypes signatures for clipboard operations
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.EmptyClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL


def get_current_clipboard() -> tuple[str, bool, str]:
    """
    Returns (raw_text, is_empty, error_message)
    Never alters or clears the user's clipboard.
    """
    return read_clipboard_unicode()


def analyze_clipboard_content(text: str) -> dict:
    """
    Produces real-time telemetry and character analysis for the clipboard text.
    """
    if not text:
        return {
            "char_count": 0,
            "word_count": 0,
            "line_count": 0,
            "has_unicode": False,
            "has_code": False,
            "preview": "(Clipboard is empty)"
        }
    
    char_count = len(text)
    words = len(text.split())
    lines = len(text.splitlines()) or 1
    
    # Check for astral / emoji characters (> 0xFFFF) or non-ASCII
    has_unicode = any(ord(c) > 127 for c in text)
    
    # Detect code-like patterns
    code_indicators = ["def ", "class ", "function ", "const ", "let ", "var ", "import ", "return ", "{", "}", ";", "=>", "print("]
    has_code = any(ind in text for ind in code_indicators) or "\t" in text or "    " in text
    
    # Generate clean preview
    preview = text[:600]
    if len(text) > 600:
        preview += f"\n\n... [Truncated: {char_count - 600} more characters] ..."
        
    return {
        "char_count": char_count,
        "word_count": words,
        "line_count": lines,
        "has_unicode": has_unicode,
        "has_code": has_code,
        "preview": preview
    }


def set_test_clipboard_text(text: str) -> bool:
    """
    Convenience utility for testing: writes Unicode text to Windows clipboard.
    """
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        data = text.encode("utf-16le") + b"\x00\x00"
        h_glb = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h_glb:
            return False
        ptr = kernel32.GlobalLock(h_glb)
        if not ptr:
            return False
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(h_glb)
        user32.SetClipboardData(CF_UNICODETEXT, h_glb)
        return True
    finally:
        user32.CloseClipboard()
