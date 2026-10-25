"""
TYPO — Precision Typing Automation
Desktop Application Entrypoint
"""

import sys
import os
import ctypes

# Ensure current directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def setup_windows_dpi():
    """Enables crisp Per-Monitor DPI awareness on Windows."""
    if sys.platform == "win32":
        try:
            # Windows 8.1+ Per-Monitor DPI aware
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                # Windows Vista+ System DPI aware
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

def main():
    if sys.platform != "win32":
        print("[ERROR] TYPO is engineered exclusively for Microsoft Windows.")
        sys.exit(1)

    setup_windows_dpi()

    from typo.ui import main as ui_main
    ui_main()

if __name__ == "__main__":
    main()
