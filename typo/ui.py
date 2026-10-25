"""
TYPO — Studio Glass Edition
A standalone PySide6 desktop UI prototype.

Run:
    pip install PySide6
    python mainui.py

This file builds a warm amber, frosted-glass-inspired interface. It keeps its
background fully inside the app window so desktop content cannot bleed through.
"""
import sys
from PySide6.QtCore import Qt, QSize, QPointF
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QRadialGradient, QPainter, QPen,
    QBrush, QIcon, QPixmap, QPainterPath
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSlider, QTextEdit, QCheckBox,
    QProgressBar, QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect
)

APP_NAME = "TYPO — Studio Glass Edition"

SAMPLE_CODE = """#include <vector>
#include <string>
using namespace std;

class Solution {
public:
    int closedIsland(vector<vector<int>>& grid) {
        int rows = static_cast<int>(grid.size());
        if (rows == 0) return 0;
        int cols = static_cast<int>(grid[0].size());
        int islands = 0;

        // Explore connected components and count closed islands.
        for (int r = 0; r < rows; ++r) {
            for (int c = 0; c < cols; ++c) {
                if (grid[r][c] == 0) {
                    // Add your traversal here.
                }
            }
        }
        return islands;
    }
};"""


class AmbientBackground(QWidget):
    """Opaque custom-painted background with warm light blooms."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()

        base = QLinearGradient(0, 0, r.width(), r.height())
        base.setColorAt(0.0, QColor("#17100e"))
        base.setColorAt(0.42, QColor("#29170f"))
        base.setColorAt(0.75, QColor("#1c100d"))
        base.setColorAt(1.0, QColor("#100c0b"))
        p.fillRect(r, base)

        # Soft, blurred-looking in-app illumination; never reveals desktop pixels.
        blooms = [
            (QPointF(r.width() * .35, r.height() * .10), r.width() * .40, QColor(255, 117, 35, 85)),
            (QPointF(r.width() * .76, r.height() * .43), r.width() * .35, QColor(255, 164, 66, 48)),
            (QPointF(r.width() * .18, r.height() * .78), r.width() * .33, QColor(255, 94, 26, 48)),
        ]
        for center, radius, color in blooms:
            grad = QRadialGradient(center, radius)
            grad.setColorAt(0, color)
            edge = QColor(color)
            edge.setAlpha(0)
            grad.setColorAt(1, edge)
            p.fillRect(r, QBrush(grad))

        # Restrained diagonal light ribbon.
        ribbon = QLinearGradient(0, r.height() * .88, r.width() * .80, r.height() * .05)
        ribbon.setColorAt(0.0, QColor(255, 125, 34, 0))
        ribbon.setColorAt(.45, QColor(255, 155, 62, 26))
        ribbon.setColorAt(.53, QColor(255, 197, 105, 35))
        ribbon.setColorAt(1.0, QColor(255, 125, 34, 0))
        p.fillRect(r, ribbon)
        p.end()




def make_logo_icon():
    """Create a small TYPO mark for the window icon."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(3, 3, 58, 58, 16, 16)
    p.fillPath(path, QColor("#f59b35"))
    p.setPen(QPen(QColor("#fff4df"), 3))
    p.drawRoundedRect(14, 14, 36, 36, 9, 9)
    p.setFont(QFont("Arial", 25, QFont.Weight.Bold))
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "T")
    p.end()
    return QIcon(pix)


def panel_style(extra=""):
    return """
        QFrame#glassPanel {
            background: rgba(255, 226, 198, 20);
            border: 1px solid rgba(255, 209, 160, 58);
            border-radius: 20px;
        }
        """ + extra


class GlassPanel(QFrame):
    def __init__(self, parent=None, object_name="glassPanel"):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setStyleSheet(panel_style())


def label(text, size=10, color="#f8eadb", weight=QFont.Weight.Normal):
    w = QLabel(text)
    w.setFont(QFont("Segoe UI", size, weight))
    w.setStyleSheet(f"color: {color}; background: transparent;")
    return w


