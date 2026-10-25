"""
TYPO - Human-Speed Typing Engine & Automation Orchestrator
Features:
- Configurable WPM (30 - 180, default 80) and Gaussian timing variance (jitter)
- Smart Code Indentation Engine:
  * Detects code indentation schemes (4-space, 2-space, tabs)
  * Syncs with editor's auto-indentation upon Enter (Zero spacebars used for indentation!)
  * Uses VK_TAB for incremental indentation and VK_BACK for dedenting
  * Never types spacebar spacebar spacebar for code indentation
- Natural human cadence: punctuation pauses, newline thinking time, digraph bursts
- Safety countdown with live cancellation
- Target window binding with auto-pause on focus loss (prevents cross-window leaks)
- Emergency abort via physical Escape key detection (GetAsyncKeyState)
- Telemetry: characters/actions typed, progress percentage, elapsed & remaining time
"""

import time
import random
import threading
from typing import Callable, Optional

from typo.win32_api import (
    type_character_native,
    type_character_biometric,
    send_virtual_key,
    send_virtual_key_with_dwell,
    get_foreground_window_info,
    is_escape_pressed,
    read_clipboard_unicode,
    smooth_cursor_drift,
    simulate_select_and_replace,
    VK_TAB,
    VK_BACK,
    VK_RETURN,
    VK_DELETE,
    VK_UP,
    VK_DOWN,
    VK_LEFT,
    VK_RIGHT,
    VK_HOME,
    VK_END
)

# QWERTY Proximity Map for Autonomous Mistake Injection
QWERTY_NEIGHBORS: dict[str, list[str]] = {
    'a': ['q', 'w', 's', 'z'],
    'b': ['v', 'g', 'h', 'n'],
    'c': ['x', 'd', 'f', 'v'],
    'd': ['s', 'e', 'r', 'f', 'c', 'x'],
    'e': ['w', 's', 'd', 'r', '3', '4'],
    'f': ['d', 'r', 't', 'g', 'v', 'c'],
    'g': ['f', 't', 'y', 'h', 'b', 'v'],
    'h': ['g', 'y', 'u', 'j', 'n', 'b'],
    'i': ['u', 'j', 'k', 'o', '8', '9'],
    'j': ['h', 'u', 'i', 'k', 'm', 'n'],
    'k': ['j', 'i', 'o', 'l', 'm'],
    'l': ['k', 'o', 'p', ';'],
    'm': ['n', 'j', 'k'],
    'n': ['b', 'h', 'j', 'm'],
    'o': ['i', 'k', 'l', 'p', '9', '0'],
    'p': ['o', 'l', '[', '-'],
    'q': ['1', '2', 'w', 'a'],
    'r': ['e', 'd', 'f', 't', '4', '5'],
    's': ['a', 'w', 'e', 'd', 'x', 'z'],
    't': ['r', 'f', 'g', 'y', '5', '6'],
    'u': ['y', 'h', 'j', 'i', '7', '8'],
    'v': ['c', 'f', 'g', 'b'],
    'w': ['q', 'a', 's', 'e', '2', '3'],
    'x': ['z', 's', 'd', 'c'],
    'y': ['t', 'g', 'h', 'u', '6', '7'],
    'z': ['a', 's', 'x'],
    '0': ['9', '-', 'o', 'p'],
    '1': ['2', 'q'],
    '2': ['1', '3', 'q', 'w'],
    '3': ['2', '4', 'w', 'e'],
    '4': ['3', '5', 'e', 'r'],
    '5': ['4', '6', 'r', 't'],
    '6': ['5', '7', 't', 'y'],
    '7': ['6', '8', 'y', 'u'],
    '8': ['7', '9', 'u', 'i'],
    '9': ['8', '0', 'i', 'o'],
}


# Refactor simulation pairs for authentic developer hesitation (Feature 18)
REFACTOR_CANDIDATES: dict[str, str] = {
    "ans": "res",
    "res": "ans",
    "total": "ans",
    "curr": "temp",
    "temp": "curr",
    "count": "cnt",
    "cnt": "count",
    "nums": "arr",
    "result": "ret",
    "diff": "delta",
    "val": "target",
}


