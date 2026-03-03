import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox, simpledialog, font as tkfont
from PIL import Image, ImageDraw, ImageTk, ImageFont
import math
import os


# ======================== CG Algorithms ========================

def bresenham_line(x1, y1, x2, y2):
    """Bresenham's line drawing algorithm."""
    points = []
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    while True:
        points.append((x1, y1))
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy
    return points


def midpoint_circle(cx, cy, r):
    """Midpoint circle drawing algorithm."""
    points = []
    x, y = 0, r
    d = 1 - r
    while x <= y:
        for dx, dy in [(x, y), (y, x), (-x, y), (-y, x),
                        (x, -y), (y, -x), (-x, -y), (-y, -x)]:
            points.append((cx + dx, cy + dy))
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1
    return points


def midpoint_ellipse(cx, cy, rx, ry):
    """Midpoint ellipse drawing algorithm."""
    points = []
    if rx == 0 or ry == 0:
        return points
    rx2, ry2 = rx * rx, ry * ry
    x, y = 0, ry
    # Region 1
    d1 = ry2 - rx2 * ry + 0.25 * rx2
    dx = 2 * ry2 * x
    dy = 2 * rx2 * y
    while dx < dy:
        for sx, sy in [(x, y), (-x, y), (x, -y), (-x, -y)]:
            points.append((cx + sx, cy + sy))
        x += 1
        dx += 2 * ry2
        if d1 < 0:
            d1 += dx + ry2
        else:
            y -= 1
            dy -= 2 * rx2
            d1 += dx - dy + ry2
    # Region 2
    d2 = ry2 * (x + 0.5) ** 2 + rx2 * (y - 1) ** 2 - rx2 * ry2
    while y >= 0:
        for sx, sy in [(x, y), (-x, y), (x, -y), (-x, -y)]:
            points.append((cx + sx, cy + sy))
        y -= 1
        dy -= 2 * rx2
        if d2 > 0:
            d2 += rx2 - dy
        else:
            x += 1
            dx += 2 * ry2
            d2 += dx - dy + rx2
    return points


def flood_fill(image, x, y, fill_color):
    """Flood fill (bucket) using BFS on a PIL Image."""
    w, h = image.size
    pixels = image.load()
    if x < 0 or x >= w or y < 0 or y >= h:
        return
    target_color = pixels[x, y]
    if target_color == fill_color:
        return
    stack = [(x, y)]
    visited = set()
    while stack:
        cx, cy = stack.pop()
        if (cx, cy) in visited:
            continue
        if cx < 0 or cx >= w or cy < 0 or cy >= h:
            continue
        if pixels[cx, cy] != target_color:
            continue
        visited.add((cx, cy))
        pixels[cx, cy] = fill_color
        stack.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])


def bezier_curve(control_points, num_steps=500):
    """Compute points on a Bezier curve using De Casteljau's algorithm."""
    if len(control_points) < 2:
        return []
    points = []
    n = len(control_points) - 1
    for i in range(num_steps + 1):
        t = i / num_steps
        # De Casteljau's algorithm
        temp = list(control_points)
        for k in range(n):
            temp = [
                (
                    (1 - t) * temp[j][0] + t * temp[j + 1][0],
                    (1 - t) * temp[j][1] + t * temp[j + 1][1],
                )
                for j in range(len(temp) - 1)
            ]
        px, py = int(round(temp[0][0])), int(round(temp[0][1]))
        if not points or points[-1] != (px, py):
            points.append((px, py))
    return points


# ======================== Paint Application ========================

# --- Light UI Theme (matching reference design) ---
THEME = {
    "bg": "#E8E8E8",
    "panel_bg": "#F5F5F5",
    "panel_inner": "#FFFFFF",
    "header_bg": "#EAEAEA",
    "header_fg": "#444444",
    "text": "#333333",
    "text_light": "#777777",
    "border": "#CCCCCC",
    "btn_bg": "#EEEEEE",
    "btn_fg": "#333333",
    "btn_active_bg": "#D4E4F7",
    "btn_active_fg": "#1A1A1A",
    "green": "#5CB85C",
    "green_fg": "#FFFFFF",
    "status_bg": "#ECECEC",
    "status_fg": "#555555",
    "toolbar_bg": "#F5F5F5",
    "sidebar_bg": "#F0F0F0",
    "canvas_surround": "#C8C8C8",
    "accent": "#5B9BD5",
    "layer_green": "#5CB85C",
}

COLORS = [
    "#000000", "#434343", "#800000", "#808000",
    "#008000", "#008080", "#000080", "#800080",
    "#FFFFFF", "#C0C0C0", "#FF0000", "#FFFF00",
    "#00FF00", "#00FFFF", "#0000FF", "#FF00FF",
    "#FF8C00", "#FFD700", "#7CFC00", "#40E0D0",
    "#1E90FF", "#BA55D3", "#FF69B4", "#A0522D",
]

# Secondary toolbar quick-access items
QUICK_TOOLS = [
    ("\u25ad", "rectangle"), ("\u2571", "line"), ("\u25cb", "circle"),
    ("\u2b2d", "oval"), ("\u25a2", "roundrect"), ("\u2b21", "polygon"),
    ("\u223f", "curve"), ("\u270f", "pencil"), ("\U0001f58c", "brush"),
]


