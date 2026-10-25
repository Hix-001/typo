"""
Unit & Integration Tests for TYPO
Verifies:
- Smart Code Indentation Engine (zero spacebar indentation, auto-indent sync)
- Dedent detection and Backspace action compilation
- Timing model (WPM, Gaussian jitter, cadence modifiers)
- Clipboard analytics (Unicode, emojis, code detection)
- Global Hotkey Manager lifecycle and dynamic rebinding
"""

import unittest
from typo.typing_engine import TypingEngine, detect_indent_unit
from typo.clipboard import analyze_clipboard_content
from typo.win32_api import GlobalHotKeyManager, get_foreground_window_info, PRIMARY_HOTKEY_LABEL


class TestTypoEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TypingEngine()

    def test_indent_unit_detection(self):
        code_4 = ["def foo():", "    return 1"]
        self.assertEqual(detect_indent_unit(code_4), 4)

        code_2 = ["function foo() {", "  return 1;", "}"]
        self.assertEqual(detect_indent_unit(code_2), 2)

        code_tab = ["def foo():", "\treturn 1"]
        self.assertEqual(detect_indent_unit(code_tab), 1)

    def test_smart_auto_indent_no_spacebars(self):
        code = (
            "def solve(nums):\n"
            "    total = 0\n"
            "    for x in nums:\n"
            "        if x > 0:\n"
            "            total += x\n"
            "    return total"
        )
        self.engine.smart_auto_indent = True
        actions = self.engine.compile_typing_actions(code)

        # Ensure no CHAR action is a leading space for indentation
        # Every action is either ENTER, TAB, BACKSPACE, or characters in stripped content
        action_types = [a[0] for a in actions]
        self.assertIn("ENTER", action_types)
        self.assertIn("BACKSPACE", action_types) # Line 6 dedents!

        # Verify that total line starts do not type spaces for indentation
        # Lines 1, 2, 3, 4 match the editor's auto-indent, so diff=0
        # Line 6 dedents from level 3 to level 1 (needs 2 backspaces)
        backspace_count = sum(val for act, val in actions if act == "BACKSPACE")
        self.assertEqual(backspace_count, 2)

    def test_bracket_neutralizer_actions(self):
        cpp_code = (
            "int solve() {\n"
            "    return 42;\n"
            "}"
        )
        self.engine.smart_auto_indent = True
        self.engine.neutralize_auto_closing_brackets = True
        actions = self.engine.compile_typing_actions(cpp_code)
        
        # Verify that DELETE_AUTO_CLOSE is scheduled after line 1's opening brace
        action_names = [a[0] for a in actions]
        self.assertIn("DELETE_AUTO_CLOSE", action_names)

    def test_closing_bracket_dedent_sync(self):
        cpp_code = (
            "void foo() {\n"
            "    int x = 1;\n"
            "}"
        )
        self.engine.smart_auto_indent = True
        self.engine.code_editor_mode = True
        actions = self.engine.compile_typing_actions(cpp_code)

        # For line 3 ("}"), diff is -1 from level 1 to level 0.
        # Since line 3 starts with '}', Monaco auto-dedents by 1 upon typing '}'.
        # Needed backspaces should be max(0, abs(-1) - 1) == 0.
        backspace_actions = [val for act, val in actions if act == "BACKSPACE"]
        self.assertEqual(sum(backspace_actions), 0)

    def test_wpm_timing_calculation(self):
        self.engine.wpm = 80.0
        self.engine.variance = 0.0  # Zero jitter to check base math
        
        # Base delay at 80 WPM: 12.0 / 80 = 0.150 seconds
        delay_a = self.engine.calculate_character_delay("a", "")
        self.assertAlmostEqual(delay_a, 0.150, delta=0.005)

        # 60 WPM: 12.0 / 60 = 0.200 seconds
        self.engine.wpm = 60.0
        delay_60 = self.engine.calculate_character_delay("a", "")
        self.assertAlmostEqual(delay_60, 0.200, delta=0.005)

        # 100 WPM: 12.0 / 100 = 0.120 seconds
        self.engine.wpm = 100.0
        delay_100 = self.engine.calculate_character_delay("a", "")
        self.assertAlmostEqual(delay_100, 0.120, delta=0.005)

    def test_cadence_modifiers(self):
        self.engine.wpm = 80.0
        self.engine.variance = 0.0
        base = 0.150

        # Punctuation pause should be significantly higher than standard char
        delay_period = self.engine.calculate_character_delay(".", "a")
        self.assertGreater(delay_period, base * 1.5)

        # Newline pause should be higher than standard char
        delay_newline = self.engine.calculate_character_delay("\n", "x")
        self.assertGreater(delay_newline, base * 1.8)

    def test_jitter_bounds(self):
        self.engine.wpm = 80.0
        self.engine.variance = 0.40  # 40% jitter
        
        delays = [self.engine.calculate_character_delay("x", "y") for _ in range(100)]
        for d in delays:
            self.assertGreaterEqual(d, 0.015)
            self.assertLessEqual(d, 0.150 * 2.8)


