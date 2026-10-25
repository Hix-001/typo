# ⌨️ TYPO® — Precision Typing Automation (Pegassi Chrome Noir Edition)

**TYPO®** is a high-performance, lightweight Windows automation utility engineered to simulate authentic, human-speed keyboard typing directly from your clipboard into any target input field (LeetCode code editors, Monaco/VS Code, Notepad, browser text boxes, contest forms, or terminals).

Features a **Pegassi Chrome Noir / Brutalist Electronic Music aesthetic** with gleaming 3D liquid chrome beveled typography, star glints, film-grain obsidian panels, and an animated audio equalizer status player pill.

Activated globally via **`Alt + Z + T`** and instant **`Esc`** emergency abort.

---

## 🚀 Key Highlights

- **Pegassi Chrome Noir Aesthetic**:
  - Arched 3D liquid chrome metallic typography with specular glints and a backlit portal doorway.
  - Deep pitch-black film-grain noir void (`#050507`) with specular platinum hairline borders (`#22222D`).
  - High-contrast grotesque sans & monospaced album metadata layout.
  - Floating brutalist player pill with real-time animated equalizer bars (`ılılılllı`).
- **Dedicated Global Trigger: `Alt + Z + T`**:
  - Bound exclusively to simultaneous press of the Alt key, `Z`, and `T` in any order.
  - Powered by low-level thread-safe key listener (`pynput.keyboard.Listener`) with seamless debouncing and case normalization.
  - Eliminates Windows OS shortcut collisions (like `Win + P` screen projection) and avoids code editor `Ctrl + Z` undo traps.
- **Smart Code Indentation & Bracket Neutralizer (Zero Extra Brackets & Spacebars)**:
  - Automatically identifies whether your code uses 4-space, 2-space, or tab indentation.
  - **Eliminates Duplicate Brackets**: Neutralizes editor auto-closing pairs before `Enter` so closing brackets never accumulate at the bottom of the file in LeetCode/VS Code.
  - **Electric Closing Bracket Dedent Sync**: Synchronizes with Monaco's `decreaseIndentPattern` so closing brackets (`}`, `]`, `)`) never double-dedent.
  - **Never types spacebar spacebar spacebar for code indentation**:
    - If the editor's auto-indent matches the required level: **Zero keystrokes are typed** (the caret is already in position).
    - If extra indentation is required: Sends **`VK_TAB`** keystrokes.
    - If the line dedents (e.g. `return`, `else:`, `}`, `break`): Sends **`VK_BACK`** (Backspace) to unindent to the required level.
- **Native Win32 Keystroke Injection**: Built on `user32.SendInput` with `KEYEVENTF_UNICODE` (0x0004). Completely bypasses keyboard layouts (QWERTY, AZERTY, etc.), Caps Lock inversion, and IME conflicts.
- **Full Unicode & Astral Plane Support**: Automatically handles UTF-16 surrogate pairs for emojis (`🚀`, `✨`), math symbols (`π`, `≤`, `∞`), and international alphabets.
- **Natural Human Cadence & Timing**:
  - Configurable speed: **60 to 140 WPM** (Default: **80 WPM** / 400 CPM).
  - Gaussian timing variance (**Jitter**): Realistic per-keystroke variance with bounded standard deviations.
  - Contextual pauses: Natural reading pauses after punctuation (`.`, `,`, `!`, `?`), line breaks (`\n`), and muscle-memory bursts for digraphs.
- **Window Focus Lock (Safety Shield)**:
  - Automatically identifies and locks onto the target application when the safety countdown expires.
  - If focus shifts away (e.g. accidental click or notification popup), typing **immediately pauses** to prevent accidental text leakage into other apps.
- **Zero-Telemetry & Privacy**: 100% local, runs entirely in memory, never modifies, logs, or transmits clipboard contents.

---

## 🖥️ User Interface Overview

```
+-------------------------------------------------------------------------------+
| TYPO® [01/CORE]     STUDIO • SEQUENCER • ABOUT      “TYPO” CORE ENGINE v2.0   |
|                                                     Trigger: Alt+Z+T | ©2026  |
+-------------------------------------------------------------------------------+
| [C]                                                                       [0] |
| [O]                ✦  ✦  ✦   T Y P O   ✦  ✦  ✦                            [1] |
| [R]                       [🚪 Backlit Portal]                                 |
| [E]                                                                           |
+-------------------------------------------------------------------------------+
| ● IDLE — Ready. Focus target field and press Alt + Z + T                      |
+-------------------------------------------------------------------------------+
| [============================= Progress (25%) ==============================] |
| PROGRESS: 140/560   CADENCE: 80 WPM   ELAPSED: 00:21   REMAINING: 01:03   CHAR:'{'|
+-------------------------------------------------------------------------------+
| CLIPBOARD BUFFER // 560 chars • 72 words • 24 lines • Code Detected           |
| class Solution { ...                                                          |
+-------------------------------------------------------------------------------+
| Speed: 80 WPM [====|====]   Jitter: 25% [===|====]   Delay: 3.0s [===|======] |
| Indentation: [ Smart Auto-Indent & Bracket Sync ▼ ]                           |
| [✓] Auto-pause on focus loss   [✓] Settle Pause   [✓] Bracket Neutralizer     |
+-------------------------------------------------------------------------------+
| [ ▶ ARM & TYPE (Alt+Z+T) ]       [ ⏸ PAUSE / RESUME ]     [ ⏹ STOP (Esc) ]  |
+-------------------------------------------------------------------------------+
| LEETCODE • MONACO • VS CODE               [ 📊 TYPO Engine • IDLE (Alt+Z+T) ] |
+-------------------------------------------------------------------------------+
```

