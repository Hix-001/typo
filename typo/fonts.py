"""
TYPO® — Nothing OS Typography Engine
Dynamically discovers and registers Nothing OS fonts into the Windows GDI font table:
- Ndot 55 / Ndot 57: Iconic Nothing OS Dot-Matrix glyphs for headings, displays & numeric readouts
- NType 82 / NType 82 Headline: Clean geometric modern sans-serif
- NType 82 Mono: Technical monospace notation for code, chips, and hardware specs
"""

import os
import sys
import ctypes

_fonts_registered = False

FONTS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")

# Fallback fonts if system doesn't register custom OTFs
DEFAULT_DOT = "Consolas"
DEFAULT_BODY = "Segoe UI"
DEFAULT_MONO = "Consolas"

# Dynamic Nothing OS Font Tokens
FONT_DOT = "Ndot 55"
FONT_DOT_BOLD = "Ndot 57"
FONT_HEADLINE = "NType 82 Headline"
FONT_BODY = "NType 82"
FONT_MONO = "NType 82 Mono"


def register_fonts() -> bool:
    """
    Registers Nothing OS OTF/TTF fonts with Windows GDI using AddFontResourceExW.
    FR_PRIVATE (0x10) ensures fonts are accessible to the process without system installation.
    """
    global _fonts_registered
    if _fonts_registered:
        return True

    if sys.platform != "win32":
        _fonts_registered = True
        return False

    FR_PRIVATE = 0x10
    success_count = 0

    if os.path.isdir(FONTS_DIR):
        for fname in os.listdir(FONTS_DIR):
            if fname.lower().endswith((".otf", ".ttf")):
                font_path = os.path.abspath(os.path.join(FONTS_DIR, fname))
                try:
                    res = ctypes.windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
                    if res > 0:
                        success_count += 1
                except Exception:
                    pass

    _fonts_registered = True
    return success_count > 0


# Automatically register on import
try:
    register_fonts()
except Exception:
    pass
