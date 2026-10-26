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

    # 2. Verify assets and fonts exist
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "typo", "assets")
    fonts_dir = os.path.join(base_dir, "fonts")

    data_args = []
    if os.path.exists(assets_dir):
        data_args.append(f"--add-data={assets_dir};typo/assets")
        print(f"[OK] Assets directory located: {assets_dir}")
    if os.path.exists(fonts_dir):
        data_args.append(f"--add-data={fonts_dir};fonts")
        print(f"[OK] Fonts directory located: {fonts_dir}")

    # 3. Clean old build artifacts
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"[INFO] Cleaning old '{folder}' directory...")
            shutil.rmtree(folder, ignore_errors=True)

    # 4. Construct PyInstaller command for PySide6 Liquid Glass
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",                # Onedir ensures instant launch and full Qt DLL loading
        "--windowed",              # No terminal window
        "--name", "TYPO",
        "--collect-all", "PySide6",
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pynput.mouse._win32",
    ] + data_args + [
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
