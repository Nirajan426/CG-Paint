"""
CG-Paint — PyQt6 Edition
All CG algorithms (Bresenham, Midpoint Circle/Ellipse, Flood Fill, Bezier)
are preserved exactly. Only the UI layer is replaced with PyQt6 + QPainter.
"""

import sys
import math
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QStatusBar,
    QDockWidget, QLabel, QPushButton, QSlider, QColorDialog,
    QFileDialog, QMessageBox, QInputDialog, QScrollArea,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QCheckBox,
    QSizePolicy, QSplitter, QMenu,
)
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QColor, QAction,
    QIcon, QCursor, QPainterPath, QFont, QKeySequence,
)
from PyQt6.QtCore import Qt, QPoint, QRect, QSize, pyqtSignal


# ======================== CG Algorithms (unchanged) ========================

def bresenham_line(x1, y1, x2, y2):
    points = []
    dx = abs(x2 - x1); dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    while True:
        points.append((x1, y1))
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy; x1 += sx
        if e2 < dx:
            err += dx; y1 += sy
    return points


def midpoint_circle(cx, cy, r):
    points = []
    x, y = 0, r
    d = 1 - r
    while x <= y:
        for ddx, ddy in [(x,y),(y,x),(-x,y),(-y,x),(x,-y),(y,-x),(-x,-y),(-y,-x)]:
            points.append((cx + ddx, cy + ddy))
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1
    return points


def midpoint_ellipse(cx, cy, rx, ry):
    points = []
    if rx == 0 or ry == 0:
        return points
    rx2, ry2 = rx * rx, ry * ry
    x, y = 0, ry
    d1 = ry2 - rx2 * ry + 0.25 * rx2
    dx = 2 * ry2 * x; dy = 2 * rx2 * y
    while dx < dy:
        for sx, sy in [(x,y),(-x,y),(x,-y),(-x,-y)]:
            points.append((cx+sx, cy+sy))
        x += 1; dx += 2 * ry2
        if d1 < 0:
            d1 += dx + ry2
        else:
            y -= 1; dy -= 2 * rx2
            d1 += dx - dy + ry2
    d2 = ry2*(x+0.5)**2 + rx2*(y-1)**2 - rx2*ry2
    while y >= 0:
        for sx, sy in [(x,y),(-x,y),(x,-y),(-x,-y)]:
            points.append((cx+sx, cy+sy))
        y -= 1; dy -= 2 * rx2
        if d2 > 0:
            d2 += rx2 - dy
        else:
            x += 1; dx += 2 * ry2
            d2 += dx - dy + rx2
    return points


def flood_fill(image: QImage, x, y, fill_color: QColor):
    w, h = image.width(), image.height()
    if x < 0 or x >= w or y < 0 or y >= h:
        return
    target = image.pixel(x, y)
    fill_rgba = fill_color.rgba()
    if target == fill_rgba:
        return
    stack = [(x, y)]
    visited = set()
    while stack:
        cx, cy = stack.pop()
        if (cx, cy) in visited:
            continue
        if cx < 0 or cx >= w or cy < 0 or cy >= h:
            continue
        if image.pixel(cx, cy) != target:
            continue
        visited.add((cx, cy))
        image.setPixel(cx, cy, fill_rgba)
        stack.extend([(cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)])


def bezier_curve(control_points, num_steps=500):
    if len(control_points) < 2:
        return []
    points = []
    n = len(control_points) - 1
    for i in range(num_steps + 1):
        t = i / num_steps
        temp = list(control_points)
        for k in range(n):
            temp = [
                ((1-t)*temp[j][0]+t*temp[j+1][0],
                 (1-t)*temp[j][1]+t*temp[j+1][1])
                for j in range(len(temp)-1)
            ]
        px, py = int(round(temp[0][0])), int(round(temp[0][1]))
        if not points or points[-1] != (px, py):
            points.append((px, py))
    return points


# ======================== Canvas Widget ========================