class CGPaint:
    def __init__(self, root):
        self.root = root
        self.root.title("CG-Paint")
        self.root.geometry("1200x750")
        self.root.minsize(900, 650)
        self.root.configure(bg=THEME["bg"])

        # State
        self.canvas_width = 800
        self.canvas_height = 600
        self.current_tool = "brush"
        self.fg_color = "#000000"
        self.bg_color = "#FFFFFF"
        self.brush_size = 10
        self.opacity = 100
        self.fill_shape = False
        self.start_x = self.start_y = None
        self.prev_x = self.prev_y = None
        self.preview_id = None
        self.polygon_points = []
        self.polygon_preview_ids = []
        self.bezier_points = []
        self.bezier_preview_ids = []
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo = 30
        self.file_path = None
        self.mouse_x = 0
        self.mouse_y = 0

        # Layers (visual + basic functionality)
        self.layers = [
            {"name": "Background", "visible": False},
            {"name": "Layer 1", "visible": True},
            {"name": "Layer 2", "visible": True},
        ]
        self.layer_counter = 2

        # PIL backing image
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)

        self._build_ui()
        self._sync_canvas()
        self._push_undo()
        self._update_status()

    # ================================================================
    #                       UI CONSTRUCTION
    # ================================================================

    def _build_ui(self):
        # ---- Menu Bar ----
        self._build_menu_bar()

        # ---- Top Action Bar ----
        self._build_action_bar()

        # ---- Secondary Toolbar ----
        self._build_secondary_toolbar()

        # ---- Status Bar (pack first so it's at bottom) ----
        self._build_status_bar()

        # ---- Main Content Area ----
        self.content = tk.Frame(self.root, bg=THEME["bg"])
        self.content.pack(fill="both", expand=True)

        # Left sidebar
        self._build_left_sidebar(self.content)

        # Right sidebar
        self._build_right_sidebar(self.content)

        # Center canvas
        self._build_canvas_area(self.content)

        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self.new_canvas())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())

    # ----------------------------------------------------------------
    #  Menu Bar
    # ----------------------------------------------------------------

    def _build_menu_bar(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New           Ctrl+N", command=self.new_canvas)
        file_menu.add_command(label="Open...      Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save           Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo   Ctrl+Z", command=self.undo)
        edit_menu.add_command(label="Redo   Ctrl+Y", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear Canvas", command=self.clear_canvas)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        image_menu = tk.Menu(menubar, tearoff=0)
        image_menu.add_command(label="Resize Canvas...", command=self.resize_canvas_dialog)
        menubar.add_cascade(label="Image", menu=image_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Brush", command=lambda: self._select_tool("brush"))
        tools_menu.add_command(label="Pencil", command=lambda: self._select_tool("pencil"))
        tools_menu.add_command(label="Eraser", command=lambda: self._select_tool("eraser"))
        tools_menu.add_command(label="Fill", command=lambda: self._select_tool("fill"))
        tools_menu.add_separator()
        tools_menu.add_command(label="Line", command=lambda: self._select_tool("line"))
        tools_menu.add_command(label="Rectangle", command=lambda: self._select_tool("rectangle"))
        tools_menu.add_command(label="Oval", command=lambda: self._select_tool("oval"))
        tools_menu.add_command(label="Circle", command=lambda: self._select_tool("circle"))
        tools_menu.add_command(label="Rounded Rect", command=lambda: self._select_tool("roundrect"))
        tools_menu.add_command(label="Polygon", command=lambda: self._select_tool("polygon"))
        tools_menu.add_command(label="Bezier Curve", command=lambda: self._select_tool("curve"))
        tools_menu.add_separator()
        tools_menu.add_command(label="Text", command=lambda: self._select_tool("text"))
        tools_menu.add_command(label="Color Picker", command=lambda: self._select_tool("picker"))
        menubar.add_cascade(label="Tools", menu=tools_menu)

        self.root.config(menu=menubar)

    # ----------------------------------------------------------------
    #  Action Bar (Crop, Resize, Rotate, Effects, Help, Save)
    # ----------------------------------------------------------------

    def _build_action_bar(self):
        bar = tk.Frame(self.root, bg=THEME["toolbar_bg"], height=40)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Bottom border line
        tk.Frame(bar, height=1, bg=THEME["border"]).pack(side="bottom", fill="x")

        inner = tk.Frame(bar, bg=THEME["toolbar_bg"])
        inner.pack(fill="both", expand=True, padx=6)

        # Right side: green Save button
        save_btn = tk.Button(
            inner, text="\U0001f4be Save", font=("Segoe UI", 10, "bold"),
            bg=THEME["green"], fg=THEME["green_fg"],
            activebackground="#449D44", activeforeground="#FFFFFF",
            relief="flat", bd=0, padx=18, pady=3, cursor="hand2",
            command=self.save_file,
        )
        save_btn.pack(side="right", padx=(8, 4), pady=5)

        # Action buttons
        actions = [
            ("# Crop", self._crop_action),
            ("\u270e Resize", self.resize_canvas_dialog),
            ("\u21bb Rotate", self._rotate_action),
            ("\u2728 Effects", self._effects_action),
            ("? Help", self._help_dialog),
        ]
        for text, cmd in actions:
            btn = tk.Button(
                inner, text=text, font=("Segoe UI", 9),
                bg=THEME["toolbar_bg"], fg=THEME["text"],
                activebackground=THEME["btn_active_bg"],
                relief="flat", bd=0, padx=10, pady=2, cursor="hand2",
                command=cmd,
            )
            btn.pack(side="left", padx=3, pady=5)

    # ----------------------------------------------------------------
    #  Secondary Toolbar (quick tool icons, undo/redo, fill toggle)
    # ----------------------------------------------------------------

    def _build_secondary_toolbar(self):
        bar = tk.Frame(self.root, bg=THEME["bg"], height=36)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Frame(bar, height=1, bg=THEME["border"]).pack(side="bottom", fill="x")

        inner = tk.Frame(bar, bg=THEME["bg"])
        inner.pack(fill="both", expand=True, padx=6)

        self.quick_buttons = {}
        for symbol, tool_id in QUICK_TOOLS:
            btn = tk.Button(
                inner, text=symbol, font=("Segoe UI", 11),
                bg=THEME["btn_bg"], fg=THEME["btn_fg"],
                activebackground=THEME["btn_active_bg"],
                relief="flat", bd=0, width=3, height=1, cursor="hand2",
                command=lambda t=tool_id: self._select_tool(t),
            )
            btn.pack(side="left", padx=1, pady=3)
            self.quick_buttons[tool_id] = btn

        # Separator
        tk.Frame(inner, width=2, bg=THEME["border"]).pack(side="left", fill="y", padx=6, pady=5)

        # Fill checkbox
        self.fill_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            inner, text="Fill", variable=self.fill_var,
            font=("Segoe UI", 8), command=self._on_fill_toggle,
            bg=THEME["bg"], fg=THEME["text"],
            activebackground=THEME["bg"],
        ).pack(side="left", padx=4)

        # Separator
        tk.Frame(inner, width=2, bg=THEME["border"]).pack(side="left", fill="y", padx=6, pady=5)

        # Undo / Redo
        tk.Button(
            inner, text="\u25c0", font=("Segoe UI", 10), bg=THEME["btn_bg"], fg=THEME["btn_fg"],
            relief="flat", bd=0, width=3, cursor="hand2", command=self.undo,
        ).pack(side="left", padx=1, pady=3)
        tk.Button(
            inner, text="\u25b6", font=("Segoe UI", 10), bg=THEME["btn_bg"], fg=THEME["btn_fg"],
            relief="flat", bd=0, width=3, cursor="hand2", command=self.redo,
        ).pack(side="left", padx=1, pady=3)

        # Right side: horizontal size slider indicator
        tk.Frame(inner, width=2, bg=THEME["border"]).pack(side="left", fill="y", padx=6, pady=5)
        self.toolbar_size_scale = tk.Scale(
            inner, from_=1, to=40, orient="horizontal",
            variable=tk.IntVar(value=self.brush_size),
            command=self._on_toolbar_size_change,
            showvalue=False, length=180,
            bg=THEME["bg"], fg=THEME["text"],
            troughcolor="#D0D0D0", highlightthickness=0,
            activebackground=THEME["accent"], sliderrelief="flat",
        )
        self.toolbar_size_scale.pack(side="left", padx=4, pady=3)

    # ----------------------------------------------------------------
    #  Left Sidebar (Tool Buttons)
    # ----------------------------------------------------------------

    def _build_left_sidebar(self, parent):
        sidebar = tk.Frame(parent, width=130, bg=THEME["sidebar_bg"])
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Right border
        border_line = tk.Frame(sidebar, width=1, bg=THEME["border"])
        border_line.pack(side="right", fill="y")

        inner = tk.Frame(sidebar, bg=THEME["sidebar_bg"])
        inner.pack(fill="both", expand=True)

        self.tool_buttons = {}
        tools = [
            ("\U0001f58c", "Brush", "brush"),
            ("\u2312", "Eraser", "eraser"),
            ("\u25d5", "Fill", "fill"),
            ("\u25f0", "Shapes", "shapes"),
            ("A", "Text", "text"),
            ("\u2b1a", "Select", "picker"),
        ]

        for icon, label, tool_id in tools:
            btn = tk.Button(
                inner, text=f"  {icon}  {label}", font=("Segoe UI", 10),
                bg=THEME["btn_bg"], fg=THEME["btn_fg"],
                activebackground=THEME["btn_active_bg"], activeforeground=THEME["btn_active_fg"],
                relief="flat", bd=0, anchor="w", padx=8, pady=7, cursor="hand2",
                command=lambda t=tool_id: self._on_sidebar_tool(t),
            )
            btn.pack(fill="x", padx=6, pady=2)
            self.tool_buttons[tool_id] = btn

        self._highlight_tool()

        # Spacer
        tk.Frame(inner, bg=THEME["sidebar_bg"]).pack(fill="both", expand=True)

        # Bottom: FG color swatch + magnifier
        bottom = tk.Frame(inner, bg=THEME["sidebar_bg"])
        bottom.pack(fill="x", padx=10, pady=10)

        self.fg_swatch_large = tk.Label(
            bottom, bg=self.fg_color, width=4, height=2,
            relief="solid", bd=2, cursor="hand2",
        )
        self.fg_swatch_large.pack(side="left")
        self.fg_swatch_large.bind("<Button-1>", lambda e: self._pick_custom_color("fg"))

        tk.Label(
            bottom, text="\U0001f50d", font=("Segoe UI", 16),
            bg=THEME["sidebar_bg"], fg=THEME["text_light"], cursor="hand2",
        ).pack(side="left", padx=12)

    # ----------------------------------------------------------------
    #  Right Sidebar (Color Palette, Brush Settings, Layers)
    # ----------------------------------------------------------------

    def _build_right_sidebar(self, parent):
        sidebar = tk.Frame(parent, width=230, bg=THEME["panel_bg"])
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)

        # Left border
        border_line = tk.Frame(sidebar, width=1, bg=THEME["border"])
        border_line.pack(side="left", fill="y")

        inner = tk.Frame(sidebar, bg=THEME["panel_bg"])
        inner.pack(fill="both", expand=True)

        # ---- Color Palette Panel ----
        self._build_color_palette_panel(inner)

        # ---- Brush Settings Panel ----
        self._build_brush_settings_panel(inner)

        # ---- Layers Panel ----
        self._build_layers_panel(inner)

    def _build_color_palette_panel(self, parent):
        # Header
        header = tk.Frame(parent, bg=THEME["header_bg"])
        header.pack(fill="x")
        tk.Frame(header, height=1, bg=THEME["border"]).pack(side="top", fill="x")
        header_inner = tk.Frame(header, bg=THEME["header_bg"])
        header_inner.pack(fill="x", padx=8, pady=5)
        tk.Label(
            header_inner, text="Color Palette", font=("Segoe UI", 10, "bold"),
            bg=THEME["header_bg"], fg=THEME["header_fg"],
        ).pack(side="left")
        tk.Label(
            header_inner, text="\u2296", font=("Segoe UI", 12),
            bg=THEME["header_bg"], fg=THEME["text_light"], cursor="hand2",
        ).pack(side="right")
        tk.Frame(header, height=1, bg=THEME["border"]).pack(side="bottom", fill="x")

        # Body
        body = tk.Frame(parent, bg=THEME["panel_inner"])
        body.pack(fill="x")

        # Rainbow gradient bar
        gradient_frame = tk.Frame(body, bg=THEME["panel_inner"])
        gradient_frame.pack(fill="x", padx=10, pady=(10, 6))
        self.gradient_canvas = tk.Canvas(
            gradient_frame, height=20, bg="#FFFFFF",
            highlightthickness=1, highlightbackground=THEME["border"],
            cursor="hand2",
        )
        self.gradient_canvas.pack(fill="x")
        self.gradient_canvas.bind("<Configure>", self._draw_gradient)
        self.gradient_canvas.bind("<Button-1>", self._pick_gradient_color)

        # Color swatches grid (3 rows x 8 cols)
        swatch_frame = tk.Frame(body, bg=THEME["panel_inner"])
        swatch_frame.pack(padx=10, pady=4)
        for i, color in enumerate(COLORS):
            swatch = tk.Label(
                swatch_frame, bg=color, width=2, height=1,
                relief="solid", bd=1, cursor="hand2",
            )
            swatch.grid(row=i // 8, column=i % 8, padx=1, pady=1)
            swatch.bind("<Button-1>", lambda e, c=color: self._set_color("fg", c))
            swatch.bind("<Button-3>", lambda e, c=color: self._set_color("bg", c))

        # Edit Colors button
        tk.Button(
            body, text="Edit Colors", font=("Segoe UI", 9),
            bg=THEME["btn_bg"], fg=THEME["text"],
            activebackground=THEME["btn_active_bg"],
            relief="solid", bd=1, padx=16, pady=3, cursor="hand2",
            command=lambda: self._pick_custom_color("fg"),
        ).pack(pady=(6, 10))

        tk.Frame(body, height=1, bg=THEME["border"]).pack(fill="x")

    def _build_brush_settings_panel(self, parent):
        # Header
        header = tk.Frame(parent, bg=THEME["header_bg"])
        header.pack(fill="x")
        header_inner = tk.Frame(header, bg=THEME["header_bg"])
        header_inner.pack(fill="x", padx=8, pady=5)
        tk.Label(
            header_inner, text="Brush Settings", font=("Segoe UI", 10, "bold"),
            bg=THEME["header_bg"], fg=THEME["header_fg"],
        ).pack(side="left")
        tk.Label(
            header_inner, text="\u2296", font=("Segoe UI", 12),
            bg=THEME["header_bg"], fg=THEME["text_light"], cursor="hand2",
        ).pack(side="right")
        tk.Frame(header, height=1, bg=THEME["border"]).pack(side="bottom", fill="x")

        # Body
        body = tk.Frame(parent, bg=THEME["panel_inner"])
        body.pack(fill="x")

        # Size row
        size_row = tk.Frame(body, bg=THEME["panel_inner"])
        size_row.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(
            size_row, text="Size", font=("Segoe UI", 9),
            bg=THEME["panel_inner"], fg=THEME["text"],
        ).pack(side="left")
        self.size_value_label = tk.Label(
            size_row, text=str(self.brush_size), font=("Segoe UI", 9, "bold"),
            bg=THEME["panel_inner"], fg=THEME["text"], width=4, anchor="e",
        )
        self.size_value_label.pack(side="right")

        self.size_var = tk.IntVar(value=self.brush_size)
        self.size_scale = tk.Scale(
            size_row, from_=1, to=40, orient="horizontal",
            variable=self.size_var, command=self._on_size_change,
            showvalue=False, length=110,
            bg=THEME["panel_inner"], fg=THEME["text"],
            troughcolor="#D8D8D8", highlightthickness=0,
            activebackground=THEME["accent"], sliderrelief="flat",
        )
        self.size_scale.pack(side="right", padx=(8, 4))

        # Opacity row
        opacity_row = tk.Frame(body, bg=THEME["panel_inner"])
        opacity_row.pack(fill="x", padx=10, pady=(4, 10))
        tk.Label(
            opacity_row, text="Opacity", font=("Segoe UI", 9),
            bg=THEME["panel_inner"], fg=THEME["text"],
        ).pack(side="left")
        self.opacity_value_label = tk.Label(
            opacity_row, text=f"{self.opacity}%", font=("Segoe UI", 9, "bold"),
            bg=THEME["panel_inner"], fg=THEME["text"], width=4, anchor="e",
        )
        self.opacity_value_label.pack(side="right")

        self.opacity_var = tk.IntVar(value=self.opacity)
        opacity_scale = tk.Scale(
            opacity_row, from_=0, to=100, orient="horizontal",
            variable=self.opacity_var, command=self._on_opacity_change,
            showvalue=False, length=110,
            bg=THEME["panel_inner"], fg=THEME["text"],
            troughcolor="#D8D8D8", highlightthickness=0,
            activebackground=THEME["accent"], sliderrelief="flat",
        )
        opacity_scale.pack(side="right", padx=(8, 4))

        tk.Frame(body, height=1, bg=THEME["border"]).pack(fill="x")

    def _build_layers_panel(self, parent):
        # Header
        header = tk.Frame(parent, bg=THEME["header_bg"])
        header.pack(fill="x")
        header_inner = tk.Frame(header, bg=THEME["header_bg"])
        header_inner.pack(fill="x", padx=8, pady=5)
        tk.Label(
            header_inner, text="Layers", font=("Segoe UI", 10, "bold"),
            bg=THEME["header_bg"], fg=THEME["header_fg"],
        ).pack(side="left")
        tk.Label(
            header_inner, text="\u26a0", font=("Segoe UI", 10),
            bg=THEME["header_bg"], fg=THEME["text_light"],
        ).pack(side="right")
        tk.Frame(header, height=1, bg=THEME["border"]).pack(side="bottom", fill="x")

        # Body
        self.layers_body = tk.Frame(parent, bg=THEME["panel_inner"])
        self.layers_body.pack(fill="both", expand=True)

        self._rebuild_layers_ui()

    def _rebuild_layers_ui(self):
        for w in self.layers_body.winfo_children():
            w.destroy()

        layer_list = tk.Frame(self.layers_body, bg=THEME["panel_inner"])
        layer_list.pack(fill="x", padx=6, pady=6)

        self.layer_vars = []
        for i, layer in enumerate(self.layers):
            row = tk.Frame(layer_list, bg=THEME["panel_inner"])
            row.pack(fill="x", pady=2)

            var = tk.BooleanVar(value=layer["visible"])
            self.layer_vars.append(var)

            cb = tk.Checkbutton(
                row, variable=var,
                bg=THEME["panel_inner"], activebackground=THEME["panel_inner"],
                command=lambda idx=i: self._toggle_layer_visibility(idx),
            )
            cb.pack(side="left", padx=(4, 0))

            name_label = tk.Label(
                row, text=layer["name"], font=("Segoe UI", 9),
                bg=THEME["panel_inner"], fg=THEME["text"], anchor="w",
            )
            name_label.pack(side="left", fill="x", expand=True, padx=4)

            # Green indicator for visible non-background layers
            if layer["visible"] and layer["name"] != "Background":
                indicator = tk.Label(
                    row, bg=THEME["layer_green"], width=2, height=1,
                    relief="solid", bd=1,
                )
                indicator.pack(side="right", padx=6)

        # + Add Layer button
        add_btn = tk.Button(
            self.layers_body, text="+ Add Layer", font=("Segoe UI", 9),
            bg=THEME["btn_bg"], fg=THEME["text"],
            activebackground=THEME["btn_active_bg"],
            relief="solid", bd=1, padx=16, pady=4, cursor="hand2",
            command=self._add_layer,
        )
        add_btn.pack(pady=(4, 10))

    # ----------------------------------------------------------------
    #  Canvas Area
    # ----------------------------------------------------------------

    def _build_canvas_area(self, parent):
        canvas_frame = tk.Frame(parent, bg=THEME["canvas_surround"], relief="flat", bd=2)
        canvas_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.h_scroll = tk.Scrollbar(canvas_frame, orient="horizontal")
        self.v_scroll = tk.Scrollbar(canvas_frame, orient="vertical")
        self.canvas = tk.Canvas(
            canvas_frame, bg="#C0C0C0",
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set,
            cursor="cross",
        )
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))

        # Mouse bindings
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)

    # ----------------------------------------------------------------
    #  Status Bar (3 sections)
    # ----------------------------------------------------------------

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=THEME["status_bg"], height=28)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)

        tk.Frame(bar, height=1, bg=THEME["border"]).pack(side="top", fill="x")

        self.status_canvas_size = tk.Label(
            bar, text=f"Canvas Size: {self.canvas_width} \u00d7 {self.canvas_height} px",
            font=("Segoe UI", 9), bg=THEME["status_bg"], fg=THEME["status_fg"],
            anchor="w", padx=16,
        )
        self.status_canvas_size.pack(side="left")

        tk.Frame(bar, width=1, bg=THEME["border"]).pack(side="left", fill="y", pady=4)

        self.status_zoom = tk.Label(
            bar, text="Zoom: 100%",
            font=("Segoe UI", 9), bg=THEME["status_bg"], fg=THEME["status_fg"],
            anchor="center", padx=24,
        )
        self.status_zoom.pack(side="left")

        tk.Frame(bar, width=1, bg=THEME["border"]).pack(side="left", fill="y", pady=4)

        self.status_position = tk.Label(
            bar, text="Position: X: 0, Y: 0",
            font=("Segoe UI", 9), bg=THEME["status_bg"], fg=THEME["status_fg"],
            anchor="w", padx=24,
        )
        self.status_position.pack(side="left", fill="x", expand=True)

    # ================================================================
    #                     GRADIENT & COLOR HELPERS
    # ================================================================

    def _draw_gradient(self, event=None):
        """Draw rainbow gradient on the gradient canvas."""
        w = self.gradient_canvas.winfo_width()
        h = self.gradient_canvas.winfo_height()
        if w <= 1:
            return
        self.gradient_canvas.delete("all")
        colors_seq = [
            (255, 0, 0), (255, 165, 0), (255, 255, 0), (0, 255, 0),
            (0, 255, 255), (0, 0, 255), (128, 0, 255), (255, 0, 255), (255, 0, 0),
        ]
        segments = len(colors_seq) - 1
        for x in range(w):
            t = x / max(1, w - 1) * segments
            idx = min(int(t), segments - 1)
            frac = t - idx
            r = int(colors_seq[idx][0] * (1 - frac) + colors_seq[idx + 1][0] * frac)
            g = int(colors_seq[idx][1] * (1 - frac) + colors_seq[idx + 1][1] * frac)
            b = int(colors_seq[idx][2] * (1 - frac) + colors_seq[idx + 1][2] * frac)
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.gradient_canvas.create_line(x, 0, x, h, fill=color)

    def _pick_gradient_color(self, event):
        """Pick color from the gradient bar."""
        w = self.gradient_canvas.winfo_width()
        if w <= 1:
            return
        colors_seq = [
            (255, 0, 0), (255, 165, 0), (255, 255, 0), (0, 255, 0),
            (0, 255, 255), (0, 0, 255), (128, 0, 255), (255, 0, 255), (255, 0, 0),
        ]
        segments = len(colors_seq) - 1
        t = max(0, min(event.x, w - 1)) / max(1, w - 1) * segments
        idx = min(int(t), segments - 1)
        frac = t - idx
        r = int(colors_seq[idx][0] * (1 - frac) + colors_seq[idx + 1][0] * frac)
        g = int(colors_seq[idx][1] * (1 - frac) + colors_seq[idx + 1][1] * frac)
        b = int(colors_seq[idx][2] * (1 - frac) + colors_seq[idx + 1][2] * frac)
        color = f"#{r:02x}{g:02x}{b:02x}"
        self._set_color("fg", color)

    # ================================================================
    #                     TOOL SELECTION
    # ================================================================

    def _on_sidebar_tool(self, tool_id):
        """Handle sidebar tool button clicks. 'shapes' shows a popup menu."""
        if tool_id == "shapes":
            self._show_shapes_menu()
        else:
            self._select_tool(tool_id)

    def _show_shapes_menu(self):
        """Show popup menu for shape tools."""
        menu = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 9))
        shapes = [
            ("Line", "line"), ("Rectangle", "rectangle"), ("Oval", "oval"),
            ("Circle", "circle"), ("Rounded Rect", "roundrect"),
            ("Polygon", "polygon"), ("Bezier Curve", "curve"),
        ]
        for label, tool_id in shapes:
            menu.add_command(label=label, command=lambda t=tool_id: self._select_tool(t))
        btn = self.tool_buttons.get("shapes")
        if btn:
            x = btn.winfo_rootx() + btn.winfo_width()
            y = btn.winfo_rooty()
            menu.tk_popup(x, y)

    def _select_tool(self, tool_id):
        self._finish_polygon()
        self._finish_bezier()
        self.current_tool = tool_id
        self._highlight_tool()
        cursors = {
            "pencil": "pencil", "brush": "circle", "eraser": "circle",
            "line": "cross", "rectangle": "cross", "oval": "cross",
            "circle": "cross", "roundrect": "cross", "polygon": "cross",
            "curve": "cross", "fill": "cross", "text": "xterm", "picker": "crosshair",
        }
        self.canvas.config(cursor=cursors.get(tool_id, "cross"))

    def _highlight_tool(self):
        """Highlight the active tool in both sidebar and quick toolbar."""
        shape_tools = {"line", "rectangle", "oval", "circle", "roundrect", "polygon", "curve"}
        sidebar_active = self.current_tool
        if self.current_tool in ("pencil", "brush"):
            sidebar_active = "brush"
        elif self.current_tool in shape_tools:
            sidebar_active = "shapes"

        for tid, btn in self.tool_buttons.items():
            if tid == sidebar_active:
                btn.config(bg=THEME["btn_active_bg"], fg=THEME["btn_active_fg"])
            else:
                btn.config(bg=THEME["btn_bg"], fg=THEME["btn_fg"])

        for tid, btn in self.quick_buttons.items():
            if tid == self.current_tool:
                btn.config(bg=THEME["btn_active_bg"])
            else:
                btn.config(bg=THEME["btn_bg"])

    # ================================================================
    #                     CANVAS SYNC
    # ================================================================

    def _sync_canvas(self):
        """Update the tk Canvas from the PIL image."""
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.delete("img")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image, tags="img")
        self.canvas.tag_lower("img")

    def _canvas_coords(self, event):
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        return x, y

    def _update_status(self):
        self.status_canvas_size.config(
            text=f"Canvas Size: {self.canvas_width} \u00d7 {self.canvas_height} px"
        )
        self.status_position.config(
            text=f"Position: X: {self.mouse_x}, Y: {self.mouse_y}"
        )

    # ================================================================
    #                   DRAWING ON PIL IMAGE
    # ================================================================

    def _draw_bresenham_line(self, x1, y1, x2, y2, color, thickness=1):
        points = bresenham_line(x1, y1, x2, y2)
        r = max(0, thickness // 2)
        for px, py in points:
            if r <= 1:
                if 0 <= px < self.canvas_width and 0 <= py < self.canvas_height:
                    self.draw.point((px, py), fill=color)
            else:
                self.draw.ellipse(
                    (px - r, py - r, px + r, py + r), fill=color,
                )

    def _draw_circle_cg(self, cx, cy, radius, color, thickness=1, fill_color=None):
        if fill_color:
            self.draw.ellipse(
                (cx - radius, cy - radius, cx + radius, cy + radius),
                fill=fill_color, outline=color, width=thickness,
            )
        else:
            points = midpoint_circle(cx, cy, radius)
            r = max(0, thickness // 2)
            for px, py in points:
                if r <= 1:
                    if 0 <= px < self.canvas_width and 0 <= py < self.canvas_height:
                        self.draw.point((px, py), fill=color)
                else:
                    self.draw.ellipse((px - r, py - r, px + r, py + r), fill=color)

    def _draw_ellipse_cg(self, cx, cy, rx, ry, color, thickness=1, fill_color=None):
        if fill_color:
            self.draw.ellipse(
                (cx - rx, cy - ry, cx + rx, cy + ry),
                fill=fill_color, outline=color, width=thickness,
            )
        else:
            points = midpoint_ellipse(cx, cy, rx, ry)
            r = max(0, thickness // 2)
            for px, py in points:
                if r <= 1:
                    if 0 <= px < self.canvas_width and 0 <= py < self.canvas_height:
                        self.draw.point((px, py), fill=color)
                else:
                    self.draw.ellipse((px - r, py - r, px + r, py + r), fill=color)

    def _draw_rectangle(self, x1, y1, x2, y2, color, thickness=1, fill_color=None):
        if fill_color:
            self.draw.rectangle((x1, y1, x2, y2), fill=fill_color, outline=color, width=thickness)
        else:
            self.draw.rectangle((x1, y1, x2, y2), outline=color, width=thickness)

    def _draw_roundrect(self, x1, y1, x2, y2, color, thickness=1, fill_color=None, radius=15):
        if fill_color:
            self.draw.rounded_rectangle((x1, y1, x2, y2), radius=radius,
                                        fill=fill_color, outline=color, width=thickness)
        else:
            self.draw.rounded_rectangle((x1, y1, x2, y2), radius=radius,
                                        outline=color, width=thickness)

    # ================================================================
    #                     MOUSE HANDLERS
    # ================================================================

    def on_mouse_down(self, event):
        x, y = self._canvas_coords(event)
        self.start_x, self.start_y = x, y
        self.prev_x, self.prev_y = x, y

        tool = self.current_tool

        if tool == "fill":
            color_rgb = self._hex_to_rgb(self.fg_color)
            flood_fill(self.image, x, y, color_rgb)
            self.draw = ImageDraw.Draw(self.image)
            self._sync_canvas()
            self._push_undo()

        elif tool == "picker":
            if 0 <= x < self.canvas_width and 0 <= y < self.canvas_height:
                r, g, b = self.image.getpixel((x, y))[:3]
                color = f"#{r:02x}{g:02x}{b:02x}"
                self._set_color("fg", color)

        elif tool == "text":
            text = simpledialog.askstring("Text", "Enter text:", parent=self.root)
            if text:
                try:
                    fnt = ImageFont.truetype("arial.ttf", self.brush_size * 4 + 8)
                except:
                    fnt = ImageFont.load_default()
                self.draw.text((x, y), text, fill=self.fg_color, font=fnt)
                self._sync_canvas()
                self._push_undo()

        elif tool == "polygon":
            self.polygon_points.append((x, y))
            r = 3
            pid = self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                           fill=self.fg_color, outline=self.fg_color, tags="poly_pt")
            self.polygon_preview_ids.append(pid)
            if len(self.polygon_points) > 1:
                p1 = self.polygon_points[-2]
                p2 = self.polygon_points[-1]
                lid = self.canvas.create_line(p1[0], p1[1], p2[0], p2[1],
                                               fill=self.fg_color, width=self.brush_size, tags="poly_pt")
                self.polygon_preview_ids.append(lid)

        elif tool == "curve":
            self.bezier_points.append((x, y))
            r = 5
            pid = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill="#F38BA8", outline="#FFFFFF", width=1, tags="bezier_pt",
            )
            self.bezier_preview_ids.append(pid)
            self._update_bezier_preview()

    def on_mouse_drag(self, event):
        x, y = self._canvas_coords(event)
        tool = self.current_tool

        if tool in ("pencil", "brush"):
            thickness = self.brush_size if tool == "brush" else max(1, self.brush_size)
            self._draw_bresenham_line(self.prev_x, self.prev_y, x, y, self.fg_color, thickness)
            self._sync_canvas()
            self.prev_x, self.prev_y = x, y

        elif tool == "eraser":
            thickness = self.brush_size * 2
            self._draw_bresenham_line(self.prev_x, self.prev_y, x, y, self.bg_color, thickness)
            self._sync_canvas()
            self.prev_x, self.prev_y = x, y

        elif tool in ("line", "rectangle", "oval", "circle", "roundrect"):
            self.canvas.delete("preview")
            color = self.fg_color
            w = self.brush_size
            sx, sy = self.start_x, self.start_y
            fill_c = self.fg_color if self.fill_shape else ""

            if tool == "line":
                self.canvas.create_line(sx, sy, x, y, fill=color, width=w, tags="preview")
            elif tool == "rectangle":
                self.canvas.create_rectangle(sx, sy, x, y, outline=color, width=w,
                                              fill=fill_c if self.fill_shape else "", tags="preview")
            elif tool == "oval":
                self.canvas.create_oval(sx, sy, x, y, outline=color, width=w,
                                         fill=fill_c if self.fill_shape else "", tags="preview")
            elif tool == "circle":
                radius = int(math.dist((sx, sy), (x, y)))
                self.canvas.create_oval(sx - radius, sy - radius, sx + radius, sy + radius,
                                         outline=color, width=w,
                                         fill=fill_c if self.fill_shape else "", tags="preview")
            elif tool == "roundrect":
                self.canvas.create_rectangle(sx, sy, x, y, outline=color, width=w,
                                              fill=fill_c if self.fill_shape else "", tags="preview")

    def on_mouse_up(self, event):
        x, y = self._canvas_coords(event)
        tool = self.current_tool
        sx, sy = self.start_x, self.start_y
        thickness = self.brush_size
        fill_c = self.fg_color if self.fill_shape else None

        self.canvas.delete("preview")

        if tool in ("pencil", "brush", "eraser"):
            self._push_undo()

        elif tool == "line":
            self._draw_bresenham_line(sx, sy, x, y, self.fg_color, thickness)
            self._sync_canvas()
            self._push_undo()

        elif tool == "rectangle":
            self._draw_rectangle(sx, sy, x, y, self.fg_color, thickness, fill_c)
            self._sync_canvas()
            self._push_undo()

        elif tool == "oval":
            cx = (sx + x) // 2
            cy = (sy + y) // 2
            rx = abs(x - sx) // 2
            ry = abs(y - sy) // 2
            self._draw_ellipse_cg(cx, cy, rx, ry, self.fg_color, thickness, fill_c)
            self._sync_canvas()
            self._push_undo()

        elif tool == "circle":
            radius = int(math.dist((sx, sy), (x, y)))
            self._draw_circle_cg(sx, sy, radius, self.fg_color, thickness, fill_c)
            self._sync_canvas()
            self._push_undo()

        elif tool == "roundrect":
            self._draw_roundrect(sx, sy, x, y, self.fg_color, thickness, fill_c)
            self._sync_canvas()
            self._push_undo()

        self.start_x = self.start_y = None

    def on_right_click(self, event):
        """Right-click finishes polygon or Bezier curve drawing."""
        if self.current_tool == "polygon" and len(self.polygon_points) >= 3:
            self._finish_polygon(close=True)
        elif self.current_tool == "curve" and len(self.bezier_points) >= 2:
            self._finish_bezier(draw=True)

    def on_mouse_move(self, event):
        x, y = self._canvas_coords(event)
        self.mouse_x, self.mouse_y = x, y
        self._update_status()
        # Live Bezier curve preview
        if self.current_tool == "curve" and len(self.bezier_points) >= 1:
            self._update_bezier_preview(tentative_point=(x, y))

    # ================================================================
    #                     POLYGON
    # ================================================================

    def _finish_polygon(self, close=False):
        if len(self.polygon_points) >= 3 and close:
            fill_c = self.fg_color if self.fill_shape else None
            if fill_c:
                self.draw.polygon(self.polygon_points, fill=fill_c, outline=self.fg_color,
                                   width=self.brush_size)
            else:
                self.draw.polygon(self.polygon_points, outline=self.fg_color,
                                   width=self.brush_size)
            self._sync_canvas()
            self._push_undo()
        self.canvas.delete("poly_pt")
        self.polygon_points.clear()
        self.polygon_preview_ids.clear()

    # ================================================================
    #                     BEZIER CURVE
    # ================================================================

    def _update_bezier_preview(self, tentative_point=None):
        """Update the Bezier curve preview on the canvas."""
        self.canvas.delete("bezier_preview")
        pts = list(self.bezier_points)
        if tentative_point:
            pts.append(tentative_point)
        if len(pts) < 2:
            return
        # Draw control polygon (dashed lines)
        for i in range(len(pts) - 1):
            self.canvas.create_line(
                pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                fill="#888888", width=1, dash=(4, 4), tags="bezier_preview",
            )
        # Draw Bezier curve
        curve_pts = bezier_curve(pts, num_steps=300)
        if len(curve_pts) >= 2:
            flat = [coord for pt in curve_pts for coord in pt]
            self.canvas.create_line(
                *flat, fill=self.fg_color, width=self.brush_size,
                smooth=False, tags="bezier_preview",
            )

    def _finish_bezier(self, draw=False):
        """Finish Bezier curve drawing and commit to image."""
        if draw and len(self.bezier_points) >= 2:
            curve_pts = bezier_curve(self.bezier_points, num_steps=500)
            for i in range(len(curve_pts) - 1):
                self._draw_bresenham_line(
                    curve_pts[i][0], curve_pts[i][1],
                    curve_pts[i + 1][0], curve_pts[i + 1][1],
                    self.fg_color, self.brush_size,
                )
            self._sync_canvas()
            self._push_undo()
        self.canvas.delete("bezier_pt")
        self.canvas.delete("bezier_preview")
        self.bezier_points.clear()
        self.bezier_preview_ids.clear()

    # ================================================================
    #                     COLOR HELPERS
    # ================================================================

    def _set_color(self, which, color):
        if which == "fg":
            self.fg_color = color
            self.fg_swatch_large.config(bg=color)
        else:
            self.bg_color = color

    def _pick_custom_color(self, which):
        initial = self.fg_color if which == "fg" else self.bg_color
        result = colorchooser.askcolor(initialcolor=initial, parent=self.root)
        if result and result[1]:
            self._set_color(which, result[1])

    @staticmethod
    def _hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    # ================================================================
    #                     SIZE / FILL / OPACITY
    # ================================================================

    def _on_size_change(self, val):
        self.brush_size = int(val)
        self.size_value_label.config(text=str(self.brush_size))
        # Sync secondary toolbar slider
        self.toolbar_size_scale.set(self.brush_size)

    def _on_toolbar_size_change(self, val):
        self.brush_size = int(val)
        self.size_value_label.config(text=str(self.brush_size))
        self.size_var.set(self.brush_size)

    def _on_opacity_change(self, val):
        self.opacity = int(val)
        self.opacity_value_label.config(text=f"{self.opacity}%")

    def _on_fill_toggle(self):
        self.fill_shape = self.fill_var.get()

    # ================================================================
    #                     LAYERS
    # ================================================================

    def _toggle_layer_visibility(self, idx):
        self.layers[idx]["visible"] = self.layer_vars[idx].get()
        self._rebuild_layers_ui()

    def _add_layer(self):
        self.layer_counter += 1
        self.layers.append({
            "name": f"Layer {self.layer_counter}",
            "visible": True,
        })
        self._rebuild_layers_ui()

    # ================================================================
    #                     UNDO / REDO
    # ================================================================

    def _push_undo(self):
        self.undo_stack.append(self.image.copy())
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop())
            self.image = self.undo_stack[-1].copy()
            self.draw = ImageDraw.Draw(self.image)
            self._sync_canvas()

    def redo(self):
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            self.image = state.copy()
            self.draw = ImageDraw.Draw(self.image)
            self._sync_canvas()

    # ================================================================
    #                   ACTION BAR HANDLERS
    # ================================================================

    def _crop_action(self):
        messagebox.showinfo("Crop", "Select an area on the canvas first, then use Crop.")

    def _rotate_action(self):
        angle = simpledialog.askinteger(
            "Rotate", "Enter rotation angle (degrees):",
            parent=self.root, initialvalue=90,
        )
        if angle is not None:
            self.image = self.image.rotate(-angle, expand=True, fillcolor=(255, 255, 255))
            self.canvas_width, self.canvas_height = self.image.size
            self.draw = ImageDraw.Draw(self.image)
            self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
            self._sync_canvas()
            self._push_undo()
            self._update_status()

    def _effects_action(self):
        messagebox.showinfo("Effects", "Effects panel coming soon!\n\nUse the drawing tools for CG operations.")

    def _help_dialog(self):
        messagebox.showinfo(
            "Help - CG-Paint",
            "CG-Paint \u2014 Computer Graphics Paint Application\n\n"
            "Tools:\n"
            "\u2022 Brush/Pencil: Freehand drawing (Bresenham)\n"
            "\u2022 Eraser: Erase to background color\n"
            "\u2022 Fill: Flood fill algorithm\n"
            "\u2022 Shapes: Line, Rectangle, Oval, Circle, Rounded Rect, Polygon\n"
            "\u2022 Curve: Bezier curve (click control points, right-click to finish)\n"
            "\u2022 Text: Click to place text\n"
            "\u2022 Select/Picker: Pick color from canvas\n\n"
            "Shortcuts:\n"
            "Ctrl+Z = Undo, Ctrl+Y = Redo\n"
            "Ctrl+S = Save, Ctrl+O = Open, Ctrl+N = New\n\n"
            "Tips:\n"
            "\u2022 Left-click palette = Set foreground color\n"
            "\u2022 Right-click palette = Set background color\n"
            "\u2022 Right-click canvas = Finish polygon/curve",
        )

    # ================================================================
    #                     FILE OPERATIONS
    # ================================================================

    def new_canvas(self):
        if not messagebox.askyesno("New Canvas", "Discard current drawing?"):
            return
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self._sync_canvas()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._push_undo()
        self.file_path = None
        self.root.title("CG-Paint")

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                ("All files", "*.*"),
            ]
        )
        if not path:
            return
        try:
            img = Image.open(path).convert("RGB")
            self.canvas_width, self.canvas_height = img.size
            self.image = img
            self.draw = ImageDraw.Draw(self.image)
            self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
            self._sync_canvas()
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._push_undo()
            self.file_path = path
            self.root.title(f"CG-Paint - {os.path.basename(path)}")
            self._update_status()
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")

    def save_file(self):
        if self.file_path:
            self.image.save(self.file_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg;*.jpeg"),
                ("BMP Image", "*.bmp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.image.save(path)
            self.file_path = path
            self.root.title(f"CG-Paint - {os.path.basename(path)}")

    def clear_canvas(self):
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self._sync_canvas()
        self._push_undo()

    def resize_canvas_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Resize Canvas")
        dialog.geometry("280x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=THEME["panel_inner"])

        tk.Label(
            dialog, text="Width:", font=("Segoe UI", 9),
            bg=THEME["panel_inner"], fg=THEME["text"],
        ).grid(row=0, column=0, padx=12, pady=10, sticky="e")
        w_entry = tk.Entry(dialog, width=10, font=("Segoe UI", 9))
        w_entry.insert(0, str(self.canvas_width))
        w_entry.grid(row=0, column=1, padx=6, pady=10)

        tk.Label(
            dialog, text="Height:", font=("Segoe UI", 9),
            bg=THEME["panel_inner"], fg=THEME["text"],
        ).grid(row=1, column=0, padx=12, pady=4, sticky="e")
        h_entry = tk.Entry(dialog, width=10, font=("Segoe UI", 9))
        h_entry.insert(0, str(self.canvas_height))
        h_entry.grid(row=1, column=1, padx=6, pady=4)

        def apply():
            try:
                nw, nh = int(w_entry.get()), int(h_entry.get())
                if nw < 1 or nh < 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Enter valid positive integers.")
                return
            new_img = Image.new("RGB", (nw, nh), "white")
            new_img.paste(self.image, (0, 0))
            self.canvas_width, self.canvas_height = nw, nh
            self.image = new_img
            self.draw = ImageDraw.Draw(self.image)
            self.canvas.config(scrollregion=(0, 0, nw, nh))
            self._sync_canvas()
            self._push_undo()
            self._update_status()
            dialog.destroy()

        tk.Button(
            dialog, text="Apply", command=apply, width=12,
            font=("Segoe UI", 9), bg=THEME["btn_bg"], fg=THEME["text"],
            activebackground=THEME["btn_active_bg"], relief="flat", bd=1,
            cursor="hand2",
        ).grid(row=2, column=0, columnspan=2, pady=14)


# ======================== Main ========================

if __name__ == "__main__":
    root = tk.Tk()
    app = CGPaint(root)
    root.mainloop()