class TestClipboardAnalytics(unittest.TestCase):
    def test_empty_clipboard(self):
        res = analyze_clipboard_content("")
        self.assertEqual(res["char_count"], 0)
        self.assertEqual(res["word_count"], 0)

    def test_code_detection(self):
        code = "def two_sum(nums, target):\n    return [0, 1]"
        res = analyze_clipboard_content(code)
        self.assertTrue(res["has_code"])
        self.assertEqual(res["line_count"], 2)

    def test_unicode_and_emojis(self):
        text = "Hello World! 🚀 Привет π ≤ ∞"
        res = analyze_clipboard_content(text)
        self.assertTrue(res["has_unicode"])


class TestWin32API(unittest.TestCase):
    def test_foreground_window_structure(self):
        info = get_foreground_window_info()
        self.assertIn("hwnd", info)
        self.assertIn("title", info)
        self.assertIn("pid", info)
        self.assertIn("process_name", info)

    def test_primary_hotkey_label(self):
        from typo.win32_api import PRIMARY_HOTKEY_LABEL
        self.assertEqual(PRIMARY_HOTKEY_LABEL, "Alt + Z + T")

    def test_hotkey_manager_lifecycle(self):
        mgr = GlobalHotKeyManager()
        res = mgr.start()
        self.assertTrue(res)
        self.assertTrue(mgr.is_registered)
        mgr.stop()
        self.assertFalse(mgr.is_registered)

    def test_key_normalization(self):
        from pynput.keyboard import Key, KeyCode
        mgr = GlobalHotKeyManager()
        self.assertEqual(mgr._normalize_key(Key.alt), "ALT")
        self.assertEqual(mgr._normalize_key(Key.alt_l), "ALT")
        self.assertEqual(mgr._normalize_key(Key.alt_r), "ALT")
        self.assertEqual(mgr._normalize_key(Key.alt_gr), "ALT")
        self.assertEqual(mgr._normalize_key(KeyCode.from_vk(0x12)), "ALT")
        self.assertEqual(mgr._normalize_key(KeyCode.from_char('z')), "z")
        self.assertEqual(mgr._normalize_key(KeyCode.from_char('Z')), "z")
        self.assertEqual(mgr._normalize_key(KeyCode.from_char('t')), "t")
        self.assertEqual(mgr._normalize_key(KeyCode.from_char('T')), "t")


