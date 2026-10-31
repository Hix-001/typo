"""
TYPO - Clipboard Analytics & Helpers
Provides non-destructive Unicode clipboard inspection, character analytics,
code syntax detection, and preview formatting.
"""

import re
import ctypes
from ctypes import wintypes
from typo.win32_api import (
    read_clipboard_unicode,
    get_clipboard_sequence_number,
    user32,
    kernel32,
    CF_UNICODETEXT,
    GMEM_MOVEABLE
)

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
kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalFree.restype = wintypes.HGLOBAL


def get_current_clipboard() -> tuple[str, bool, str]:
    """
    Returns (raw_text, is_empty, error_message)
    Never alters or clears the user's clipboard.
    Uses Qt QClipboard if available for instantaneous retrieval without
    Windows clipboard handle locking contention, with fallback to Win32 API.
    """
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            cb = app.clipboard()
            text = cb.text()
            if text:
                return (text, False, "")
    except Exception:
        pass
    return read_clipboard_unicode()


def analyze_clipboard_content(text: str) -> dict:
    """
    Produces real-time telemetry and character analysis for the clipboard text.
    Optimized for minimal heap allocations and zero memory spikes even on multi-MB buffers.
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
    
    # Zero-allocation line counting via C-level string count
    lines = text.count("\n")
    if not text.endswith("\n") or lines == 0:
        lines += 1
    
    # Vectorized C-speed ASCII check (allocates 0 bytes)
    has_unicode = not text.isascii()
    
    # Efficient word counting: split directly for moderate text, sample for huge files
    if char_count <= 25_000:
        words = len(text.split())
    else:
        sample_words = len(text[:25_000].split())
        words = max(1, int((sample_words / 25_000) * char_count))
    
    # Code syntax heuristic inspection on first 12,000 characters
    scan_chunk = text[:12_000]
    code_indicators = (
        "def ", "class ", "function ", "const ", "let ", "var ",
        "import ", "return ", "{", "}", ";", "=>", "print("
    )
    has_code = any(ind in scan_chunk for ind in code_indicators) or "\t" in scan_chunk or "    " in scan_chunk
    
    # Generate clean preview without holding extra string copies
    if char_count > 600:
        preview = f"{text[:600]}\n\n... [Truncated: {char_count - 600} more characters] ..."
    else:
        preview = text
        
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
    Properly frees GlobalAlloc memory if lock or SetClipboardData fails.
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
            kernel32.GlobalFree(h_glb)
            return False
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(h_glb)
        res = user32.SetClipboardData(CF_UNICODETEXT, h_glb)
        if not res:
            kernel32.GlobalFree(h_glb)
            return False
        return True
    finally:
        user32.CloseClipboard()