---

## ⚡ Quick Start

### Prerequisites
- Windows 10 or Windows 11 (64-bit)
- Python 3.10+ installed ([python.org](https://www.python.org))

### Launch
Run the included one-click batch launcher:
```cmd
run.bat
```

Or run via command line:
```powershell
pip install -r requirements.txt
python main.py
```

---

## 🕹️ Keyboard Controls & Shortcuts

| Shortcut | Description | Mechanism & Safety |
| :--- | :--- | :--- |
| **`Alt + Z + T`** | **Arm & Type Trigger (Sole Shortcut)** | Thread-safe low-level hook listening exclusively for simultaneous press of `Alt`, `Z`, and `T` in any order. Bypasses conflicting Windows shell shortcuts and doesn't trigger Undo. |
| **`Esc`** | **Emergency Stop** | Instantly halts typing at any millisecond (checked in low-level hardware loop via Win32 `GetAsyncKeyState`). |

---

## 🛡️ Critical Windows Limitations & Solutions

### 1. The Code Editor Indentation & Bracket Trap (Solved)
- **The Problem**: In LeetCode, Monaco, VS Code, and Sublime:
  1. Pressing `Enter` automatically carries over the current line's indentation. Standard typing bots then type 4 or 8 spacebar characters on top of that, resulting in 8 or 16 spaces (exponential over-indentation).
  2. Typing an opening block brace `{` (or `(`, `[`) at the end of a line causes the editor to auto-close the pair (`{}`) and push the closing bracket down to a separate line upon pressing `Enter`. When the bot subsequently types its own closing brackets from the clipboard, the editor's auto-inserted brackets accumulate at the bottom of the code, creating multiple extra closing brackets (`}}}`).
  3. Typing a closing bracket (`}`, `]`, `)`) on a newly indented line triggers the editor's built-in auto-dedent (`decreaseIndentPattern`). Bots that send Backspace cause double-dedentation.
- **The Solution**: TYPO's **Smart Indentation & Bracket Neutralizer**:
  - **Zero Spacebars for Indentation**: Uses editor auto-indent + `VK_TAB` and `VK_BACK` only when needed.
  - **Bracket Auto-Close Neutralizer**: Deletes the paired bracket immediately before `Enter` so no orphan closing brackets are pushed down.
  - **Electric Dedent Sync**: Accounts for the editor's native auto-dedent when typing closing brackets, guaranteeing pixel-perfect alignment.
  - **1-to-1 Matching**: Every opening bracket matches exactly one closing bracket. Zero duplicates at the end of the code.

### 2. User Interface Privilege Isolation (UIPI) & Elevation
- **The Issue**: In Windows Vista through Windows 11, standard user processes are prohibited by UIPI from injecting synthetic input (`SendInput`) into elevated processes running as Administrator.
- **The Solution**: If you intend to type into an elevated application (such as an Administrator Command Prompt, PowerShell, or an admin-level editor), launch **TYPO as Administrator** (`Right-click run.bat -> Run as administrator`).

### 3. No Foreground Window
- If no window has focus (`GetForegroundWindow() == 0`), Windows rejects synthetic input with `ERROR_ACCESS_DENIED (5)`. TYPO enforces a configurable safety delay (default: 3 seconds) ensuring you can click or switch to the target field before keystrokes begin.

---

## 📊 Human Typing Speed Model

Human typists do not type with robotic, fixed delays. TYPO implements a realistic cognitive typing model:

$$\text{Base Delay} = \frac{60.0}{\text{WPM} \times 5.0} = \frac{12.0}{\text{WPM}}\text{ seconds}$$

- **Gaussian Variance**: Each keystroke's delay is drawn from a normal distribution $\mathcal{N}(\mu, \sigma^2)$ where $\sigma = \mu \times \text{variance}$.
- **Punctuation Thinking**: Sentence terminators (`.`, `!`, `?`) add $+1.3 \times \mu$.
- **Line Break Settle**: Newlines (`\n`) add $+1.8 \times \mu$ (simulating carriage return & line mental reset).
- **Digraph Bursts**: Consecutive alphanumeric characters in words are typed with small muscle-memory acceleration ($-0.15 \times \mu$).

---

## 📦 Building a Standalone Executable (.exe)

To bundle TYPO into a standalone executable that runs on any Windows machine without needing Python installed:

```powershell
python build_exe.py
```

The resulting standalone executable will be located in:
`dist\TYPO\TYPO.exe`

---

## 🧪 Testing

Execute the automated test suite:
```powershell
python -m unittest discover -s tests -v
```

All 14 test suites covering smart auto-indentation, bracket neutralizer, dedent synchronization, tab modes, WPM mathematics, cadence modifiers, jitter clamping, clipboard analytics, key normalization, and Alt + Z + T hotkey lifecycle pass with 100% test coverage.