class TestBiometricsAndGhostHUD(unittest.TestCase):
    def setUp(self):
        self.engine = TypingEngine()

    def test_biometric_dwell_time_bounds(self):
        # Human dwell times should strictly fall within realistic 25ms - 140ms
        for char in ("a", "E", "{", "}", " ", "\n", "5"):
            dwell = self.engine.calculate_dwell_time(char)
            self.assertGreaterEqual(dwell, 0.025)
            self.assertLessEqual(dwell, 0.140)

        # Shifted / complex symbols should have higher average dwell time than frequent lowercase
        self.engine.dwell_variance = 0.0  # Zero variance for determinism
        dwell_e = self.engine.calculate_dwell_time("e")
        dwell_bracket = self.engine.calculate_dwell_time("{")
        self.assertGreater(dwell_bracket, dwell_e)

    def test_mistake_injection_qwerty_neighbors(self):
        from typo.typing_engine import QWERTY_NEIGHBORS
        # Ensure all standard alphabetic keys have mapped neighbors
        for char in "abcdefghijklmnopqrstuvwxyz0123456789":
            self.assertIn(char, QWERTY_NEIGHBORS)
            self.assertGreater(len(QWERTY_NEIGHBORS[char]), 0)

    def test_ghost_hud_module_methods(self):
        from typo.ghost_hud import GhostHUD, HUD_BG
        # Instantiate GhostHUD headless/hidden
        hud = GhostHUD()
        hud.withdraw()
        try:
            # Test state transitions
            hud.update_state("TYPING", {"target": {"title": "Test Window"}})
            self.assertEqual(hud.lbl_state_pill.cget("text"), "⌨ TYPING")
            hud.update_countdown(2.5)
            self.assertEqual(hud.lbl_state_pill.cget("text"), "⏳ 2.5s")
            hud.update_progress(50.0, 50, 100, 5.0, 5.0, "x")
            self.assertEqual(hud.lbl_stats.cget("text"), "50/100 (50%)")
        finally:
            hud.destroy()

    def test_calculate_line_complexity(self):
        from typo.typing_engine import calculate_line_complexity
        # Low complexity boilerplate lines
        c_import = calculate_line_complexity("import math")
        c_include = calculate_line_complexity("#include <iostream>")
        c_close = calculate_line_complexity("}")
        self.assertLess(c_import, 0.7)
        self.assertLess(c_include, 0.7)
        self.assertLess(c_close, 0.7)

        # High complexity algorithmic lines
        c_dp = calculate_line_complexity("        dp[i][j] = min(dp[i-1][j], dp[i][j - coins[k]] + 1)")
        c_bitwise = calculate_line_complexity("        mask = (mask ^ (1 << bit)) | (curr & next_state)")
        self.assertGreater(c_dp, 1.4)
        self.assertGreater(c_bitwise, 1.4)

    def test_complexity_throttler_delay_scaling(self):
        self.engine.wpm = 80.0
        self.engine.variance = 0.0
        self.engine.complexity_throttler_enabled = True

        delay_simple = self.engine.calculate_character_delay("x", "y", line_complexity=0.5)
        delay_normal = self.engine.calculate_character_delay("x", "y", line_complexity=1.0)
        delay_complex = self.engine.calculate_character_delay("x", "y", line_complexity=2.2)

        self.assertLess(delay_simple, delay_normal)
        self.assertGreater(delay_complex, delay_normal)

    def test_incremental_code_construction(self):
        code = (
            "def maxSubArray(nums):\n"
            "    total = 0\n"
            "    best = nums[0]\n"
            "    for x in nums:\n"
            "        total = max(x, total + x)\n"
            "        best = max(best, total)\n"
            "    return best"
        )
        self.engine.incremental_construction_mode = True
        actions = self.engine.compile_typing_actions(code)

        action_names = [a[0] for a in actions]
        self.assertIn("NAV_UP", action_names)
        self.assertIn("NAV_DOWN", action_names)

    def test_cursor_wandering_primitives(self):
        from typo.win32_api import get_cursor_pos
        pos = get_cursor_pos()
        self.assertIsInstance(pos, tuple)
        self.assertEqual(len(pos), 2)




if __name__ == "__main__":
    unittest.main()


