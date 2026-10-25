"""
TYPO - Standalone Windows Executable Builder
Builds a single-file executable using PyInstaller.
Automatically discovers and includes CustomTkinter theme assets.
"""

import sys
import os
import subprocess
import shutil

def build_executable():
    if sys.platform != "win32":
        print("[ERROR] Build script must run on Windows.")
        sys.exit(1)

    print("==================================================")
    print("   TYPO - Building Standalone Windows Executable   ")
    print("==================================================")

    # 1. Verify PyInstaller is installed
    try:
        import PyInstaller
        print(f"[OK] PyInstaller found: version {PyInstaller.__version__}")
    except ImportError:
        print("[INFO] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Locate CustomTkinter package directory for assets
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    print(f"[OK] CustomTkinter assets located at: {ctk_path}")

    # 3. Clean old build artifacts
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"[INFO] Cleaning old '{folder}' directory...")
            shutil.rmtree(folder, ignore_errors=True)

    # 4. Construct PyInstaller command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",                # Onedir starts fast and reliably loads all DLLs
        "--windowed",              # No terminal window
        "--name", "TYPO",
        f"--add-data={ctk_path};customtkinter",
        "--clean",
        "main.py"
    ]

    print("[INFO] Running PyInstaller build command:")
    print(" ".join(cmd))
    print()

    result = subprocess.run(cmd)
    if result.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", "TYPO", "TYPO.exe"))
        print()
        print("==================================================")
        print("   BUILD SUCCESSFUL!                              ")
        print(f"   Executable: {exe_path}")
        print("==================================================")
    else:
        print()
        print("[ERROR] Build failed. Please review the output above.")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build_executable()
