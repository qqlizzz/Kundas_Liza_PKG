import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from model import hls_to_rgb, rgb_to_hls


BG = "#1e1e2e"
PANEL = "#2a2a3e"
CARD = "#31314a"
FG = "#e0e0f0"
FG_DIM = "#a0a0b8"
ACCENT = "#7aa2f7"
ENTRY_BG = "#3a3a52"
KNOB = "#d0d0e0"
BORDER = "#4a4a66"
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_MONO = ("Consolas", 11)

PICKER_W = 320
PICKER_H = 220
HUE_W = 320
HUE_H = 24
LUM_W = 320
LUM_H = 24
PRESET_COLS = 12

FAVORITES_FILE = os.path.join(os.path.dirname(__file__), "favorites.json")


class ColorView:
    def __init__(self, root, vm):
        self.root = root
        self.vm = vm
        self.root.title("ColorLab — RGB ↔ CMYK ↔ HLS")
        self.root.configure(bg=BG)

        self._style()
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))
        self.root.bind("<F11>", lambda e: self.root.attributes(
            "-fullscreen", not self.root.attributes("-fullscreen")))

        self._favorites = self._load_favorites()

        self._build_layout()
        self.refresh()

    def _style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("Card.TFrame", background=CARD)
        s.configure("TLabel", background=BG, foreground=FG, font=FONT)
        s.configure("Panel.TLabel", background=PANEL, foreground=FG, font=FONT)
        s.configure("Card.TLabel", background=CARD, foreground=FG, font=FONT)
        s.configure("Title.TLabel", background=BG, foreground=ACCENT, font=FONT_TITLE)
        s.configure("Section.TLabel", background=PANEL, foreground=ACCENT, font=FONT_BOLD)
        s.configure("Warn.TLabel", background=PANEL, foreground="#e0af68", font=FONT)
        s.configure("TRadiobutton", background=PANEL, foreground=FG, font=FONT,
                    focuscolor=PANEL)
        s.map("TRadiobutton", background=[("active", PANEL)],
              foreground=[("active", ACCENT)])
        s.configure("TEntry", fieldbackground=ENTRY_BG, foreground=FG,
                    insertcolor=FG, bordercolor=PANEL, lightcolor=PANEL,
                    darkcolor=PANEL, font=FONT)

    def _build_layout(self):
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="ColorLab — RGB ↔ CMYK ↔ HLS",
                  style="Title.TLabel").pack(anchor="w", pady=(0, 12))

        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True)

        left = ttk.Frame(content, style="Panel.TFrame", padding=18)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right = ttk.Frame(content, style="Panel.TFrame", padding=18)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self._build_result_block(left)

        opts = ttk.Frame(left, style="Panel.TFrame")
        opts.pack(fill="x", pady=(18, 0))
        ttk.Label(opts, text="Цветоделение:", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        self.sep_var = tk.StringVar(value="UCR")
        ttk.Radiobutton(opts, text="UCR", variable=self.sep_var, value="UCR",
                        command=self.on_separation).grid(row=0, column=1, padx=6)
        ttk.Radiobutton(opts, text="GCR", variable=self.sep_var, value="GCR",
                        command=self.on_separation).grid(row=0, column=2, padx=6)
        ttk.Label(opts, text="Границы:", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.strategy_var = tk.StringVar(value="clip")
        ttk.Radiobutton(opts, text="Clipping", variable=self.strategy_var, value="clip",
                        command=self.on_strategy).grid(row=1, column=1, padx=6, pady=(6, 0))
        ttk.Radiobutton(opts, text="Scaling", variable=self.strategy_var, value="scale",
                        command=self.on_strategy).grid(row=1, column=2, padx=6, pady=(6, 0))

        self.warning = ttk.Label(left, text="", style="Warn.TLabel", wraplength=420)
        self.warning.pack(anchor="w", pady=(12, 0))

        self.rgb_vars = [tk.DoubleVar() for _ in range(3)]
        self.cmyk_vars = [tk.DoubleVar() for _ in range(4)]
        self.hls_vars = [tk.DoubleVar() for _ in range(3)]

        self.rgb_sliders = []
        self.cmyk_sliders = []
        self.hls_sliders = []

        self._build_rgb(right)
        self._build_cmyk(right)
        self._build_hls(right)

    def _build_result_block(self, parent):
        ttk.Label(parent, text="Результат", style="Section.TLabel").pack(
            anchor="w", pady=(0, 8))

        card = tk.Frame(parent, bg=CARD, highlightthickness=1,
                        highlightbackground=BORDER, bd=0)
        card.pack(fill="x")

        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="x", padx=14, pady=12)

        self.canvas = tk.Canvas(inner, width=110, height=110,
                                highlightthickness=1, bd=0,
                                highlightbackground=BORDER, bg=CARD)
        self.canvas.grid(row=0, column=0, rowspan=3, sticky="nw")

        info = tk.Frame(inner, bg=CARD)
        info.grid(row=0, column=1, sticky="nw", padx=(14, 0))

        self.hex_var = tk.StringVar()
        self.hex_entry = tk.Entry(info, textvariable=self.hex_var, state="readonly",
                                   bg=CARD, fg=FG, readonlybackground=CARD,
                                   relief="flat", font=FONT_MONO,
                                   highlightthickness=0, insertbackground=FG,
                                   width=12)
        self.hex_entry.grid(row=0, column=0, sticky="w")
        self.hex_entry.bind("<Control-c>", self._copy_hex)
        self.hex_entry.bind("<Control-C>", self._copy_hex)

        self.rgb_text_var = tk.StringVar()
        ttk.Label(info, textvariable=self.rgb_text_var, style="Card.TLabel",
                  font=FONT_MONO).grid(row=1, column=0, sticky="w", pady=(6, 0))

        btns = tk.Frame(card, bg=CARD)
        btns.pack(fill="x", padx=14, pady=(0, 12))

        self._mk_button(btns, "Палитра", self.open_palette_window, width=12)
        self._mk_button(btns, "Сохранить", self.save_favorite, width=12)
        self._mk_button(btns, "Загрузить", self.load_favorite, width=12)

    def _mk_button(self, parent, text, cmd, width=10):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=ACCENT, fg="#101020", activebackground="#5a82d7",
                      activeforeground="#101020", relief="flat", bd=0,
                      font=FONT_BOLD, width=width, cursor="hand2",
                      highlightthickness=0)
        b.pack(side="left", padx=(0, 6), ipady=4)
        return b

    def _make_slider_row(self, parent, row, name, var, lo, hi, res, cmd):
        ttk.Label(parent, text=name, style="Panel.TLabel", width=3).grid(
            row=row, column=0, sticky="w", pady=6)

        s = tk.Scale(parent, from_=lo, to=hi, resolution=res, orient="horizontal",
                     variable=var, showvalue=False, length=380,
                     bg=KNOB, fg=FG,
                     troughcolor=CARD,
                     activebackground=ACCENT,
                     highlightthickness=0, bd=0,
                     sliderrelief="raised",
                     sliderlength=20,
                     width=16,
                     command=cmd)
        s.grid(row=row, column=1, sticky="ew", padx=8)
        e = ttk.Entry(parent, textvariable=var, width=10, font=("Consolas", 10))
        e.grid(row=row, column=2)
        e.bind("<Return>", lambda ev: cmd(None))
        return s

    def _build_rgb(self, parent):
        ttk.Label(parent, text="RGB", style="Section.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        for i, name in enumerate(["R", "G", "B"]):
            s = self._make_slider_row(parent, 1 + i, name, self.rgb_vars[i],
                                      0, 255, 1, lambda v, idx=i: self.on_rgb_slider(idx))
            self.rgb_sliders.append(s)

    def _build_cmyk(self, parent):
        ttk.Label(parent, text="CMYK", style="Section.TLabel").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(14, 6))
        for i, name in enumerate(["C", "M", "Y", "K"]):
            s = self._make_slider_row(parent, 5 + i, name, self.cmyk_vars[i],
                                      0.0, 1.0, 0.001, lambda v, idx=i: self.on_cmyk_slider(idx))
            self.cmyk_sliders.append(s)

    def _build_hls(self, parent):
        ttk.Label(parent, text="HLS", style="Section.TLabel").grid(
            row=9, column=0, columnspan=3, sticky="w", pady=(14, 6))
        ranges = [(0, 360, 1), (0.0, 1.0, 0.001), (0.0, 1.0, 0.001)]
        for i, (name, rng) in enumerate(zip(["H", "L", "S"], ranges)):
            s = self._make_slider_row(parent, 10 + i, name, self.hls_vars[i],
                                      rng[0], rng[1], rng[2],
                                      lambda v, idx=i: self.on_hls_slider(idx))
            self.hls_sliders.append(s)

    def _rgb_hex(self, r, g, b):
        return "#{:02X}{:02X}{:02X}".format(
            int(max(0, min(255, r))), int(max(0, min(255, g))), int(max(0, min(255, b))))

    def _update_troughs(self):
        r, g, b = self.vm.r, self.vm.g, self.vm.b
        for sl in self.rgb_sliders + self.cmyk_sliders + self.hls_sliders:
            sl.configure(troughcolor=self._rgb_hex(r, g, b))

    def _copy_hex(self, event=None):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.hex_var.get())
        return "break"

    def on_rgb_slider(self, idx):
        self.vm.set_rgb(self.rgb_vars[0].get(), self.rgb_vars[1].get(), self.rgb_vars[2].get())
        self.refresh()

    def on_cmyk_slider(self, idx):
        self.vm.set_cmyk(*[v.get() for v in self.cmyk_vars])
        self.refresh()

    def on_hls_slider(self, idx):
        self.vm.set_hls(*[v.get() for v in self.hls_vars])
        self.refresh()

    def on_separation(self):
        self.vm.separation = self.sep_var.get()
        self.vm.set_rgb(self.vm.r, self.vm.g, self.vm.b)
        self.refresh()

    def on_strategy(self):
        self.vm.gamut_strategy = self.strategy_var.get()
        self.vm.set_rgb(self.vm.r, self.vm.g, self.vm.b)
        self.refresh()

    def refresh(self):
        hex_color = self.vm.get_hex()
        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, 200, 200, fill=hex_color, outline="")
        self.canvas.configure(bg=hex_color)

        for i in range(3):
            self.rgb_vars[i].set(round([self.vm.r, self.vm.g, self.vm.b][i], 2))
        for i in range(4):
            self.cmyk_vars[i].set(round([self.vm.c, self.vm.m, self.vm.y, self.vm.k][i], 4))
        for i in range(3):
            self.hls_vars[i].set(round([self.vm.h, self.vm.l, self.vm.s][i], 4))

        self.hex_var.set(hex_color)
        self.rgb_text_var.set("RGB: {} {} {}".format(
            int(round(self.vm.r)), int(round(self.vm.g)), int(round(self.vm.b))))
        self.warning.config(text=self.vm.warning)
        self._update_troughs()

    def open_palette_window(self):
        PaletteWindow(self.root, self.vm, self)

    def save_favorite(self):
        color = self.vm.get_hex()
        if color not in self._favorites:
            self._favorites.append(color)
            self._favorites = self._favorites[-24:]
            self._save_favorites()
            messagebox.showinfo("Сохранено", "Цвет добавлен в избранное: " + color)

    def load_favorite(self):
        if not self._favorites:
            messagebox.showinfo("Пусто", "Ещё нет сохранённых цветов.")
            return
        color = self._favorites[-1]
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        self.vm.set_rgb(r, g, b)
        self.refresh()

    def _load_favorites(self):
        try:
            with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_favorites(self):
        try:
            with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._favorites, f)
        except Exception:
            pass