def calculate_line_complexity(line: str) -> float:
    """
    Evaluates the algorithmic & cognitive complexity of a single line of code (Feature 17).
    Returns a complexity coefficient:
    - 0.5 - 0.7: Low complexity (boilerplate, imports, comments, simple declarations)
    - 0.8 - 1.2: Normal complexity (standard control flow, simple assignments)
    - 1.3 - 2.8: High complexity (nested DP, bitwise logic, ternary, multi-bracket arrays, recursion)
    """
    stripped = line.strip()
    if not stripped:
        return 0.5

    # Comments or boilerplate imports
    if stripped.startswith(("#", "//", "/*", "*", "import ", "from ", "#include", "package ", "using ")):
        return 0.55

    # Simple bracket or stub lines
    if stripped in ("}", "};", "]", ")", "):", "pass", "return 0;", "return 0", "return false;", "return true;"):
        return 0.50

    score = 1.0

    # Indentation level (deeper indent = deeper nested logic)
    leading_spaces = len(line) - len(line.lstrip(" "))
    indent_depth = leading_spaces // 4
    score += min(0.6, indent_depth * 0.15)

    # Algorithmic and DP token density
    algorithmic_tokens = (
        "dp[", "memo[", "dfs(", "bfs(", "solve(", "recurse(", "binary_search",
        "matrix[", "grid[", "curr", "prev", "next", "parent", "adj[", "heap",
        "priority_queue", "lower_bound", "upper_bound", "max(", "min(",
        "Math.max", "Math.min", "std::max", "std::min", "modulo", "MOD", "1e9"
    )
    for token in algorithmic_tokens:
        if token in stripped:
            score += 0.35

    # Bitwise and intricate operators
    bitwise_tokens = ("<<", ">>", "^", " & ", " | ", "~", "?", ":")
    for op in bitwise_tokens:
        if op in stripped:
            score += 0.25

    # Multiple bracket nesting (e.g. grid[r][c] or dp[i][j])
    bracket_pairs = stripped.count("[") + stripped.count("(")
    if bracket_pairs >= 4:
        score += 0.40
    elif bracket_pairs >= 2:
        score += 0.20

    # Ternary or dense conditional expressions
    if (" if " in stripped and " else " in stripped) or ("?" in stripped and ":" in stripped):
        score += 0.45

    # Cap complexity safely between 0.5 and 2.8
    return max(0.5, min(2.8, score))


class EngineState:
    IDLE = "IDLE"
    COUNTDOWN = "COUNTDOWN"
    TYPING = "TYPING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"


def detect_indent_unit(lines: list[str]) -> int:
    """Detects whether code uses 4-space, 2-space, or tab indentation."""
    for line in lines:
        if line.startswith("  ") and not line.startswith("    "):
            return 2
        elif line.startswith("\t"):
            return 1
    return 4  # Default to standard 4-space tabstop