def button(text, primary=False, danger=False):
    b = QPushButton(text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setMinimumHeight(36)
    b.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
    if danger:
        b.setStyleSheet("""
            QPushButton { color: #ffd9d5; background: rgba(150, 38, 35, 100);
                border: 1px solid rgba(255, 94, 89, 190); border-radius: 18px; padding: 0 16px; }
            QPushButton:hover { background: rgba(190, 47, 42, 150); }
            QPushButton:pressed { background: rgba(115, 25, 23, 180); }
        """)
    elif primary:
        b.setStyleSheet("""
            QPushButton { color: #261306; background: #ffb32f; border: 1px solid #ffd17a;
                border-radius: 18px; padding: 0 18px; }
            QPushButton:hover { background: #ffc45b; }
            QPushButton:pressed { background: #e99419; }
        """)
    else:
        b.setStyleSheet("""
            QPushButton { color: #f9eadb; background: rgba(255, 229, 205, 16);
                border: 1px solid rgba(255, 209, 160, 70); border-radius: 18px; padding: 0 15px; }
            QPushButton:hover { background: rgba(255, 229, 205, 36); border-color: rgba(255, 215, 174, 130); }
            QPushButton:pressed { background: rgba(255, 229, 205, 48); }
        """)
    return b


class MetricCard(GlassPanel):
    def __init__(self, title, value, value_color="#fff4e8"):
        super().__init__()
        self.setMinimumHeight(82)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)
        lay.addWidget(label(title.upper(), 8, "#b9a394", QFont.Weight.DemiBold))
        self.value_label = label(value, 13, value_color, QFont.Weight.Bold)
        lay.addWidget(self.value_label)


