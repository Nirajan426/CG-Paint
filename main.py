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


# ======================== Paint Application ========================

COLORS = [
    "#000000", "#808080", "#800000", "#808000",
    "#008000", "#008080", "#000080", "#800080",
    "#FFFFFF", "#C0C0C0", "#FF0000", "#FFFF00",
    "#00FF00", "#00FFFF", "#0000FF", "#FF00FF",
    "#FF8C00", "#FFD700", "#7CFC00", "#40E0D0",
    "#1E90FF", "#BA55D3", "#FF69B4", "#A0522D",
]

TOOLS = [
    ("Pencil", "pencil"),
    ("Brush", "brush"),
    ("Eraser", "eraser"),
    ("Line", "line"),
    ("Rect", "rectangle"),
    ("Oval", "oval"),
    ("Circle", "circle"),
    ("R-Rect", "roundrect"),
    ("Polygon", "polygon"),
    ("Fill", "fill"),
    ("Text", "text"),
    ("Picker", "picker"),
]


class CGPaint:
    def __init__(self, root):
        self.root = root
        self.root.title("CG-Paint")
        self.root.geometry("1100x720")
        self.root.minsize(800, 600)

        # State
        self.canvas_width = 960
        self.canvas_height = 600
        self.current_tool = "pencil"
        self.fg_color = "#000000"
        self.bg_color = "#FFFFFF"
        self.brush_size = 3
        self.fill_shape = False
        self.start_x = self.start_y = None
        self.prev_x = self.prev_y = None
        self.preview_id = None
        self.polygon_points = []
        self.polygon_preview_ids = []
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo = 30
        self.file_path = None

        # PIL backing image for pixel-level ops & saving
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)

        self._build_ui()
        self._sync_canvas()
        self._push_undo()

    # -------------------- UI Construction --------------------

    def _build_ui(self):
        # Menu bar
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

        self.root.config(menu=menubar)

        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self.new_canvas())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())

        # Main layout: left toolbar | canvas | right panel
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        # ---- Left toolbar ----
        toolbar = tk.Frame(main_frame, width=110, relief="raised", bd=1)
        toolbar.pack(side="left", fill="y")
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="Tools", font=("Segoe UI", 9, "bold")).pack(pady=(6, 2))

        self.tool_buttons = {}
        tool_frame = tk.Frame(toolbar)
        tool_frame.pack(padx=4, pady=2)
        for i, (label, tool_id) in enumerate(TOOLS):
            btn = tk.Button(
                tool_frame, text=label, width=6, font=("Segoe UI", 8),
                relief="raised", bd=1,
                command=lambda t=tool_id: self._select_tool(t),
            )
            btn.grid(row=i // 2, column=i % 2, padx=1, pady=1)
            self.tool_buttons[tool_id] = btn

        self._highlight_tool()

        # Separator
        ttk.Separator(toolbar, orient="horizontal").pack(fill="x", padx=4, pady=6)

        # Brush size
        tk.Label(toolbar, text="Size", font=("Segoe UI", 9, "bold")).pack()
        self.size_var = tk.IntVar(value=self.brush_size)
        size_scale = tk.Scale(
            toolbar, from_=1, to=40, orient="horizontal",
            variable=self.size_var, command=self._on_size_change,
            length=90, showvalue=True,
        )
        size_scale.pack(padx=4, pady=2)

        # Fill checkbox
        self.fill_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            toolbar, text="Fill shape", variable=self.fill_var,
            font=("Segoe UI", 8), command=self._on_fill_toggle,
        ).pack(pady=4)

        # Separator
        ttk.Separator(toolbar, orient="horizontal").pack(fill="x", padx=4, pady=6)

        # Color palette
        tk.Label(toolbar, text="Colors", font=("Segoe UI", 9, "bold")).pack()

        # Current color indicators
        color_display = tk.Frame(toolbar)
        color_display.pack(pady=4)
        tk.Label(color_display, text="FG:", font=("Segoe UI", 8)).grid(row=0, column=0)
        self.fg_swatch = tk.Label(
            color_display, bg=self.fg_color, width=3, height=1, relief="solid", bd=1,
        )
        self.fg_swatch.grid(row=0, column=1, padx=2)
        self.fg_swatch.bind("<Button-1>", lambda e: self._pick_custom_color("fg"))

        tk.Label(color_display, text="BG:", font=("Segoe UI", 8)).grid(row=1, column=0)
        self.bg_swatch = tk.Label(
            color_display, bg=self.bg_color, width=3, height=1, relief="solid", bd=1,
        )
        self.bg_swatch.grid(row=1, column=1, padx=2)
        self.bg_swatch.bind("<Button-1>", lambda e: self._pick_custom_color("bg"))

        palette_frame = tk.Frame(toolbar)
        palette_frame.pack(padx=4, pady=2)
        for i, color in enumerate(COLORS):
            swatch = tk.Label(
                palette_frame, bg=color, width=2, height=1,
                relief="solid", bd=1, cursor="hand2",
            )
            swatch.grid(row=i // 4, column=i % 4, padx=1, pady=1)
            swatch.bind("<Button-1>", lambda e, c=color: self._set_color("fg", c))
            swatch.bind("<Button-3>", lambda e, c=color: self._set_color("bg", c))

        # ---- Canvas area ----
        canvas_frame = tk.Frame(main_frame, relief="sunken", bd=2)
        canvas_frame.pack(side="left", fill="both", expand=True, padx=2, pady=2)

        # Scrollable canvas
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
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))

        # Canvas mouse bindings
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        # ---- Status bar ----
        self.status_bar = tk.Label(
            self.root, text="Ready", bd=1, relief="sunken", anchor="w",
            font=("Segoe UI", 8), padx=6,
        )
        self.status_bar.pack(side="bottom", fill="x")

    # -------------------- Tool Selection --------------------

    def _select_tool(self, tool_id):
        self._finish_polygon()
        self.current_tool = tool_id
        self._highlight_tool()
        cursors = {
            "pencil": "pencil", "brush": "circle", "eraser": "circle",
            "line": "cross", "rectangle": "cross", "oval": "cross",
            "circle": "cross", "roundrect": "cross", "polygon": "cross",
            "fill": "cross", "text": "xterm", "picker": "crosshair",
        }
        self.canvas.config(cursor=cursors.get(tool_id, "cross"))
        self.status_bar.config(text=f"Tool: {tool_id.capitalize()}")

    def _highlight_tool(self):
        for tid, btn in self.tool_buttons.items():
            btn.config(relief="sunken" if tid == self.current_tool else "raised",
                       bg="#B0D0FF" if tid == self.current_tool else "SystemButtonFace")

    # -------------------- Canvas Sync --------------------

    def _sync_canvas(self):
        """Update the tk Canvas from the PIL image."""
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.delete("img")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image, tags="img")
        self.canvas.tag_lower("img")

    def _canvas_coords(self, event):
        """Convert event coords to canvas (image) coords."""
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        return x, y

    # -------------------- Drawing on PIL image --------------------

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

    # -------------------- Mouse Handlers --------------------

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
                self.status_bar.config(text=f"Picked color: {color}")

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
            # Show rubber-band preview on tk canvas
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
        """Right-click finishes polygon drawing."""
        if self.current_tool == "polygon" and len(self.polygon_points) >= 3:
            self._finish_polygon(close=True)

    def on_mouse_move(self, event):
        x, y = self._canvas_coords(event)
        self.status_bar.config(
            text=f"Tool: {self.current_tool.capitalize()}  |  Pos: ({x}, {y})  |  "
                 f"Canvas: {self.canvas_width}x{self.canvas_height}  |  Size: {self.brush_size}"
        )

    # -------------------- Polygon --------------------

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

        # Clean up preview
        self.canvas.delete("poly_pt")
        self.polygon_points.clear()
        self.polygon_preview_ids.clear()

    # -------------------- Color Helpers --------------------

    def _set_color(self, which, color):
        if which == "fg":
            self.fg_color = color
            self.fg_swatch.config(bg=color)
        else:
            self.bg_color = color
            self.bg_swatch.config(bg=color)

    def _pick_custom_color(self, which):
        initial = self.fg_color if which == "fg" else self.bg_color
        result = colorchooser.askcolor(initialcolor=initial, parent=self.root)
        if result and result[1]:
            self._set_color(which, result[1])

    @staticmethod
    def _hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    # -------------------- Size / Fill --------------------

    def _on_size_change(self, val):
        self.brush_size = int(val)

    def _on_fill_toggle(self):
        self.fill_shape = self.fill_var.get()

    # -------------------- Undo / Redo --------------------

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
            self.status_bar.config(text="Undo")

    def redo(self):
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(state)
            self.image = state.copy()
            self.draw = ImageDraw.Draw(self.image)
            self._sync_canvas()
            self.status_bar.config(text="Redo")

    # -------------------- File Operations --------------------

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
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")

    def save_file(self):
        if self.file_path:
            self.image.save(self.file_path)
            self.status_bar.config(text=f"Saved: {self.file_path}")
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
            self.status_bar.config(text=f"Saved: {path}")

    def clear_canvas(self):
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self._sync_canvas()
        self._push_undo()
        self.status_bar.config(text="Canvas cleared")

    def resize_canvas_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Resize Canvas")
        dialog.geometry("260x130")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Width:").grid(row=0, column=0, padx=10, pady=8, sticky="e")
        w_entry = tk.Entry(dialog, width=8)
        w_entry.insert(0, str(self.canvas_width))
        w_entry.grid(row=0, column=1, padx=4, pady=8)

        tk.Label(dialog, text="Height:").grid(row=1, column=0, padx=10, pady=4, sticky="e")
        h_entry = tk.Entry(dialog, width=8)
        h_entry.insert(0, str(self.canvas_height))
        h_entry.grid(row=1, column=1, padx=4, pady=4)

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
            dialog.destroy()

        tk.Button(dialog, text="Apply", command=apply, width=10).grid(row=2, column=0, columnspan=2, pady=10)


# ======================== Main ========================

if __name__ == "__main__":
    root = tk.Tk()
    app = CGPaint(root)
    root.mainloop()