class CanvasWidget(QWidget):
    mouse_moved = pyqtSignal(int, int)

    def __init__(self, width=900, height=650, parent=None):
        super().__init__(parent)
        self.img_w = width
        self.img_h = height
        self.setMinimumSize(width, height)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Main drawing surface — ARGB32_Premultiplied for correct alpha compositing
        self.image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        self.image.fill(QColor("white"))

        # Overlay for previews (transparent)
        self.overlay = QImage(width, height, QImage.Format.Format_ARGB32)
        self.overlay.fill(Qt.GlobalColor.transparent)

        self.setMouseTracking(True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.drawImage(0, 0, self.image)
        p.drawImage(0, 0, self.overlay)
        p.end()

    def clear_overlay(self):
        self.overlay.fill(Qt.GlobalColor.transparent)

    def mouseMoveEvent(self, event):
        self.mouse_moved.emit(int(event.position().x()), int(event.position().y()))
        super().mouseMoveEvent(event)


# ======================== Color Swatch ========================

class ColorSwatch(QLabel):
    clicked = pyqtSignal(str)  # "left" or "right"

    def __init__(self, color="#000000", size=22, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.color = color
        self._refresh()

    def set_color(self, color):
        self.color = color
        self._refresh()

    def _refresh(self):
        self.setStyleSheet(
            f"background:{self.color};border:1px solid #666;border-radius:3px;"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit("left")
        elif event.button() == Qt.MouseButton.RightButton:
            self.clicked.emit("right")


# ======================== Gradient Bar ========================

class GradientBar(QWidget):
    color_picked = pyqtSignal(str)

    STOPS = [
        (255,0,0),(255,165,0),(255,255,0),(0,255,0),
        (0,255,255),(0,0,255),(128,0,255),(255,0,255),(255,0,0),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(18)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        p = QPainter(self)
        w = self.width()
        segs = len(self.STOPS) - 1
        for x in range(w):
            t = x / max(1, w-1) * segs
            idx = min(int(t), segs-1)
            frac = t - idx
            r = int(self.STOPS[idx][0]*(1-frac) + self.STOPS[idx+1][0]*frac)
            g = int(self.STOPS[idx][1]*(1-frac) + self.STOPS[idx+1][1]*frac)
            b = int(self.STOPS[idx][2]*(1-frac) + self.STOPS[idx+1][2]*frac)
            p.setPen(QColor(r, g, b))
            p.drawLine(x, 0, x, self.height())
        p.end()

    def mousePressEvent(self, event):
        self._pick(event.position().x())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._pick(event.position().x())

    def _pick(self, ex):
        w = self.width()
        segs = len(self.STOPS) - 1
        t = max(0, min(ex, w-1)) / max(1, w-1) * segs
        idx = min(int(t), segs-1)
        frac = t - idx
        r = int(self.STOPS[idx][0]*(1-frac) + self.STOPS[idx+1][0]*frac)
        g = int(self.STOPS[idx][1]*(1-frac) + self.STOPS[idx+1][1]*frac)
        b = int(self.STOPS[idx][2]*(1-frac) + self.STOPS[idx+1][2]*frac)
        self.color_picked.emit(f"#{r:02x}{g:02x}{b:02x}")


# ======================== Main Window ========================

PALETTE_COLORS = [
    "#000000","#434343","#800000","#808000",
    "#008000","#008080","#000080","#800080",
    "#FFFFFF","#C0C0C0","#FF0000","#FFFF00",
    "#00FF00","#00FFFF","#0000FF","#FF00FF",
    "#FF8C00","#FFD700","#7CFC00","#40E0D0",
    "#1E90FF","#BA55D3","#FF69B4","#A0522D",
]

DARK = {
    "bg":           "#1E1E2E",
    "surface":      "#2A2A3E",
    "surface2":     "#313147",
    "accent":       "#7C6AF7",
    "accent2":      "#C084FC",
    "text":         "#E2E0F0",
    "text_dim":     "#888899",
    "border":       "#3A3A55",
    "success":      "#50FA7B",
    "danger":       "#FF5555",
    "toolbar":      "#252538",
    "canvas_bg":    "#12121E",
    "btn":          "#333350",
    "btn_hover":    "#444468",
    "btn_active":   "#7C6AF7",
}

TOOL_DEFS = [
    ("✏️",  "Pencil",    "pencil"),
    ("🖌️", "Brush",     "brush"),
    ("∿",  "Bezier",    "curve"),
    ("⬡",  "Polygon",   "polygon"),
    ("╱",  "Line",      "line"),
    ("▭",  "Rectangle", "rectangle"),
    ("○",  "Circle",    "circle"),
    ("⬭",  "Oval",      "oval"),
    ("▢",  "RoundRect", "roundrect"),
    ("⌫",  "Eraser",    "eraser"),
    ("🪣", "Fill",      "fill"),
    ("T",  "Text",      "text"),
    ("🔍", "Picker",    "picker"),
]

SS_MAIN = f"""
QMainWindow, QWidget {{
    background: {DARK['bg']};
    color: {DARK['text']};
    font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
    font-size: 13px;
}}
QToolBar {{
    background: {DARK['toolbar']};
    border-bottom: 1px solid {DARK['border']};
    spacing: 4px;
    padding: 4px 8px;
}}
QStatusBar {{
    background: {DARK['surface']};
    color: {DARK['text_dim']};
    border-top: 1px solid {DARK['border']};
    font-size: 12px;
}}
QDockWidget {{
    color: {DARK['text']};
    font-weight: bold;
    titlebar-close-icon: none;
}}
QDockWidget::title {{
    background: {DARK['surface2']};
    border-bottom: 1px solid {DARK['border']};
    padding: 6px 10px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: {DARK['text_dim']};
}}
QScrollArea {{ border: none; background: {DARK['canvas_bg']}; }}
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {DARK['surface']};
    width: 8px; height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {DARK['border']};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QLabel {{ color: {DARK['text']}; }}
QSlider::groove:horizontal {{
    background: {DARK['surface2']};
    height: 4px; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {DARK['accent']};
    width: 14px; height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}}
QSlider::sub-page:horizontal {{ background: {DARK['accent']}; border-radius: 2px; }}
QCheckBox {{ color: {DARK['text']}; spacing: 6px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 4px;
    border: 1px solid {DARK['border']};
    background: {DARK['surface2']};
}}
QCheckBox::indicator:checked {{
    background: {DARK['accent']};
    border: 1px solid {DARK['accent']};
}}
QMenuBar {{
    background: {DARK['toolbar']};
    color: {DARK['text']};
    border-bottom: 1px solid {DARK['border']};
}}
QMenuBar::item:selected {{ background: {DARK['btn_hover']}; border-radius: 4px; }}
QMenu {{
    background: {DARK['surface2']};
    color: {DARK['text']};
    border: 1px solid {DARK['border']};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{ padding: 6px 20px; border-radius: 4px; }}
QMenu::item:selected {{ background: {DARK['accent']}; color: white; }}
QMenu::separator {{ height: 1px; background: {DARK['border']}; margin: 4px 8px; }}
QInputDialog, QMessageBox {{
    background: {DARK['surface']};
    color: {DARK['text']};
}}
"""

BTN_SS = f"""
QPushButton {{
    background: {DARK['btn']};
    color: {DARK['text']};
    border: 1px solid {DARK['border']};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
}}
QPushButton:hover {{ background: {DARK['btn_hover']}; border-color: {DARK['accent']}; }}
QPushButton:pressed, QPushButton:checked {{
    background: {DARK['accent']};
    color: white;
    border-color: {DARK['accent']};
}}
"""

TOOL_BTN_SS = f"""
QPushButton {{
    background: {DARK['btn']};
    color: {DARK['text']};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 6px;
    font-size: 15px;
    text-align: center;
}}
QPushButton:hover {{ background: {DARK['btn_hover']}; border-color: {DARK['border']}; }}
QPushButton:checked {{
    background: {DARK['accent']};
    color: white;
    border-color: {DARK['accent2']};
}}
"""


class CGPaintQt(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CG-Paint  ·  PyQt6")
        self.resize(1280, 800)

        # State
        self.current_tool = "brush"
        self.fg_color = QColor("#00D4FF")
        self.bg_color = QColor("#FFFFFF")
        self.brush_size = 4
        self.opacity = 100
        self.fill_shape = False
        self.start_pos = None
        self.prev_pos = None
        self.polygon_points = []
        self.bezier_points = []
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo = 40
        self.file_path = None
        self.tool_buttons = {}

        self.setStyleSheet(SS_MAIN)
        self._build_ui()
        self._push_undo()

    # ----------------------------------------------------------------
    # UI Construction
    # ----------------------------------------------------------------

    def _build_ui(self):
        self._build_menu()
        self._build_toolbar()
        self._build_canvas()
        self._build_left_dock()
        self._build_right_dock()
        self._build_statusbar()

    def _build_menu(self):
        mb = self.menuBar()

        # File
        fm = mb.addMenu("File")
        self._action(fm, "New",     "Ctrl+N", self.new_canvas)
        self._action(fm, "Open…",   "Ctrl+O", self.open_file)
        self._action(fm, "Save",    "Ctrl+S", self.save_file)
        self._action(fm, "Save As…","",       self.save_file_as)
        fm.addSeparator()
        self._action(fm, "Exit", "Ctrl+Q", self.close)

        # Edit
        em = mb.addMenu("Edit")
        self._action(em, "Undo",         "Ctrl+Z", self.undo)
        self._action(em, "Redo",         "Ctrl+Y", self.redo)
        em.addSeparator()
        self._action(em, "Clear Canvas", "",       self.clear_canvas)

        # Image
        im = mb.addMenu("Image")
        self._action(im, "Resize Canvas…", "", self._resize_action)
        self._action(im, "Rotate 90°",     "", self._rotate_action)

        # Help
        hm = mb.addMenu("Help")
        self._action(hm, "About / Shortcuts", "", self._help_dialog)

    def _action(self, menu, label, shortcut, slot):
        act = QAction(label, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        # Save button (accent)
        save_btn = QPushButton("💾  Save")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {DARK['accent']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 18px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {DARK['accent2']}; }}
        """)
        save_btn.clicked.connect(self.save_file)
        tb.addWidget(save_btn)
        tb.addSeparator()

        # Rotate / Resize
        for label, slot in [("↻ Rotate", self._rotate_action),
                              ("⤢ Resize", self._resize_action)]:
            b = QPushButton(label)
            b.setStyleSheet(BTN_SS)
            b.clicked.connect(slot)
            tb.addWidget(b)

        tb.addSeparator()

        # Fill checkbox
        self.fill_cb = QCheckBox("Fill Shapes")
        self.fill_cb.stateChanged.connect(lambda s: setattr(self, "fill_shape", bool(s)))
        tb.addWidget(self.fill_cb)

        tb.addSeparator()

        # Size slider
        tb.addWidget(QLabel(" Size:"))
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(1, 50)
        self.size_slider.setValue(self.brush_size)
        self.size_slider.setFixedWidth(140)
        self.size_slider.valueChanged.connect(self._on_size_change)
        tb.addWidget(self.size_slider)
        self.size_lbl = QLabel(str(self.brush_size))
        self.size_lbl.setFixedWidth(28)
        self.size_lbl.setStyleSheet(f"color:{DARK['accent']};font-weight:bold;")
        tb.addWidget(self.size_lbl)

        # Undo / Redo in toolbar too
        tb.addSeparator()
        for label, slot in [("◀ Undo", self.undo), ("Redo ▶", self.redo)]:
            b = QPushButton(label)
            b.setStyleSheet(BTN_SS)
            b.clicked.connect(slot)
            tb.addWidget(b)

    def _build_canvas(self):
        self.canvas = CanvasWidget(900, 650)
        self.canvas.mouse_moved.connect(self._on_mouse_moved)
        self.canvas.setStyleSheet(f"background:{DARK['canvas_bg']};")

        self.canvas.mousePressEvent       = self.on_mouse_down
        self.canvas.mouseMoveEvent        = self.on_mouse_drag
        self.canvas.mouseReleaseEvent     = self.on_mouse_up
        self.canvas.mouseDoubleClickEvent = self.on_double_click
        self.canvas.contextMenuEvent      = self.on_canvas_right_click

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setStyleSheet(f"background:{DARK['canvas_bg']};border:none;")
        self.setCentralWidget(scroll)

    def _build_left_dock(self):
        dock = QDockWidget("Tools", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setFixedWidth(90)

        # Outer container
        outer = QWidget()
        outer.setStyleSheet(f"background:{DARK['surface']};")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Scrollable area for tool buttons
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: {DARK['surface']}; }}
            QScrollBar:vertical {{
                background: {DARK['surface']};
                width: 4px; border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {DARK['border']};
                border-radius: 2px; min-height: 20px;
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
        """)

        btn_widget = QWidget()
        btn_widget.setStyleSheet(f"background:{DARK['surface']};")
        btn_layout = QVBoxLayout(btn_widget)
        btn_layout.setContentsMargins(6, 8, 6, 4)
        btn_layout.setSpacing(4)

        for icon, label, tool_id in TOOL_DEFS:
            btn = QPushButton(f"{icon}\n{label}")
            btn.setStyleSheet(TOOL_BTN_SS)
            btn.setCheckable(True)
            btn.setFixedHeight(54)
            btn.clicked.connect(lambda checked, t=tool_id: self._select_tool(t))
            self.tool_buttons[tool_id] = btn
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        scroll.setWidget(btn_widget)
        outer_layout.addWidget(scroll)

        # Color swatches pinned at bottom (outside scroll)
        bottom = QWidget()
        bottom.setStyleSheet(f"background:{DARK['surface']};border-top:1px solid {DARK['border']};")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(6, 6, 6, 8)
        bottom_layout.setSpacing(4)

        swatch_lbl = QLabel("FG / BG")
        swatch_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:9px;letter-spacing:1px;border:none;")
        swatch_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(swatch_lbl)

        swatch_row = QHBoxLayout()
        self.fg_swatch = ColorSwatch(self.fg_color.name(), 28)
        self.bg_swatch = ColorSwatch(self.bg_color.name(), 28)
        self.fg_swatch.clicked.connect(lambda _: self._pick_color("fg"))
        self.bg_swatch.clicked.connect(lambda _: self._pick_color("bg"))
        swatch_row.addWidget(self.fg_swatch)
        swatch_row.addWidget(self.bg_swatch)
        bottom_layout.addLayout(swatch_row)

        outer_layout.addWidget(bottom)
        dock.setWidget(outer)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self._highlight_tool()

    def _build_right_dock(self):
        dock = QDockWidget("Colors & Settings", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setFixedWidth(230)

        w = QWidget()
        w.setStyleSheet(f"background:{DARK['surface']};")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # ---- Gradient bar ----
        grad_lbl = QLabel("QUICK COLOR")
        grad_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:10px;letter-spacing:1px;")
        layout.addWidget(grad_lbl)

        self.grad_bar = GradientBar()
        self.grad_bar.color_picked.connect(lambda c: self._set_color("fg", QColor(c)))
        layout.addWidget(self.grad_bar)

        # ---- Palette ----
        pal_lbl = QLabel("PALETTE")
        pal_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:10px;letter-spacing:1px;margin-top:4px;")
        layout.addWidget(pal_lbl)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(3)
        grid.setContentsMargins(0,0,0,0)
        for i, color in enumerate(PALETTE_COLORS):
            sw = ColorSwatch(color, 20)
            sw.clicked.connect(lambda side, c=color: self._set_color("fg" if side=="left" else "bg", QColor(c)))
            grid.addWidget(sw, i // 6, i % 6)
        layout.addWidget(grid_w)

        edit_btn = QPushButton("Custom Color…")
        edit_btn.setStyleSheet(BTN_SS)
        edit_btn.clicked.connect(lambda: self._pick_color("fg"))
        layout.addWidget(edit_btn)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"color:{DARK['border']};")
        layout.addWidget(sep1)

        # ---- Brush size ----
        brush_lbl = QLabel("BRUSH SIZE")
        brush_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:10px;letter-spacing:1px;")
        layout.addWidget(brush_lbl)

        size_row = QHBoxLayout()
        self.size_slider2 = QSlider(Qt.Orientation.Horizontal)
        self.size_slider2.setRange(1, 50)
        self.size_slider2.setValue(self.brush_size)
        self.size_slider2.valueChanged.connect(self._on_size_change2)
        self.size_lbl2 = QLabel(str(self.brush_size))
        self.size_lbl2.setFixedWidth(28)
        self.size_lbl2.setStyleSheet(f"color:{DARK['accent']};font-weight:bold;")
        size_row.addWidget(self.size_slider2)
        size_row.addWidget(self.size_lbl2)
        layout.addLayout(size_row)

        # ---- Opacity ----
        op_lbl = QLabel("OPACITY")
        op_lbl.setStyleSheet(f"color:{DARK['text_dim']};font-size:10px;letter-spacing:1px;")
        layout.addWidget(op_lbl)

        op_row = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_lbl = QLabel("100%")
        self.opacity_lbl.setFixedWidth(36)
        self.opacity_lbl.setStyleSheet(f"color:{DARK['accent']};font-weight:bold;")
        self.opacity_slider.valueChanged.connect(self._on_opacity_change)
        op_row.addWidget(self.opacity_slider)
        op_row.addWidget(self.opacity_lbl)
        layout.addLayout(op_row)

        layout.addStretch()
        dock.setWidget(w)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _build_statusbar(self):
        sb = self.statusBar()
        self.sb_pos   = QLabel("X: 0  Y: 0")
        self.sb_size  = QLabel(f"Canvas: {self.canvas.img_w} × {self.canvas.img_h}")
        self.sb_tool  = QLabel(f"Tool: brush")
        self.sb_color = QLabel()
        self.sb_color.setFixedSize(16, 16)
        self.sb_color.setStyleSheet(f"background:{self.fg_color.name()};border-radius:3px;")

        for w in [self.sb_color, self.sb_pos, self.sb_size, self.sb_tool]:
            sb.addWidget(w)
            sep = QFrame(); sep.setFrameShape(QFrame.Shape.VLine)
            sep.setStyleSheet(f"color:{DARK['border']};")
            sb.addWidget(sep)

        self.sb_hint = QLabel("")
        self.sb_hint.setStyleSheet(f"color:{DARK['accent']};font-style:italic;")
        sb.addPermanentWidget(self.sb_hint)

    # ----------------------------------------------------------------
    # Tool Selection
    # ----------------------------------------------------------------

    def _select_tool(self, tool_id):
        self._finish_polygon()
        self._finish_bezier()
        self.current_tool = tool_id
        self._highlight_tool()
        self.sb_tool.setText(f"Tool: {tool_id}")

        hints = {
            "curve":   "Bézier: Left-click to add control points  |  Right-click or Double-click to finish",
            "polygon": "Polygon: Left-click to add vertices  |  Right-click or Double-click to close",
            "fill":    "Fill: Left-click to flood-fill an area",
            "picker":  "Picker: Left-click to pick foreground color",
            "text":    "Text: Left-click on canvas to place text",
        }
        self.sb_hint.setText(hints.get(tool_id, ""))

        cursors = {
            "pencil": Qt.CursorShape.CrossCursor,
            "brush":  Qt.CursorShape.CrossCursor,
            "eraser": Qt.CursorShape.CrossCursor,
            "fill":   Qt.CursorShape.CrossCursor,
            "picker": Qt.CursorShape.CrossCursor,
            "text":   Qt.CursorShape.IBeamCursor,
        }
        self.canvas.setCursor(cursors.get(tool_id, Qt.CursorShape.CrossCursor))

    def _highlight_tool(self):
        for tid, btn in self.tool_buttons.items():
            btn.setChecked(tid == self.current_tool)

    # ----------------------------------------------------------------
    # Color helpers
    # ----------------------------------------------------------------

    def _set_color(self, which, color: QColor):
        if which == "fg":
            self.fg_color = color
            self.fg_swatch.set_color(color.name())
            self.sb_color.setStyleSheet(f"background:{color.name()};border-radius:3px;")
        else:
            self.bg_color = color
            self.bg_swatch.set_color(color.name())

    def _pick_color(self, which):
        initial = self.fg_color if which == "fg" else self.bg_color
        color = QColorDialog.getColor(initial, self, "Choose Color")
        if color.isValid():
            self._set_color(which, color)

    # ----------------------------------------------------------------
    # Size
    # ----------------------------------------------------------------

    def _on_size_change(self, val):
        self.brush_size = val
        self.size_lbl.setText(str(val))
        self.size_slider2.setValue(val)
        self.size_lbl2.setText(str(val))

    def _on_size_change2(self, val):
        self.brush_size = val
        self.size_lbl2.setText(str(val))
        self.size_slider.setValue(val)
        self.size_lbl.setText(str(val))

    def _on_opacity_change(self, val):
        self.opacity = val
        self.opacity_lbl.setText(f"{val}%")

    def _paint_color(self, color: QColor = None) -> QColor:
        """Return fg_color (or given color) with current opacity applied."""
        c = QColor(color or self.fg_color)
        c.setAlpha(int(self.opacity / 100 * 255))
        return c

    # ----------------------------------------------------------------
    # Drawing helpers (QPainter on QImage using CG algorithms)
    # ----------------------------------------------------------------

    def _draw_points(self, points, color: QColor, thickness=1):
        """Plot a list of (x,y) points onto the image using QPainter with alpha support."""
        p = QPainter(self.canvas.image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        r = max(0, thickness // 2)
        if r <= 1:
            p.setPen(color)
            for px, py in points:
                if 0 <= px < self.canvas.img_w and 0 <= py < self.canvas.img_h:
                    p.drawPoint(px, py)
        else:
            for px, py in points:
                p.drawEllipse(QPoint(px, py), r, r)
        p.end()

    def _draw_bresenham(self, x1, y1, x2, y2, color: QColor, thickness=1):
        pts = bresenham_line(x1, y1, x2, y2)
        self._draw_points(pts, color, thickness)

    def _draw_circle_cg(self, cx, cy, radius, color: QColor, thickness=1, fill=False):
        p = QPainter(self.canvas.image)
        if fill:
            p.setBrush(color)
            p.setPen(QPen(color, thickness))
            p.drawEllipse(QPoint(cx, cy), radius, radius)
        else:
            pts = midpoint_circle(cx, cy, radius)
            p.end()
            self._draw_points(pts, color, thickness)
            return
        p.end()

    def _draw_ellipse_cg(self, cx, cy, rx, ry, color: QColor, thickness=1, fill=False):
        p = QPainter(self.canvas.image)
        if fill:
            p.setBrush(color)
            p.setPen(QPen(color, thickness))
            p.drawEllipse(cx - rx, cy - ry, rx*2, ry*2)
        else:
            pts = midpoint_ellipse(cx, cy, rx, ry)
            p.end()
            self._draw_points(pts, color, thickness)
            return
        p.end()

    def _draw_rectangle(self, x1, y1, x2, y2, color: QColor, thickness=1, fill=False):
        p = QPainter(self.canvas.image)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        pen = QPen(color, thickness)
        p.setPen(pen)
        p.setBrush(color if fill else Qt.BrushStyle.NoBrush)
        p.drawRect(QRect(QPoint(x1, y1), QPoint(x2, y2)).normalized())
        p.end()

    def _draw_roundrect(self, x1, y1, x2, y2, color: QColor, thickness=1, fill=False, radius=15):
        p = QPainter(self.canvas.image)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setPen(QPen(color, thickness))
        p.setBrush(color if fill else Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRect(QPoint(x1, y1), QPoint(x2, y2)).normalized(), radius, radius)
        p.end()

    # ----------------------------------------------------------------
    # Overlay preview helpers
    # ----------------------------------------------------------------

    def _draw_preview(self, x, y):
        """Draw shape preview on overlay."""
        self.canvas.clear_overlay()
        p = QPainter(self.canvas.overlay)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.fg_color, self.brush_size, Qt.PenStyle.DashLine)
        p.setPen(pen)
        fill_brush = self.fg_color if self.fill_shape else Qt.BrushStyle.NoBrush
        p.setBrush(fill_brush)

        sx, sy = self.start_pos.x(), self.start_pos.y()
        tool = self.current_tool

        if tool == "line":
            p.drawLine(sx, sy, x, y)
        elif tool == "rectangle":
            p.drawRect(QRect(QPoint(sx, sy), QPoint(x, y)).normalized())
        elif tool == "roundrect":
            p.drawRoundedRect(QRect(QPoint(sx, sy), QPoint(x, y)).normalized(), 15, 15)
        elif tool == "oval":
            p.drawEllipse(QRect(QPoint(sx, sy), QPoint(x, y)).normalized())
        elif tool == "circle":
            radius = int(math.dist((sx, sy), (x, y)))
            p.drawEllipse(QPoint(sx, sy), radius, radius)

        p.end()
        self.canvas.update()

    def _draw_bezier_overlay(self, tentative=None):
        self.canvas.clear_overlay()
        pts = list(self.bezier_points)
        if tentative:
            pts.append(tentative)
        if len(pts) < 2:
            self.canvas.update()
            return
        p = QPainter(self.canvas.overlay)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Control polygon
        ctrl_pen = QPen(QColor(150, 150, 200, 180), 1, Qt.PenStyle.DashLine)
        p.setPen(ctrl_pen)
        for i in range(len(pts) - 1):
            p.drawLine(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])

        # Control points
        p.setBrush(QColor("#F38BA8"))
        p.setPen(QPen(QColor("white"), 1))
        for px, py in pts:
            p.drawEllipse(QPoint(px, py), 5, 5)

        # Bezier curve
        curve_pts = bezier_curve(pts, num_steps=300)
        if len(curve_pts) >= 2:
            path = QPainterPath()
            path.moveTo(curve_pts[0][0], curve_pts[0][1])
            for cp in curve_pts[1:]:
                path.lineTo(cp[0], cp[1])
            p.setPen(QPen(self.fg_color, self.brush_size))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        p.end()
        self.canvas.update()

    def _draw_polygon_overlay(self, tentative=None):
        self.canvas.clear_overlay()
        if not self.polygon_points:
            self.canvas.update()
            return
        p = QPainter(self.canvas.overlay)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self.fg_color, self.brush_size)
        p.setPen(pen)

        pts = list(self.polygon_points)
        if tentative:
            pts.append(tentative)
        for i in range(len(pts) - 1):
            p.drawLine(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])

        # Dots at vertices
        p.setBrush(self.fg_color)
        for px, py in self.polygon_points:
            p.drawEllipse(QPoint(px, py), 3, 3)
        p.end()
        self.canvas.update()

    # ----------------------------------------------------------------
    # Mouse Events
    # ----------------------------------------------------------------

    def on_mouse_down(self, event):
        x, y = int(event.position().x()), int(event.position().y())
        pos = QPoint(x, y)
        self.start_pos = pos
        self.prev_pos = pos
        tool = self.current_tool

        if tool == "fill":
            flood_fill(self.canvas.image, x, y, self.fg_color)
            self.canvas.update()
            self._push_undo()

        elif tool == "picker":
            if 0 <= x < self.canvas.img_w and 0 <= y < self.canvas.img_h:
                rgba = self.canvas.image.pixel(x, y)
                self._set_color("fg", QColor(rgba))

        elif tool == "text":
            text, ok = QInputDialog.getText(self, "Text", "Enter text:")
            if ok and text:
                p = QPainter(self.canvas.image)
                p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
                font = QFont("Segoe UI", self.brush_size * 3 + 8)
                p.setFont(font)
                p.setPen(self.fg_color)
                p.drawText(x, y, text)
                p.end()
                self.canvas.update()
                self._push_undo()

        elif tool == "polygon":
            self.polygon_points.append((x, y))
            self._draw_polygon_overlay()

        elif tool == "curve":
            self.bezier_points.append((x, y))
            self._draw_bezier_overlay()
            n = len(self.bezier_points)
            self.sb_hint.setText(
                f"Bézier: {n} control point{'s' if n != 1 else ''} placed  |  Right-click or Double-click to finish"
            )

        # Start mouse tracking for mouse_moved signal
        self.canvas.mouse_moved.emit(x, y)

    def on_mouse_drag(self, event):
        x, y = int(event.position().x()), int(event.position().y())
        tool = self.current_tool
        left_held = bool(event.buttons() & Qt.MouseButton.LeftButton)

        # Bezier and polygon overlays update on any mouse movement (no button needed)
        if tool == "curve":
            self._draw_bezier_overlay(tentative=(x, y))
            self.canvas.mouse_moved.emit(x, y)
            return

        if tool == "polygon" and self.polygon_points:
            self._draw_polygon_overlay(tentative=(x, y))
            self.canvas.mouse_moved.emit(x, y)
            return

        # All other tools require left button held
        if not left_held:
            self.canvas.mouse_moved.emit(x, y)
            return

        # Guard: if prev_pos or start_pos is None, initialise and return
        if self.prev_pos is None:
            self.prev_pos = QPoint(x, y)
            return
        if self.start_pos is None:
            self.start_pos = QPoint(x, y)

        if tool in ("brush", "pencil"):
            px, py = self.prev_pos.x(), self.prev_pos.y()
            self._draw_bresenham(px, py, x, y, self._paint_color(), self.brush_size)
            self.canvas.update()
            self.prev_pos = QPoint(x, y)

        elif tool == "eraser":
            px, py = self.prev_pos.x(), self.prev_pos.y()
            self._draw_bresenham(px, py, x, y, self.bg_color, self.brush_size * 2)
            self.canvas.update()
            self.prev_pos = QPoint(x, y)

        elif tool in ("line", "rectangle", "oval", "circle", "roundrect") and self.start_pos:
            self._draw_preview(x, y)

        elif tool == "curve":
            self._draw_bezier_overlay(tentative=(x, y))

        elif tool == "polygon" and self.polygon_points:
            self._draw_polygon_overlay(tentative=(x, y))

        self.canvas.mouse_moved.emit(x, y)

    def on_mouse_up(self, event):
        x, y = int(event.position().x()), int(event.position().y())
        tool = self.current_tool
        sx = self.start_pos.x() if self.start_pos else x
        sy = self.start_pos.y() if self.start_pos else y
        fill = self.fill_shape

        # Don't clear overlay for bezier/polygon — they need it to persist between clicks
        if tool not in ("curve", "polygon"):
            self.canvas.clear_overlay()

        if tool in ("brush", "pencil", "eraser"):
            self._push_undo()

        elif tool == "line":
            self._draw_bresenham(sx, sy, x, y, self._paint_color(), self.brush_size)
            self.canvas.update()
            self._push_undo()

        elif tool == "rectangle":
            self._draw_rectangle(sx, sy, x, y, self._paint_color(), self.brush_size, fill)
            self.canvas.update()
            self._push_undo()

        elif tool == "oval":
            cx = (sx + x) // 2; cy = (sy + y) // 2
            rx = abs(x - sx) // 2; ry = abs(y - sy) // 2
            self._draw_ellipse_cg(cx, cy, rx, ry, self._paint_color(), self.brush_size, fill)
            self.canvas.update()
            self._push_undo()

        elif tool == "circle":
            radius = int(math.dist((sx, sy), (x, y)))
            self._draw_circle_cg(sx, sy, radius, self._paint_color(), self.brush_size, fill)
            self.canvas.update()
            self._push_undo()

        elif tool == "roundrect":
            self._draw_roundrect(sx, sy, x, y, self._paint_color(), self.brush_size, fill)
            self.canvas.update()
            self._push_undo()

        self.canvas.update()
        self.start_pos = None

    def on_double_click(self, event):
        """Double-click finishes polygon; right-click also works via contextMenu."""
        if self.current_tool == "polygon" and len(self.polygon_points) >= 3:
            self._finish_polygon(close=True)
        elif self.current_tool == "curve" and len(self.bezier_points) >= 2:
            self._finish_bezier(draw=True)

    def on_canvas_right_click(self, event):
        """Right-click on canvas: finish polygon or bezier curve."""
        if self.current_tool == "polygon" and len(self.polygon_points) >= 3:
            self._finish_polygon(close=True)
        elif self.current_tool == "curve" and len(self.bezier_points) >= 2:
            self._finish_bezier(draw=True)
        else:
            # Default right-click: pick bg color
            x = int(event.pos().x())
            y = int(event.pos().y())
            if 0 <= x < self.canvas.img_w and 0 <= y < self.canvas.img_h:
                rgba = self.canvas.image.pixel(x, y)
                self._set_color("bg", QColor(rgba))

    # ----------------------------------------------------------------
    # Polygon / Bezier finalize
    # ----------------------------------------------------------------

    def _finish_polygon(self, close=False):
        if close and len(self.polygon_points) >= 3:
            p = QPainter(self.canvas.image)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(self._paint_color(), self.brush_size)
            p.setPen(pen)
            if self.fill_shape:
                p.setBrush(self._paint_color())
            else:
                p.setBrush(Qt.BrushStyle.NoBrush)
            pts = [QPoint(x, y) for x, y in self.polygon_points]
            p.drawPolygon(*pts)
            p.end()
            self.canvas.update()
            self._push_undo()
        self.canvas.clear_overlay()
        self.polygon_points.clear()
        self.canvas.update()

    def _finish_bezier(self, draw=False):
        if draw and len(self.bezier_points) >= 2:
            curve_pts = bezier_curve(self.bezier_points, num_steps=500)
            color = self._paint_color()
            for i in range(len(curve_pts) - 1):
                self._draw_bresenham(
                    curve_pts[i][0], curve_pts[i][1],
                    curve_pts[i+1][0], curve_pts[i+1][1],
                    color, self.brush_size,
                )
            self.canvas.update()
            self._push_undo()
        self.canvas.clear_overlay()
        self.bezier_points.clear()
        self.canvas.update()
        if self.current_tool == "curve":
            self.sb_hint.setText("Bézier: Left-click to add control points  |  Right-click or Double-click to finish")

    # ----------------------------------------------------------------
    # Status bar update
    # ----------------------------------------------------------------

    def _on_mouse_moved(self, x, y):
        self.sb_pos.setText(f"X: {x}  Y: {y}")

    # ----------------------------------------------------------------
    # Undo / Redo
    # ----------------------------------------------------------------

    def _push_undo(self):
        self.undo_stack.append(self.canvas.image.copy())
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            self.canvas.image = self.undo_stack[-1].copy()
            self.canvas.update()

    def redo(self):
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            self.canvas.image = state.copy()
            self.canvas.update()

    # ----------------------------------------------------------------
    # File Operations
    # ----------------------------------------------------------------

    def new_canvas(self):
        r = QMessageBox.question(self, "New Canvas", "Discard current drawing?")
        if r == QMessageBox.StandardButton.Yes:
            self.canvas.image.fill(QColor("white"))
            self.canvas.update()
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._push_undo()
            self.file_path = None
            self.setWindowTitle("CG-Paint  ·  PyQt6")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All files (*)"
        )
        if not path:
            return
        img = QImage(path)
        if img.isNull():
            QMessageBox.critical(self, "Error", "Could not open file.")
            return
        img = img.convertToFormat(QImage.Format.Format_RGB32)
        self.canvas.img_w = img.width()
        self.canvas.img_h = img.height()
        self.canvas.image = img
        self.canvas.overlay = QImage(img.width(), img.height(), QImage.Format.Format_ARGB32)
        self.canvas.overlay.fill(Qt.GlobalColor.transparent)
        self.canvas.setFixedSize(img.width(), img.height())
        self.canvas.update()
        self.undo_stack.clear(); self.redo_stack.clear(); self._push_undo()
        self.file_path = path
        self.setWindowTitle(f"CG-Paint  ·  {os.path.basename(path)}")
        self.sb_size.setText(f"Canvas: {img.width()} × {img.height()}")

    def save_file(self):
        if self.file_path:
            self.canvas.image.save(self.file_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "",
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;All files (*)"
        )
        if path:
            self.canvas.image.save(path)
            self.file_path = path
            self.setWindowTitle(f"CG-Paint  ·  {os.path.basename(path)}")

    def clear_canvas(self):
        self.canvas.image.fill(QColor("white"))
        self.canvas.update()
        self._push_undo()

    # ----------------------------------------------------------------
    # Image Actions
    # ----------------------------------------------------------------

    def _resize_action(self):
        w, ok1 = QInputDialog.getInt(self, "Resize", "Width:", self.canvas.img_w, 1, 9999)
        if not ok1: return
        h, ok2 = QInputDialog.getInt(self, "Resize", "Height:", self.canvas.img_h, 1, 9999)
        if not ok2: return
        new_img = QImage(w, h, QImage.Format.Format_RGB32)
        new_img.fill(QColor("white"))
        p = QPainter(new_img)
        p.drawImage(0, 0, self.canvas.image)
        p.end()
        self.canvas.img_w = w; self.canvas.img_h = h
        self.canvas.image = new_img
        self.canvas.overlay = QImage(w, h, QImage.Format.Format_ARGB32)
        self.canvas.overlay.fill(Qt.GlobalColor.transparent)
        self.canvas.setFixedSize(w, h)
        self.canvas.update()
        self._push_undo()
        self.sb_size.setText(f"Canvas: {w} × {h}")

    def _rotate_action(self):
        angle, ok = QInputDialog.getInt(self, "Rotate", "Angle (degrees):", 90, -360, 360)
        if not ok: return
        transform = self.canvas.image.transformed(
            __import__("PyQt6.QtGui", fromlist=["QTransform"]).QTransform().rotate(angle)
        )
        self.canvas.img_w = transform.width()
        self.canvas.img_h = transform.height()
        self.canvas.image = transform
        self.canvas.overlay = QImage(transform.width(), transform.height(), QImage.Format.Format_ARGB32)
        self.canvas.overlay.fill(Qt.GlobalColor.transparent)
        self.canvas.setFixedSize(transform.width(), transform.height())
        self.canvas.update()
        self._push_undo()
        self.sb_size.setText(f"Canvas: {transform.width()} × {transform.height()}")

    def _help_dialog(self):
        QMessageBox.information(self, "Help — CG-Paint (PyQt6)",
            "CG-Paint — Computer Graphics Paint App\n\n"
            "All algorithms are implemented from scratch:\n"
            "• Bresenham's line  • Midpoint Circle\n"
            "• Midpoint Ellipse  • Flood Fill (BFS)\n"
            "• Bézier (De Casteljau)\n\n"
            "Shortcuts:\n"
            "Ctrl+Z = Undo   Ctrl+Y = Redo\n"
            "Ctrl+S = Save   Ctrl+O = Open\n"
            "Ctrl+N = New    Ctrl+Q = Quit\n\n"
            "Tips:\n"
            "• Polygon: click points, double-click or right-click to close\n"
            "• Bézier: click control points, double-click or right-click to finish\n"
            "• Left-click palette = foreground\n"
            "• Right-click palette = background"
        )


# ======================== Entry Point ========================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = CGPaintQt()
    window.show()
    sys.exit(app.exec())