class PaletteWindow:
    def __init__(self, master, vm, parent_view):
        self.vm = vm
        self.parent = parent_view
        self.win = tk.Toplevel(master)
        self.win.title("Палитра")
        self.win.configure(bg=BG)
        self.win.transient(master)
        self.win.grab_set()

        self._picker_photo = None
        self._hue_photo = None
        self._lum_photo = None
        self._picker_cache_h = None
        self._picker_redraw_job = None

        self.h_preview = vm.h
        self.l_preview = vm.l
        self.s_preview = vm.s

        self._build()
        self._draw_picker(force=True)
        self._draw_hue()
        self._draw_lum()
        self._draw_picker_marker()

    def _build(self):
        wrap = tk.Frame(self.win, bg=BG, padx=20, pady=20)
        wrap.pack(fill="both", expand=True)

        tk.Label(wrap, text="Палитра", bg=BG, fg=ACCENT,
                 font=FONT_TITLE).pack(anchor="w", pady=(0, 12))

        self.picker = tk.Canvas(wrap, width=PICKER_W, height=PICKER_H,
                                highlightthickness=1, bd=0,
                                highlightbackground=BORDER, bg=BG)
        self.picker.pack(anchor="w")
        self.picker.bind("<Button-1>", self._click_picker)
        self.picker.bind("<B1-Motion>", self._click_picker)

        self.hue_bar = tk.Canvas(wrap, width=HUE_W, height=HUE_H,
                                 highlightthickness=1, bd=0,
                                 highlightbackground=BORDER, bg=BG)
        self.hue_bar.pack(anchor="w", pady=(10, 0))
        self.hue_bar.bind("<Button-1>", self._click_hue)
        self.hue_bar.bind("<B1-Motion>", self._click_hue)

        self.lum_bar = tk.Canvas(wrap, width=LUM_W, height=LUM_H,
                                 highlightthickness=1, bd=0,
                                 highlightbackground=BORDER, bg=BG)
        self.lum_bar.pack(anchor="w", pady=(8, 0))
        self.lum_bar.bind("<Button-1>", self._click_lum)
        self.lum_bar.bind("<B1-Motion>", self._click_lum)

        tk.Label(wrap, text="Быстрые цвета", bg=BG, fg=ACCENT,
                 font=FONT_BOLD).pack(anchor="w", pady=(14, 6))

        presets = tk.Frame(wrap, bg=BG)
        presets.pack(anchor="w")
        colors = [
            "#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", "#FFFF00",
            "#FF00FF", "#00FFFF", "#808080", "#800000", "#808000", "#008000",
            "#800080", "#008080", "#000080", "#C0C0C0", "#FFA500", "#A52A2A",
            "#FFC0CB", "#4B0082", "#EE82EE", "#F5DEB3", "#7FFFD4", "#2E8B57",
        ]
        for idx, c in enumerate(colors):
            row = idx // PRESET_COLS
            col = idx % PRESET_COLS
            b = tk.Button(presets, bg=c, activebackground=c, width=2, height=1,
                          bd=1, relief="flat", highlightthickness=0,
                          command=lambda cc=c: self._pick_preset(cc))
            b.grid(row=row, column=col, padx=1, pady=1)

        btns = tk.Frame(wrap, bg=BG)
        btns.pack(fill="x", pady=(16, 0))
        PaletteWindow._mk_btn(btns, "Применить", self._apply, ACCENT).pack(side="left")
        PaletteWindow._mk_btn(btns, "Отмена", self.win.destroy, "#666680").pack(side="left", padx=6)

    @staticmethod
    def _mk_btn(parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd, bg=color, fg="#101020",
                         activebackground=color, relief="flat", bd=0,
                         font=FONT_BOLD, width=12, cursor="hand2",
                         highlightthickness=0)

    def _hex(self, r, g, b):
        return "#{:02X}{:02X}{:02X}".format(
            int(max(0, min(255, r))), int(max(0, min(255, g))), int(max(0, min(255, b))))

    def _draw_picker(self, force=False):
        if not force and self._picker_cache_h == self.h_preview:
            return
        self._picker_cache_h = self.h_preview

        BLOCK = 4
        cols = PICKER_W // BLOCK
        rows = PICKER_H // BLOCK

        photo = tk.PhotoImage(width=PICKER_W, height=PICKER_H)
        h = self.h_preview

        for cy in range(rows):
            l = 1.0 - (cy * BLOCK) / (PICKER_H - 1)
            row_line = []
            for cx in range(cols):
                s = (cx * BLOCK) / (PICKER_W - 1)
                r, g, b = hls_to_rgb(h, l, s)
                row_line.append(self._hex(r, g, b))
            for i, color in enumerate(row_line):
                x0 = i * BLOCK
                for dy in range(BLOCK):
                    y = cy * BLOCK + dy
                    if y >= PICKER_H:
                        break
                    for dx in range(BLOCK):
                        x = x0 + dx
                        if x >= PICKER_W:
                            break
                        photo.put(color, (x, y))

        self._picker_photo = photo
        self.picker.delete("all")
        self.picker.create_image(0, 0, anchor="nw", image=photo)

    def _draw_picker_marker(self):
        self.picker.delete("marker")
        x = self.s_preview * (PICKER_W - 1)
        y = (1.0 - self.l_preview) * (PICKER_H - 1)
        r = 6
        self.picker.create_oval(x - r, y - r, x + r, y + r,
                                outline="black", width=2, tags="marker")
        self.picker.create_oval(x - r + 1, y - r + 1, x + r - 1, y + r - 1,
                                outline="white", width=1, tags="marker")

    def _draw_hue(self):
        photo = tk.PhotoImage(width=HUE_W, height=HUE_H)
        for x in range(HUE_W):
            h = (x / (HUE_W - 1)) * 360.0
            r, g, b = hls_to_rgb(h, 0.5, 1.0)
            c = self._hex(r, g, b)
            for y in range(HUE_H):
                photo.put(c, (x, y))
        self._hue_photo = photo
        self.hue_bar.delete("all")
        self.hue_bar.create_image(0, 0, anchor="nw", image=photo)
        self._draw_hue_marker()

    def _draw_hue_marker(self):
        self.hue_bar.delete("hm")
        x = (self.h_preview / 360.0) * (HUE_W - 1)
        self.hue_bar.create_rectangle(x - 2, 0, x + 2, HUE_H,
                                      outline="white", width=2, tags="hm")
        self.hue_bar.create_rectangle(x - 2, 0, x + 2, HUE_H,
                                      outline="black", width=1, tags="hm")

    def _draw_lum(self):
        photo = tk.PhotoImage(width=LUM_W, height=LUM_H)
        for x in range(LUM_W):
            l = x / (LUM_W - 1)
            r, g, b = hls_to_rgb(self.h_preview, l, self.s_preview)
            c = self._hex(r, g, b)
            for y in range(LUM_H):
                photo.put(c, (x, y))
        self._lum_photo = photo
        self.lum_bar.delete("all")
        self.lum_bar.create_image(0, 0, anchor="nw", image=photo)
        self._draw_lum_marker()

    def _draw_lum_marker(self):
        self.lum_bar.delete("lm")
        x = self.l_preview * (LUM_W - 1)
        self.lum_bar.create_rectangle(x - 2, 0, x + 2, LUM_H,
                                      outline="white", width=2, tags="lm")
        self.lum_bar.create_rectangle(x - 2, 0, x + 2, LUM_H,
                                      outline="black", width=1, tags="lm")

    def _click_picker(self, event):
        self.s_preview = max(0.0, min(1.0, event.x / (PICKER_W - 1)))
        self.l_preview = max(0.0, min(1.0, 1.0 - event.y / (PICKER_H - 1)))
        self._draw_picker_marker()
        self._draw_lum_marker()
        self.win.after_idle(self._refresh_lum)

    def _refresh_lum(self):
        self._draw_lum()

    def _click_hue(self, event):
        self.h_preview = max(0.0, min(360.0, (event.x / (HUE_W - 1)) * 360.0))
        self._draw_hue_marker()
        self._draw_lum_marker()
        self._schedule_picker_redraw()
        self.win.after_idle(self._refresh_lum)

    def _click_lum(self, event):
        self.l_preview = max(0.0, min(1.0, event.x / (LUM_W - 1)))
        self._draw_picker_marker()
        self._draw_lum_marker()

    def _pick_preset(self, color):
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        h, l, s = rgb_to_hls(r, g, b)
        self.h_preview = h
        self.l_preview = l
        self.s_preview = s
        self._draw_picker(force=True)
        self._draw_hue()
        self._draw_lum()

    def _schedule_picker_redraw(self):
        if self._picker_redraw_job:
            self.win.after_cancel(self._picker_redraw_job)
        self._picker_redraw_job = self.win.after(60, self._do_picker_redraw)

    def _do_picker_redraw(self):
        self._picker_redraw_job = None
        self._draw_picker(force=True)
        self._draw_picker_marker()

    def _apply(self):
        self.vm.set_hls(self.h_preview, self.l_preview, self.s_preview)
        self.parent.refresh()
        self.win.destroy()