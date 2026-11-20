from model import (
    rgb_to_cmyk,
    cmyk_to_rgb,
    rgb_to_hls,
    hls_to_rgb,
    rgb_to_cmyk_ucr,
    rgb_to_cmyk_gcr,
    apply_strategy,
)


class ColorViewModel:
    def __init__(self):
        self.r = 255.0
        self.g = 0.0
        self.b = 0.0
        self.c = 0.0
        self.m = 1.0
        self.y = 1.0
        self.k = 0.0
        self.h = 0.0
        self.l = 0.5
        self.s = 1.0
        self.separation = "UCR"
        self.gamut_strategy = "clip"
        self.warning = ""

    def _update_from_rgb(self):
        r, g, b, clipped = apply_strategy(self.r, self.g, self.b, self.gamut_strategy)
        self.warning = "Цвет вне диапазона RGB — применено " + (
            "обрезание" if self.gamut_strategy == "clip" else "масштабирование"
        ) if clipped else ""
        self.r, self.g, self.b = r, g, b
        if self.separation == "UCR":
            self.c, self.m, self.y, self.k = rgb_to_cmyk_ucr(r, g, b)
        else:
            self.c, self.m, self.y, self.k = rgb_to_cmyk_gcr(r, g, b)
        self.h, self.l, self.s = rgb_to_hls(r, g, b)

    def set_rgb(self, r, g, b):
        self.r, self.g, self.b = float(r), float(g), float(b)
        self._update_from_rgb()

    def set_cmyk(self, c, m, y, k):
        self.c, self.m, self.y, self.k = float(c), float(m), float(y), float(k)
        r, g, b = cmyk_to_rgb(self.c, self.m, self.y, self.k)
        self.r, self.g, self.b = r, g, b
        self._update_from_rgb()

    def set_hls(self, h, l, s):
        self.h, self.l, self.s = float(h), float(l), float(s)
        r, g, b = hls_to_rgb(self.h, self.l, self.s)
        self.r, self.g, self.b = r, g, b
        self._update_from_rgb()

    def get_hex(self):
        return "#{:02X}{:02X}{:02X}".format(
            int(round(self.r)), int(round(self.g)), int(round(self.b))
        )