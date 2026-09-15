import tkinter as tk
from tkinter import ttk
from model import hls_to_rgb


BG = "#1e1e2e"
PANEL = "#2a2a3e"
FG = "#e0e0f0"
ACCENT = "#7aa2f7"
ENTRY_BG = "#3a3a52"
KNOB = "#d0d0e0"
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")


class ColorView:
    def __init__(self, root, vm):
        self.root = root
        self.vm = vm
        self.root.title("Цветовые модели: RGB ↔ CMYK ↔ HLS")
        self.root.configure(bg=BG)

        self._style()
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))
        self.root.bind("<F11>", lambda e: self.root.attributes(
            "-fullscreen", not self.root.attributes("-fullscreen")))

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
        s.configure("TLabel", background=BG, foreground=FG, font=FONT)
        s.configure("Panel.TLabel", background=PANEL, foreground=FG, font=FONT)
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

        ttk.Label(outer, text="Цветовые модели: RGB ↔ CMYK ↔ HLS",
                  style="Title.TLabel").pack(anchor="w", pady=(0, 15))

        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True)

        left = ttk.Frame(content, style="Panel.TFrame", padding=20)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right = ttk.Frame(content, style="Panel.TFrame", padding=20)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self.canvas = tk.Canvas(left, height=260, highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", pady=(0, 10))

        self.hex_var = tk.StringVar()
        hex_row = ttk.Frame(left, style="Panel.TFrame")
        hex_row.pack(fill="x", pady=(0, 10))
        ttk.Label(hex_row, text="HEX:", style="Panel.TLabel").pack(side="left")
        ttk.Entry(hex_row, textvariable=self.hex_var, state="readonly",
                  font=("Consolas", 12)).pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.warning = ttk.Label(left, text="", style="Warn.TLabel", wraplength=400)
        self.warning.pack(anchor="w", pady=(0, 10))

        opts = ttk.Frame(left, style="Panel.TFrame")
        opts.pack(fill="x", pady=(5, 0))
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

        self.rgb_vars = [tk.DoubleVar() for _ in range(3)]
        self.cmyk_vars = [tk.DoubleVar() for _ in range(4)]
        self.hls_vars = [tk.DoubleVar() for _ in range(3)]

        self.rgb_sliders = []
        self.cmyk_sliders = []
        self.hls_sliders = []

        self._build_rgb(right)
        self._build_cmyk(right)
        self._build_hls(right)

    def _make_slider_row(self, parent, row, name, var, lo, hi, res, cmd):
        ttk.Label(parent, text=name, style="Panel.TLabel", width=3).grid(
            row=row, column=0, sticky="w", pady=6)

        s = tk.Scale(parent, from_=lo, to=hi, resolution=res, orient="horizontal",
                     variable=var, showvalue=False, length=380,
                     bg=KNOB,
                     fg=FG,
                     troughcolor=PANEL,
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

        for i, sl in enumerate(self.rgb_sliders):
            base = [r, g, b]
            left = base[:]
            right = base[:]
            left[i] = 0
            right[i] = 255
            sl.configure(troughcolor=self._rgb_hex(*base))

        for i, sl in enumerate(self.cmyk_sliders):
            sl.configure(troughcolor=self._rgb_hex(r, g, b))

        for i, sl in enumerate(self.hls_sliders):
            sl.configure(troughcolor=self._rgb_hex(r, g, b))

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
        w = self.canvas.winfo_width() or 400
        h = self.canvas.winfo_height() or 260
        self.canvas.create_rectangle(0, 0, w, h, fill=hex_color, outline="")
        self.canvas.configure(bg=hex_color)

        for i in range(3):
            self.rgb_vars[i].set(round([self.vm.r, self.vm.g, self.vm.b][i], 2))
        for i in range(4):
            self.cmyk_vars[i].set(round([self.vm.c, self.vm.m, self.vm.y, self.vm.k][i], 4))
        for i in range(3):
            self.hls_vars[i].set(round([self.vm.h, self.vm.l, self.vm.s][i], 4))

        self.hex_var.set(hex_color)
        self.warning.config(text=self.vm.warning)
        self._update_troughs()