class FeatureCard(GlassPanel):
    def __init__(self, title, description, checked=True):
        super().__init__()
        self.setMinimumHeight(76)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)
        icon_box = QLabel("✳")
        icon_box.setFixedSize(40, 40)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet("""
            color: #ffd69b; font-size: 18px; background: rgba(255, 192, 112, 28);
            border: 1px solid rgba(255, 213, 162, 50); border-radius: 14px;
        """)
        row.addWidget(icon_box)
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.addWidget(label(title, 10, "#fff1e2", QFont.Weight.DemiBold))
        desc = label(description, 8, "#c9b6a5")
        desc.setWordWrap(True)
        text_col.addWidget(desc)
        row.addLayout(text_col, 1)
        self.toggle = QCheckBox()
        self.toggle.setChecked(checked)
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.setStyleSheet("""
            QCheckBox { spacing: 0; }
            QCheckBox::indicator { width: 38px; height: 22px; border-radius: 11px;
                background: rgba(230, 216, 203, 95); border: 1px solid rgba(255,255,255,70); }
            QCheckBox::indicator:checked { background: #50d783; border: 1px solid #70f2a0; }
            QCheckBox::indicator:unchecked { background: #655b56; border: 1px solid #81736b; }
        """)
        row.addWidget(self.toggle)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(make_logo_icon())
        self.resize(1440, 940)
        self.setMinimumSize(1080, 720)
        self.setStyleSheet("""
            QMainWindow { background: #17100e; }
            QWidget { color: #f8eadb; }
            QSlider::groove:horizontal { height: 6px; background: rgba(255, 230, 210, 40); border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #f6a52c; border-radius: 3px; }
            QSlider::handle:horizontal { background: #ffe4a0; border: 2px solid #fff0c7; width: 16px; height: 16px; margin: -6px 0; border-radius: 9px; }
            QTextEdit { color: #f4e7d8; background: rgba(15, 11, 10, 190); border: 1px solid rgba(255, 212, 166, 45); border-radius: 14px; padding: 14px; selection-background-color: #9a5b27; }
            QScrollBar:vertical { width: 9px; background: transparent; margin: 4px 1px; }
            QScrollBar::handle:vertical { background: rgba(255, 208, 161, 85); border-radius: 4px; min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        root = AmbientBackground()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(18)

        sidebar = self.build_sidebar()
        sidebar.setFixedWidth(235)
        outer.addWidget(sidebar)

        main = QWidget()
        main.setStyleSheet("background: transparent;")
        main_col = QVBoxLayout(main)
        main_col.setContentsMargins(0, 0, 0, 0)
        main_col.setSpacing(14)
        outer.addWidget(main, 1)

        main_col.addWidget(self.build_header())
        main_col.addWidget(self.build_tabs())
        main_col.addWidget(self.build_execution_panel())
        main_col.addWidget(self.build_sliders())
        main_col.addWidget(self.build_code_panel(), 1)
        main_col.addWidget(self.build_features())

        self.statusBar().setStyleSheet("""
            QStatusBar { color: #bfa894; background: rgba(20, 12, 9, 170);
                border-top: 1px solid rgba(255, 213, 164, 35); }
        """)
        self.statusBar().showMessage("TYPO Studio  •  Ready  •  Clipboard integration available")

    def build_sidebar(self):
        panel = GlassPanel()
        panel.setStyleSheet("""
            QFrame#glassPanel { background: rgba(255, 218, 182, 18);
                border: 1px solid rgba(255, 209, 160, 52); border-radius: 22px; }
        """)
        col = QVBoxLayout(panel)
        col.setContentsMargins(14, 16, 14, 14)
        col.setSpacing(10)

        brand = GlassPanel()
        brand.setStyleSheet("""
            QFrame#glassPanel { background: rgba(255, 181, 97, 25);
                border: 1px solid rgba(255, 218, 176, 60); border-radius: 16px; }
        """)
        br = QHBoxLayout(brand)
        br.setContentsMargins(12, 10, 12, 10)
        mark = QLabel("T")
        mark.setFixedSize(36, 36)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        mark.setStyleSheet("background: #f2a33c; color: #2a170c; border-radius: 11px;")
        br.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(3)
        brand_text.addWidget(label("TYPO STUDIO", 10, "#ffd18b", QFont.Weight.Bold))
        brand_text.addWidget(label("Vision Liquid Glass", 8, "#e3cbbb"))
        br.addLayout(brand_text, 1)
        dot = QLabel("●")
        dot.setStyleSheet("color: #5be08a; background: transparent;")
        br.addWidget(dot)
        col.addWidget(brand)
        col.addSpacing(8)

        groups = [
            ("CONTROL DECK", [("⌂", "Control Deck", True)]),
            ("PRECISION INPUT ENGINE", [("◌", "Live Chat", False), ("▧", "Images", False)]),
            ("SEQUENCER", [("▦", "Sequencer Deck", True), ("ϟ", "Biometrics Lab", False)]),
            ("TOOLS", [("♧", "Code Memory", False), ("▥", "Session Telemetry", False)]),
        ]
        for heading, items in groups:
            col.addWidget(label(heading, 8, "#bda18b", QFont.Weight.DemiBold))
            for icon_text, text, active in items:
                b = QPushButton(f"{icon_text}    {text}" + ("     •" if active and text == "Sequencer Deck" else ""))
                b.setMinimumHeight(38)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet("""
                    QPushButton { text-align: left; padding: 0 11px; color: #f0ddcb;
                        background: transparent; border: 1px solid transparent; border-radius: 13px; }
                    QPushButton:hover { background: rgba(255, 226, 196, 24); border-color: rgba(255, 218, 176, 45); }
                """ if not active else """
                    QPushButton { text-align: left; padding: 0 11px; color: #fff3e3;
                        background: rgba(255, 172, 74, 36); border: 1px solid rgba(255, 204, 137, 90); border-radius: 13px; }
                    QPushButton:hover { background: rgba(255, 185, 91, 54); }
                """)
                b.clicked.connect(lambda checked=False, name=text: self.statusBar().showMessage(f"{name} selected — navigation prototype"))
                col.addWidget(b)
            col.addSpacing(5)

        col.addStretch(1)
        hotkey = GlassPanel()
        hotkey_col = QVBoxLayout(hotkey)
        hotkey_col.setContentsMargins(12, 12, 12, 12)
        hotkey_col.setSpacing(8)
        hotkey_col.addWidget(label("HARDWARE HOTKEY", 8, "#bda18b", QFont.Weight.DemiBold))
        hotkey_col.addWidget(label("⌥   Alt  +  Z  +  T", 10, "#fff0dc", QFont.Weight.Bold))
        abort = button("●  Emergency Abort  [ Esc ]", danger=True)
        abort.clicked.connect(lambda: self.statusBar().showMessage("Emergency abort requested"))
        hotkey_col.addWidget(abort)
        col.addWidget(hotkey)
        return panel

    def build_header(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        row = QHBoxLayout(w)
        row.setContentsMargins(4, 2, 4, 0)
        left = QVBoxLayout()
        left.setSpacing(5)
        left.addWidget(label("VISION OS  //  AUTOMATION STUDIO", 8, "#d8a66b", QFont.Weight.DemiBold))
        title = label("Control Deck  ·  Dynamic Glass Sequencer", 20, "#fff4e8", QFont.Weight.Bold)
        left.addWidget(title)
        row.addLayout(left, 1)
        for text in ("●  Target: Standby", "◖))  Audio On", "◉  Ghost HUD"):
            row.addWidget(button(text))
        return w

    def build_tabs(self):
        panel = GlassPanel()
        panel.setStyleSheet("""
            QFrame#glassPanel { background: rgba(255, 221, 190, 15);
                border: 1px solid rgba(255, 209, 160, 48); border-radius: 22px; }
        """)
        row = QHBoxLayout(panel)
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(8)
        add = button("+")
        add.setFixedWidth(42)
        row.addWidget(add)
        tabs = ["●  Primary Studio", "Biometrics", "Code Buffer", "Telemetry Log", "Anti-Gaze"]
        for i, t in enumerate(tabs):
            b = QPushButton(t)
            b.setMinimumHeight(34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton { color: %s; background: %s; border: 1px solid %s;
                    border-radius: 17px; padding: 0 14px; }
                QPushButton:hover { background: rgba(255, 205, 148, 40); }
            """ % ("#ffe5bc" if i == 0 else "#ddc7b5",
                   "rgba(255, 173, 69, 42)" if i == 0 else "transparent",
                   "rgba(255, 196, 118, 90)" if i == 0 else "transparent"))
            b.clicked.connect(lambda checked=False, tab=t: self.statusBar().showMessage(f"{tab.replace('●  ', '')} tab selected"))
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(button("♢  Liquid Glass"))
        return panel

    def build_execution_panel(self):
        panel = GlassPanel()
        col = QVBoxLayout(panel)
        col.setContentsMargins(18, 14, 18, 14)
        col.setSpacing(14)
        row = QHBoxLayout()
        ready = button("●  Ready")
        ready.setMinimumWidth(100)
        row.addWidget(ready)
        row.addWidget(label("Focus your target editor and press Alt + Z + T", 9, "#d7c0ae"), 1)
        self.arm_btn = button("▶  Arm & Execute  [ Alt + Z + T ]", primary=True)
        self.arm_btn.clicked.connect(self.toggle_execution)
        row.addWidget(self.arm_btn)
        self.pause_btn = button("Ⅱ  Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        row.addWidget(self.pause_btn)
        abort = button("■  Esc / Abort", danger=True)
        abort.clicked.connect(self.abort_execution)
        row.addWidget(abort)
        col.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.setStyleSheet("""
            QProgressBar { background: rgba(255, 231, 209, 24); border: 0; border-radius: 2px; }
            QProgressBar::chunk { background: #ffb12d; border-radius: 2px; }
        """)
        col.addWidget(self.progress)

        metrics = QGridLayout()
        metrics.setSpacing(10)
        self.progress_metric = MetricCard("Progress", "0 / 0 (0%)")
        self.velocity_metric = MetricCard("Velocity", "80.0 WPM", "#ffb52e")
        self.time_metric = MetricCard("Elapsed / Remain", "00:00 / 00:00")
        self.token_metric = MetricCard("Last Token / Dwell", "[ ↵ ]  ~55ms", "#69d8ff")
        for i, card in enumerate((self.progress_metric, self.velocity_metric, self.time_metric, self.token_metric)):
            metrics.addWidget(card, 0, i)
        col.addLayout(metrics)
        return panel

    def toggle_execution(self):
        if self.arm_btn.text().startswith("▶"):
            self.arm_btn.setText("■  Stop Preview")
            self.statusBar().showMessage("Preview armed — this UI prototype does not type into external applications.")
        else:
            self.arm_btn.setText("▶  Arm & Execute  [ Alt + Z + T ]")
            self.statusBar().showMessage("Preview stopped")

    def toggle_pause(self):
        paused = self.pause_btn.text().startswith("Ⅱ")
        self.pause_btn.setText("▶  Resume" if paused else "Ⅱ  Pause")
        self.statusBar().showMessage("Preview paused" if paused else "Preview resumed")

    def abort_execution(self):
        self.arm_btn.setText("▶  Arm & Execute  [ Alt + Z + T ]")
        self.pause_btn.setText("Ⅱ  Pause")
        self.progress.setValue(0)
        self.statusBar().showMessage("Emergency abort — preview reset")

    def build_sliders(self):
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        grid = QGridLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)
        self.typo_value = label("1.5%", 10, "#ffce71", QFont.Weight.Bold)
        typo = self.slider_card("Typo & Mistake Rate", self.typo_value, 0, 50, 15, "0.0% (Flawless)", "5.0% (Natural Typos)", "#f5a12b")
        self.safety_value = label("3.0s", 10, "#f08be9", QFont.Weight.Bold)
        safety = self.slider_card("Safety Focus Countdown", self.safety_value, 10, 80, 30, "1.0s (Fast Switch)", "8.0s (Relaxed)", "#d65be8")
        grid.addWidget(typo, 0, 0)
        grid.addWidget(safety, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return wrap

    def slider_card(self, title_text, value_label, minimum, maximum, value, left_text, right_text, accent):
        panel = GlassPanel()
        col = QVBoxLayout(panel)
        col.setContentsMargins(18, 14, 18, 14)
        col.setSpacing(8)
        top = QHBoxLayout()
        top.addWidget(label(title_text, 12, "#fff1e4", QFont.Weight.Bold), 1)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setMinimumWidth(62)
        value_label.setStyleSheet(f"color: {accent}; background: rgba(255,255,255,12); border: 1px solid {accent}; border-radius: 10px; padding: 5px 8px;")
        top.addWidget(value_label)
        col.addLayout(top)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 6px; background: rgba(255, 230, 210, 35); border-radius: 3px; }}
            QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {accent}; border: 2px solid rgba(255,245,220,210); width: 15px; height: 15px; margin: -6px 0; border-radius: 9px; }}
        """)
        if "Typo" in title_text:
            slider.valueChanged.connect(lambda v: value_label.setText(f"{v / 10:.1f}%"))
        else:
            slider.valueChanged.connect(lambda v: value_label.setText(f"{v / 10:.1f}s"))
        col.addWidget(slider)
        ends = QHBoxLayout()
        ends.addWidget(label(left_text, 8, "#bba391"))
        ends.addStretch(1)
        ends.addWidget(label(right_text, 8, "#bba391"))
        col.addLayout(ends)
        return panel

    def build_code_panel(self):
        panel = GlassPanel()
        col = QVBoxLayout(panel)
        col.setContentsMargins(18, 14, 18, 14)
        col.setSpacing(10)
        top = QHBoxLayout()
        top.addWidget(label("●  Live Code Buffer & Non-Destructive Inspection", 12, "#fff0e2", QFont.Weight.Bold), 1)
        refresh = button("↻  Refresh")
        refresh.clicked.connect(self.refresh_clipboard)
        top.addWidget(refresh)
        load = button("▣  Load Sample Code")
        load.clicked.connect(self.load_sample)
        top.addWidget(load)
        col.addLayout(top)

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.setPlaceholderText("Copy source code from your IDE, or click 'Load Sample Code'.")
        self.editor.setPlainText("")
        self.editor.setMinimumHeight(145)
        col.addWidget(self.editor, 1)

        self.code_status = label("Clipboard empty", 9, "#ffb02e")
        col.addWidget(self.code_status)
        self.editor.textChanged.connect(self.update_code_stats)
        return panel

    def refresh_clipboard(self):
        text = QApplication.clipboard().text()
        if text.strip():
            self.editor.setPlainText(text)
            self.code_status.setText("Clipboard imported")
            self.code_status.setStyleSheet("color: #62e69a; background: transparent;")
            self.statusBar().showMessage("Code imported from clipboard")
        else:
            self.code_status.setText("Clipboard empty")
            self.code_status.setStyleSheet("color: #ffb02e; background: transparent;")
            self.statusBar().showMessage("Clipboard does not contain text")

    def load_sample(self):
        self.editor.setPlainText(SAMPLE_CODE)
        self.code_status.setText("Sample code loaded")
        self.code_status.setStyleSheet("color: #62e69a; background: transparent;")
        self.statusBar().showMessage("Sample code loaded into the buffer")

    def update_code_stats(self):
        text = self.editor.toPlainText()
        chars = len(text)
        lines = len(text.splitlines()) if text else 0
        words = len(text.split()) if text else 0
        self.code_status.setText(f"{chars} characters  •  {lines} lines  •  {words} tokens  •  Code buffer")
        self.code_status.setStyleSheet("color: #67d7ff; background: transparent;" if text else "color: #ffb02e; background: transparent;")

    def build_features(self):
        panel = GlassPanel()
        col = QVBoxLayout(panel)
        col.setContentsMargins(18, 14, 18, 14)
        col.setSpacing(10)
        col.addWidget(label("●  Automation & Input Behavior", 12, "#fff0e2", QFont.Weight.Bold))
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.addWidget(FeatureCard("Simulated Cursor Wandering", "Optional pointer movement simulation for natural interaction.", True), 0, 0)
        grid.addWidget(FeatureCard("Complexity Cadence Throttler", "Adjusts the typing pace for longer or more complex code.", True), 0, 1)
        grid.addWidget(FeatureCard("Incremental Code Construction", "Builds the preview buffer in incremental steps.", False), 1, 0)
        grid.addWidget(FeatureCard("Selection & Refactoring Simulation", "Preview selection and replacement-style editing behavior.", True), 1, 1)
        col.addLayout(grid)
        return panel


TypoApp = MainWindow


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("TYPO Studio")
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