class TypingEngine:
    def __init__(self):
        # Settings
        self.wpm: float = 80.0
        self.variance: float = 0.25         # Jitter standard deviation ratio
        self.safety_delay: float = 3.0       # Countdown before typing starts
        self.code_editor_mode: bool = True   # Smart auto-indent synchronization
        self.smart_auto_indent: bool = True  # Follow editor indent scheme without spacebars
        self.neutralize_auto_closing_brackets: bool = True  # Eliminates auto-closing bracket duplicates in LeetCode/VS Code
        self.auto_pause_on_focus_loss: bool = True
        self.burst_digraphs: bool = True

        # Biometric Keystroke Dynamics (Dwell time & flight time realism)
        self.biometric_dynamics_enabled: bool = True
        self.base_dwell_ms: float = 55.0     # Mean key hold duration in ms (human normal: 45-75ms)
        self.dwell_variance: float = 0.20

        # Autonomous Mistake Injection & Backspace Engine
        self.mistake_injection_enabled: bool = True
        self.mistake_rate: float = 0.015     # 1.5% typo probability on alphanumeric chars
        self.on_mistake_injected: Optional[Callable[[str, str], None]] = None

        # Feature 5: Simulated Cursor Wandering (Anti-Gaze & Mouse Motion Inactivity Bypass)
        self.cursor_wandering_enabled: bool = True
        self.last_cursor_drift_time: float = 0.0

        # Feature 15: Incremental Code Construction (Signature & Stub Outline -> Body Fill)
        self.incremental_construction_mode: bool = False

        # Feature 17: Complexity Cadence Throttler (Fast Boilerplate, Slower Algorithmic Logic)
        self.complexity_throttler_enabled: bool = True

        # Feature 18: Selection & Refactoring Simulation (Authentic Shift+Left Word Replacement)
        self.refactoring_simulation_enabled: bool = True
        self.refactoring_rate: float = 0.02
        self.on_refactoring_simulated: Optional[Callable[[str, str], None]] = None

        # Feature 19: Inhuman Mode (360 WPM / ~1800 CPM Ultra-Speed Stream)
        self.inhuman_mode: bool = False

        # State management
        self.state: str = EngineState.IDLE
        self._pause_event = threading.Event()
        self._pause_event.set()  # Set means NOT paused
        self._stop_event = threading.Event()

        # Telemetry & Target
        self.target_window: dict = {}
        self.total_chars: int = 0
        self.chars_typed: int = 0
        self.start_time: float = 0.0
        self.elapsed_time: float = 0.0
        self.raw_text: str = ""
        self.compiled_actions: list[tuple[str, any]] = []

        # Thread reference
        self._worker_thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_state_change: Optional[Callable[[str, dict], None]] = None
        self.on_progress: Optional[Callable[[float, int, int, float, float, str], None]] = None
        self.on_countdown: Optional[Callable[[float], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

    def _set_state(self, new_state: str, details: Optional[dict] = None):
        self.state = new_state
        if self.on_state_change:
            try:
                self.on_state_change(new_state, details or {})
            except Exception as e:
                print(f"[TYPO Engine] Callback state change error: {e}")

    def _trigger_cursor_wandering(self):
        """
        Feature 5: Simulated Cursor Wandering.
        Gently drifts mouse cursor by small natural offsets with cubic easing during pauses.
        Defeats webcam eye-tracking and static mouse anomaly sensors in proctored assessments.
        """
        if not self.cursor_wandering_enabled:
            return
        if getattr(self, "_wander_thread", None) and self._wander_thread.is_alive():
            return
        now = time.time()
        if now - self.last_cursor_drift_time < 2.0:
            return
        self.last_cursor_drift_time = now
        dx = random.randint(-24, 24)
        dy = random.randint(-14, 14)
        self._wander_thread = threading.Thread(
            target=smooth_cursor_drift,
            args=(dx, dy, random.uniform(0.18, 0.28), 10),
            daemon=True,
            name="TypoWanderThread"
        )
        self._wander_thread.start()

    def compile_incremental_actions(self, raw_text: str) -> Optional[list[tuple[str, any]]]:
        """
        Feature 15: Incremental Code Construction.
        Simulates authentic human development sequence:
        1. Types function header / class outline.
        2. Types return / closing stub.
        3. Navigates back up inside the function body (NAV_UP).
        4. Fills in the algorithmic logic line by line.
        5. Navigates down past closing to finish.
        """
        normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
        lines = [line for line in normalized.split("\n")]
        if len(lines) < 4:
            return None

        # Detect function signature on line 0
        first = lines[0].strip()
        is_fn = any(first.startswith(kw) for kw in (
            "def ", "int ", "void ", "bool ", "string ", "vector<", "public ", "private ",
            "class ", "function ", "const ", "auto ", "double ", "long "
        ))
        if not is_fn:
            return None

        # Detect tail / closing statement
        last = lines[-1].strip()
        has_closing = last in ("}", "};", "pass") or last.startswith("return ") or "return " in lines[-2]
        if not has_closing:
            return None

        header_line = lines[0]
        body_lines = lines[1:-1]
        tail_line = lines[-1]
        indent_unit = detect_indent_unit(lines)

        actions: list[tuple[str, any]] = []

        # 1. Type Header
        actions.append(("LINE_START", calculate_line_complexity(header_line)))
        for char in header_line:
            actions.append(("CHAR", char))
        actions.append(("ENTER", None))

        # 2. Type Tail Stub
        actions.append(("LINE_START", calculate_line_complexity(tail_line)))
        tail_stripped = tail_line.lstrip()
        tail_indent = round((len(tail_line) - len(tail_stripped)) / indent_unit)
        if tail_indent > 0:
            actions.append(("TAB", tail_indent))
        for char in tail_stripped:
            actions.append(("CHAR", char))

        # 3. Navigate back up into the body cavity
        actions.append(("NAV_UP", 1))
        actions.append(("ENTER", None))

        # 4. Fill in Body
        for b_idx, bline in enumerate(body_lines):
            if b_idx > 0:
                actions.append(("ENTER", None))
            bstripped = bline.lstrip()
            if not bstripped:
                continue
            b_indent = round((len(bline) - len(bstripped)) / indent_unit)
            if b_indent > 0:
                actions.append(("TAB", b_indent))
            actions.append(("LINE_START", calculate_line_complexity(bline)))
            for char in bstripped:
                actions.append(("CHAR", char))

        # 5. Navigate down to end of function
        actions.append(("NAV_DOWN", 1))
        return actions

    def compile_typing_actions(self, raw_text: str) -> list[tuple[str, any]]:
        """
        Decomposes raw code or text into semantic typing actions:
        - ('LINE_START', complexity): Prepares cognitive cadence for the line
        - ('ENTER', None): Creates newline with editor-settling delay
        - ('TAB', count): Sends VK_TAB for indentation (Zero spacebars!)
        - ('BACKSPACE', count): Sends VK_BACK to dedent to the required level
        - ('CHAR', char): Types actual code tokens/content with human cadence
        - ('REFACTOR_SIM', (draft, final)): Simulates Shift+Left selection and token refactoring
        - ('NAV_UP', count) / ('NAV_DOWN', count): Realistic multi-pass cursor navigation

        If incremental_construction_mode is active:
        Drafts the outer signature & stub first before filling the body!
        """
        if self.incremental_construction_mode:
            inc_actions = self.compile_incremental_actions(raw_text)
            if inc_actions is not None:
                return inc_actions

        # Normalize line breaks
        normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")
        indent_unit = detect_indent_unit(lines)

        actions = []
        editor_indent = 0
        prev_opened_block = False
        refactor_injected = False

        for i, line in enumerate(lines):
            if i > 0:
                actions.append(("ENTER", None))

            stripped = line.lstrip()
            if not stripped:
                # Blank line
                continue

            # Feature 17: Complexity Cadence Throttler - evaluate line complexity
            line_complexity = calculate_line_complexity(line)
            actions.append(("LINE_START", line_complexity))

            # Calculate indentation level of this line
            if line.startswith("\t"):
                indent_level = len(line) - len(line.lstrip("\t"))
            else:
                leading_spaces = len(line) - len(stripped)
                indent_level = round(leading_spaces / indent_unit)

            if self.smart_auto_indent:
                if i == 0:
                    # Line 0: If indented, send TABs (not spacebars)
                    if indent_level > 0:
                        actions.append(("TAB", indent_level))
                    editor_indent = indent_level
                else:
                    # Expected indent that Monaco / LeetCode / VS Code automatically applied on Enter
                    expected_indent = editor_indent + (1 if prev_opened_block else 0)
                    diff = indent_level - expected_indent

                    is_closing_bracket_line = stripped.startswith(("}", "]", ")"))

                    if diff > 0:
                        # Extra indent needed beyond editor's auto-indent -> use TAB
                        actions.append(("TAB", diff))
                    elif diff < 0:
                        # Line is dedented (e.g. return, else, closing bracket)
                        if is_closing_bracket_line and self.code_editor_mode:
                            # Monaco / VS Code / LeetCode auto-dedents by 1 indent unit when a closing bracket is typed!
                            # Subtract 1 from needed backspaces to prevent double-dedent:
                            needed_backspaces = max(0, abs(diff) - 1)
                            if needed_backspaces > 0:
                                actions.append(("BACKSPACE", needed_backspaces))
                        else:
                            actions.append(("BACKSPACE", abs(diff)))

                    editor_indent = indent_level
            else:
                # Non-auto-indent mode: send TAB for each indent level (never spacebars)
                if indent_level > 0:
                    actions.append(("TAB", indent_level))

            # Feature 18: Selection & Refactoring Simulation check
            # Look for candidate words to simulate human self-correction (max 1 per snippet)
            refactor_on_this_line = False
            if self.refactoring_simulation_enabled and not refactor_injected and i > 0:
                words = [w.strip("(),:;[]{}") for w in stripped.split()]
                for w in words:
                    if w in REFACTOR_CANDIDATES and random.random() < (self.refactoring_rate * 3.5):
                        draft_token = REFACTOR_CANDIDATES[w]
                        target_token = w
                        w_pos = stripped.find(w)
                        if w_pos != -1:
                            before = stripped[:w_pos]
                            after = stripped[w_pos + len(w):]
                            for char in before:
                                actions.append(("CHAR", char))
                            actions.append(("REFACTOR_SIM", (draft_token, target_token)))
                            for char in after:
                                actions.append(("CHAR", char))
                            refactor_injected = True
                            refactor_on_this_line = True
                            break

            if not refactor_on_this_line:
                # Append standard line content character-by-character
                for char in stripped:
                    actions.append(("CHAR", char))

            # Check if this line opened a block (ends with :, {, (, [)
            clean_end = stripped.rstrip()
            code_part = clean_end.split("//")[0].split("#")[0].rstrip()
            prev_opened_block = code_part.endswith((":", "{", "(", "["))

            # If line opened a multiline block with an auto-closing bracket, schedule bracket neutralizer
            if self.neutralize_auto_closing_brackets and code_part.endswith(("{", "(", "[")):
                actions.append(("DELETE_AUTO_CLOSE", None))

        return actions

    def calculate_character_delay(self, current_char: str, prev_char: str, line_complexity: float = 1.0) -> float:
        """
        Calculates humanized keystroke delay:
        1. Base delay from WPM: (60 / (WPM * 5))
        2. Gaussian jitter distribution
        3. Cadence modifiers:
           - Punctuation (. , ! ? ; :) pauses
           - Line break (\\n) cognitive pauses
           - Word boundaries (space)
           - Digraph muscle-memory bursts
        4. Feature 17: Complexity Cadence Throttler scaling
        """
        cpm = max(30.0, self.wpm) * 5.0
        base_delay = 60.0 / cpm

        std_dev = base_delay * self.variance
        delay = random.gauss(base_delay, std_dev)

        if current_char == "\n":
            delay += base_delay * (1.8 if self.code_editor_mode else 1.2)
        elif current_char in (".", "!", "?"):
            delay += base_delay * 1.3
        elif current_char in (",", ";", ":"):
            delay += base_delay * 0.7
        elif current_char == " ":
            delay += base_delay * 0.25
        elif self.burst_digraphs and prev_char and prev_char.isalnum() and current_char.isalnum():
            delay -= base_delay * 0.15

        # Feature 17: Scale delay based on line complexity
        if self.complexity_throttler_enabled and line_complexity != 1.0:
            delay *= (0.65 + line_complexity * 0.35)

        # Inhuman Mode allows ultra-low micro-delays down to 5ms for 360 WPM stream
        min_clamp = 0.005 if (self.inhuman_mode or self.wpm >= 300.0) else 0.015
        min_delay = max(min_clamp, base_delay * 0.35)
        max_delay = base_delay * 3.2
        return max(min_delay, min(delay, max_delay))

    def calculate_dwell_time(self, char: str) -> float:
        """
        Calculates authentic human key dwell time (duration physical key remains held down).
        Normal distribution centered around base_dwell_ms (default ~55ms).
        In Inhuman Mode (360 WPM), scales down to ~12ms to prevent queue congestion.
        """
        effective_dwell_ms = 12.0 if (self.inhuman_mode or self.wpm >= 300.0) else self.base_dwell_ms
        base = effective_dwell_ms / 1000.0
        std = base * self.dwell_variance
        dwell = random.gauss(base, std)

        if char.isupper() or char in ("{", "}", "[", "]", "(", ")", "<", ">", ":", '"', "?", "!", "@", "#", "$", "%", "^", "&", "*", "+", "_"):
            dwell += base * 0.40
        elif char in (" ", "\n", "\t"):
            dwell += base * 0.35
        elif char.lower() in ("e", "t", "a", "o", "i", "n", "s"):
            dwell -= base * 0.15

        min_clamp = 0.008 if (self.inhuman_mode or self.wpm >= 300.0) else 0.025
        max_clamp = 0.024 if (self.inhuman_mode or self.wpm >= 300.0) else 0.140
        return max(min_clamp, min(dwell, max_clamp))

    def _inject_mistake_and_correct(self, target_char: str) -> bool:
        """
        Simulates an authentic human typing mistake and spontaneous backspace correction:
        1. Selects an adjacent QWERTY key.
        2. Types the erroneous key with natural dwell time.
        3. Visual perception delay: human notices the mistake (120ms - 280ms).
        4. Presses Backspace with natural dwell time.
        5. Motor recovery delay: human prepares to type correct key (60ms - 130ms).
        Returns True if interrupted/stopped, False otherwise.
        """
        lower = target_char.lower()
        candidates = QWERTY_NEIGHBORS.get(lower, [])
        if not candidates:
            return False

        typo_char = random.choice(candidates)
        if target_char.isupper():
            typo_char = typo_char.upper()

        typo_dwell = self.calculate_dwell_time(typo_char) if self.biometric_dynamics_enabled else 0.04
        if self.biometric_dynamics_enabled:
            type_character_biometric(typo_char, typo_dwell)
        else:
            type_character_native(typo_char)

        if self.on_mistake_injected:
            try:
                self.on_mistake_injected(typo_char, target_char)
            except Exception:
                pass

        # Human visual perception latency: 120ms - 280ms
        perception_delay = random.uniform(0.12, 0.28)
        if self._sleep_interruptible(perception_delay):
            return True

        # Send Backspace with realistic dwell time
        backspace_dwell = random.uniform(0.045, 0.080)
        send_virtual_key_with_dwell(VK_BACK, backspace_dwell)

        # Motor recovery latency: 60ms - 130ms
        recovery_delay = random.uniform(0.06, 0.13)
        if self._sleep_interruptible(recovery_delay):
            return True

        return False

    def trigger_from_clipboard(self):

        """Reads text from clipboard and initiates the countdown & typing workflow."""
        if self.state in (EngineState.COUNTDOWN, EngineState.TYPING):
            return

        text, is_empty, err_msg = read_clipboard_unicode()
        if is_empty:
            if self.on_error:
                self.on_error(err_msg or "Clipboard is empty.")
            return

        self.start_typing_text(text)

    def start_typing_text(self, raw_text: str):
        """Starts the background typing worker with the given text."""
        if self.state in (EngineState.COUNTDOWN, EngineState.TYPING):
            return

        self.raw_text = raw_text
        self.compiled_actions = self.compile_typing_actions(raw_text)
        self.total_chars = len(self.compiled_actions)
        self.chars_typed = 0
        self.elapsed_time = 0.0

        self._stop_event.clear()
        self._pause_event.set()

        self._worker_thread = threading.Thread(
            target=self._run_typing_process,
            daemon=True,
            name="TypoWorkerThread"
        )
        self._worker_thread.start()

    def _sleep_interruptible(self, duration: float) -> bool:
        """
        Sleeps for duration seconds in short 15ms slices.
        Checks for Escape key and stop event continuously.
        Returns True if cancelled/stopped, False if sleep completed normally.
        """
        end_time = time.time() + duration
        while time.time() < end_time:
            if self._stop_event.is_set() or is_escape_pressed():
                self._stop_event.set()
                return True
            time.sleep(min(0.015, max(0.001, end_time - time.time())))
        return False

    def _run_typing_process(self):
        """Main background orchestrator."""
        # =====================================
        # Phase 1: Safety Countdown
        # =====================================
        self._set_state(EngineState.COUNTDOWN, {"delay": self.safety_delay})
        countdown_left = self.safety_delay
        interval = 0.1

        while countdown_left > 0:
            if self._stop_event.is_set() or is_escape_pressed():
                self._set_state(EngineState.STOPPED, {"reason": "Cancelled during countdown"})
                return

            if self.on_countdown:
                try:
                    self.on_countdown(round(countdown_left, 1))
                except Exception:
                    pass

            sleep_chunk = min(interval, countdown_left)
            if self._sleep_interruptible(sleep_chunk):
                self._set_state(EngineState.STOPPED, {"reason": "Cancelled during countdown"})
                return
            countdown_left -= sleep_chunk

        if self.on_countdown:
            try:
                self.on_countdown(0.0)
            except Exception:
                pass

        # =====================================
        # Phase 2: Lock Target Window
        # =====================================
        self.target_window = get_foreground_window_info()
        self.start_time = time.time()
        self._set_state(EngineState.TYPING, {"target": self.target_window})

        # =====================================
        # Phase 3: Typing Action Loop
        # =====================================
        prev_char = ""
        current_line_complexity = 1.0
        typing_start = time.time()
        accumulated_pause_duration = 0.0
        mistake_cooldown = 0

        for idx, (action_type, val) in enumerate(self.compiled_actions):
            # Check stop condition (ESC or UI Stop)
            if self._stop_event.is_set() or is_escape_pressed():
                self._set_state(EngineState.STOPPED, {
                    "reason": "Emergency stop triggered (ESC pressed or Stop button)",
                    "typed": self.chars_typed,
                    "total": self.total_chars
                })
                return

            # Check target window focus
            if self.auto_pause_on_focus_loss and self.target_window.get("hwnd"):
                current_window = get_foreground_window_info()
                if current_window.get("hwnd") != self.target_window.get("hwnd"):
                    self._pause_event.clear()
                    pause_start_ts = time.time()
                    self._set_state(EngineState.PAUSED, {
                        "reason": f"Target lost focus. Current active: {current_window.get('title', 'Unknown')}",
                        "lost_to": current_window
                    })

                    while not self._pause_event.is_set():
                        if self._stop_event.is_set() or is_escape_pressed():
                            self._set_state(EngineState.STOPPED, {"reason": "Cancelled while paused"})
                            return
                        time.sleep(0.05)

                    accumulated_pause_duration += (time.time() - pause_start_ts)
                    self._set_state(EngineState.TYPING, {"target": self.target_window})

            # Check manual pause
            if not self._pause_event.is_set():
                pause_start_ts = time.time()
                self._set_state(EngineState.PAUSED, {"reason": "Paused by user"})
                while not self._pause_event.is_set():
                    if self._stop_event.is_set() or is_escape_pressed():
                        self._set_state(EngineState.STOPPED, {"reason": "Cancelled while paused"})
                        return
                    time.sleep(0.05)
                accumulated_pause_duration += (time.time() - pause_start_ts)
                self._set_state(EngineState.TYPING, {"target": self.target_window})

            # Execute semantic typing action
            display_char = ""
            base_char_delay = 12.0 / max(30.0, self.wpm)

            if action_type == "LINE_START":
                current_line_complexity = float(val)
                # Feature 17 & 5: If line is complex, pause contemplatively and gently drift cursor
                if self.complexity_throttler_enabled and current_line_complexity > 1.35:
                    cog_pause = random.uniform(0.25, 0.65) * (current_line_complexity - 0.9)
                    if self._sleep_interruptible(cog_pause):
                        self._set_state(EngineState.STOPPED, {"reason": "Emergency stop during cognitive pause"})
                        return
                    self._trigger_cursor_wandering()
                continue

            elif action_type == "ENTER":
                # Send Enter with biometric dwell time
                dwell = self.calculate_dwell_time("\n") if self.biometric_dynamics_enabled else 0.04
                send_virtual_key_with_dwell(VK_RETURN, dwell)
                display_char = "↵"
                # Feature 5: Drift cursor during newline pause
                self._trigger_cursor_wandering()
                # Extra pause after Enter for editor auto-formatting to settle
                pause_len = base_char_delay * (1.8 if self.code_editor_mode else 1.2)
                if self._sleep_interruptible(pause_len):
                    self._set_state(EngineState.STOPPED, {"reason": "Emergency stop during typing"})
                    return
                prev_char = "\n"

            elif action_type == "NAV_UP":
                # Feature 15: Incremental Code Construction - navigate back up into function body
                count = val
                dwell = self.calculate_dwell_time(" ") if self.biometric_dynamics_enabled else 0.035
                for _ in range(count):
                    send_virtual_key_with_dwell(VK_UP, dwell)
                    time.sleep(0.04)
                display_char = "↑"
                if self._sleep_interruptible(base_char_delay * 0.5):
                    self._set_state(EngineState.STOPPED, {"reason": "Emergency stop during navigation"})
                    return

            elif action_type == "NAV_DOWN":
                # Feature 15: Incremental Code Construction - navigate down past closing stub
                count = val
                dwell = self.calculate_dwell_time(" ") if self.biometric_dynamics_enabled else 0.035
                for _ in range(count):
                    send_virtual_key_with_dwell(VK_DOWN, dwell)
                    time.sleep(0.04)
                display_char = "↓"
                if self._sleep_interruptible(base_char_delay * 0.5):
                    self._set_state(EngineState.STOPPED, {"reason": "Emergency stop during navigation"})
                    return

            elif action_type == "REFACTOR_SIM":
                # Feature 18: Selection & Refactoring Simulation
                draft_token, target_token = val
                dwell = self.calculate_dwell_time("a") if self.biometric_dynamics_enabled else 0.04
                for ch in draft_token:
                    if self.biometric_dynamics_enabled:
                        type_character_biometric(ch, dwell)
                    else:
                        type_character_native(ch)
                    time.sleep(0.035)

                if self._sleep_interruptible(random.uniform(0.18, 0.32)):
                    self._set_state(EngineState.STOPPED, {"reason": "Emergency stop during refactor hesitation"})
                    return

                simulate_select_and_replace(len(draft_token), target_token, dwell)
                display_char = "✎"
                if self.on_refactoring_simulated:
                    try:
                        self.on_refactoring_simulated(draft_token, target_token)
                    except Exception:
                        pass
                prev_char = target_token[-1] if target_token else ""
                if self._sleep_interruptible(base_char_delay * 0.6):
                    self._set_state(EngineState.STOPPED, {"reason": "Emergency stop during refactoring"})
                    return

            elif action_type == "TAB":
                # Send Tab keypresses (indents by tab stop, NEVER spacebars!)
                count = val
                dwell = self.calculate_dwell_time("\t") if self.biometric_dynamics_enabled else 0.04
                for _ in range(count):
                    send_virtual_key_with_dwell(VK_TAB, dwell)
                    time.sleep(0.035)
                display_char = "⇥"
                if self._sleep_interruptible(base_char_delay * 0.5):
                    self._set_state(EngineState.STOPPED, {"reason": "Emergency stop during typing"})
                    return

            elif action_type == "BACKSPACE":
                # Send Backspace to dedent
                count = val
                for _ in range(count):
                    send_virtual_key_with_dwell(VK_BACK, 0.045)
                    time.sleep(0.035)
                display_char = "⌫"
                if self._sleep_interruptible(base_char_delay * 0.4):
                    self._set_state(EngineState.STOPPED, {"reason": "Emergency stop during typing"})
                    return

            elif action_type == "DELETE_AUTO_CLOSE":
                # Bracket Neutralizer: deletes editor's auto-inserted closing bracket before newline
                if self.neutralize_auto_closing_brackets and self.code_editor_mode:
                    time.sleep(0.025)
                    send_virtual_key_with_dwell(VK_DELETE, 0.035)
                    time.sleep(0.015)
                display_char = "⌦"

            elif action_type == "CHAR":
                char = val
                display_char = char
                delay = self.calculate_character_delay(char, prev_char, current_line_complexity)
                if self._sleep_interruptible(delay):
                    self._set_state(EngineState.STOPPED, {"reason": "Emergency stop during typing"})
                    return

                # Autonomous Mistake Injection Check
                if (
                    self.mistake_injection_enabled
                    and mistake_cooldown <= 0
                    and char.isalnum()
                    and random.random() < self.mistake_rate
                ):
                    if self._inject_mistake_and_correct(char):
                        self._set_state(EngineState.STOPPED, {"reason": "Emergency stop during typing mistake"})
                        return
                    mistake_cooldown = 14  # Cooldown of at least 14 chars before next mistake

                if mistake_cooldown > 0:
                    mistake_cooldown -= 1

                # Biometric Dwell Time Typing
                dwell_s = self.calculate_dwell_time(char) if self.biometric_dynamics_enabled else 0.0
                if self.biometric_dynamics_enabled:
                    type_character_biometric(char, dwell_s)
                else:
                    type_character_native(char)
                prev_char = char


            self.chars_typed = idx + 1

            # Telemetry update
            now = time.time()
            effective_elapsed = max(0.01, (now - typing_start) - accumulated_pause_duration)
            chars_left = self.total_chars - self.chars_typed
            chars_per_sec = self.chars_typed / effective_elapsed
            est_remaining_sec = (chars_left / chars_per_sec) if chars_per_sec > 0 else 0.0
            pct = (self.chars_typed / self.total_chars) * 100.0

            if self.on_progress:
                try:
                    self.on_progress(
                        pct,
                        self.chars_typed,
                        self.total_chars,
                        effective_elapsed,
                        est_remaining_sec,
                        display_char
                    )
                except Exception:
                    pass

        # Completed all actions!
        elapsed = max(0.01, (time.time() - typing_start) - accumulated_pause_duration)
        self._set_state(EngineState.COMPLETED, {
            "total_typed": self.chars_typed,
            "elapsed_sec": elapsed
        })
        self._release_memory()

    def pause(self):
        """Pauses typing."""
        if self.state == EngineState.TYPING:
            self._pause_event.clear()

    def resume(self):
        """Resumes paused typing."""
        if self.state == EngineState.PAUSED:
            self._pause_event.set()

    def toggle_pause(self):
        """Toggles between paused and typing."""
        if self.state == EngineState.TYPING:
            self.pause()
        elif self.state == EngineState.PAUSED:
            self.resume()

    def stop(self):
        """Stops typing immediately."""
        self._stop_event.set()
        self._pause_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.5)
        self._set_state(EngineState.STOPPED, {"reason": "Stopped by user"})
        self._release_memory()

    def _release_memory(self):
        """Releases compiled actions and raw text buffers to minimize memory footprint."""
        self.compiled_actions = []
        self.raw_text = ""
        try:
            import gc
            gc.collect()
        except Exception:
            pass
