import math


def srgb_to_linear(c):
    c = c / 255.0
    if c >= 0.04045:
        return ((c + 0.055) / 1.055) ** 2.4
    return c / 12.92


def linear_to_srgb(c):
    if c >= 0.0031308:
        c = 1.055 * (c ** (1 / 2.4)) - 0.055
    else:
        c = 12.92 * c
    return c * 255.0


def rgb_to_cmyk(r, g, b):
    r1, g1, b1 = r / 255.0, g / 255.0, b / 255.0
    k = 1.0 - max(r1, g1, b1)
    if k >= 1.0:
        return 0.0, 0.0, 0.0, 1.0
    c = (1.0 - r1 - k) / (1.0 - k)
    m = (1.0 - g1 - k) / (1.0 - k)
    y = (1.0 - b1 - k) / (1.0 - k)
    return c, m, y, k


def cmyk_to_rgb(c, m, y, k):
    r = 255.0 * (1 - c) * (1 - k)
    g = 255.0 * (1 - m) * (1 - k)
    b = 255.0 * (1 - y) * (1 - k)
    return r, g, b


def rgb_to_hls(r, g, b):
    r1, g1, b1 = r / 255.0, g / 255.0, b / 255.0
    maxc = max(r1, g1, b1)
    minc = min(r1, g1, b1)
    l = (maxc + minc) / 2.0
    if maxc == minc:
        return 0.0, l, 0.0
    d = maxc - minc
    if l < 0.5:
        s = d / (maxc + minc)
    else:
        s = d / (2.0 - maxc - minc)
    if maxc == r1:
        h = (g1 - b1) / d
        if g1 < b1:
            h += 6.0
    elif maxc == g1:
        h = (b1 - r1) / d + 2.0
    else:
        h = (r1 - g1) / d + 4.0
    h *= 60.0
    return h, l, s


def _hue_to_rgb(p, q, t):
    if t < 0:
        t += 1
    if t > 1:
        t -= 1
    if t < 1 / 6:
        return p + (q - p) * 6 * t
    if t < 1 / 2:
        return q
    if t < 2 / 3:
        return p + (q - p) * (2 / 3 - t) * 6
    return p


def hls_to_rgb(h, l, s):
    h = (h % 360.0) / 360.0
    if s == 0:
        v = l * 255.0
        return v, v, v
    if l < 0.5:
        q = l * (1 + s)
    else:
        q = l + s - l * s
    p = 2 * l - q
    r = _hue_to_rgb(p, q, h + 1 / 3)
    g = _hue_to_rgb(p, q, h)
    b = _hue_to_rgb(p, q, h - 1 / 3)
    return r * 255.0, g * 255.0, b * 255.0


def _ucr(c, m, y, k_max):
    k = k_max
    c2 = (c - k) / (1 - k) if k < 1 else 0.0
    m2 = (m - k) / (1 - k) if k < 1 else 0.0
    y2 = (y - k) / (1 - k) if k < 1 else 0.0
    return max(c2, 0.0), max(m2, 0.0), max(y2, 0.0), k


def _gcr(c, m, y, k_max):
    k = min(c, m, y)
    c2 = c - k
    m2 = m - k
    y2 = y - k
    return c2, m2, y2, k


def rgb_to_cmyk_ucr(r, g, b):
    r1, g1, b1 = r / 255.0, g / 255.0, b / 255.0
    c = 1 - r1
    m = 1 - g1
    y = 1 - b1
    k_max = min(c, m, y)
    return _ucr(c, m, y, k_max)


def rgb_to_cmyk_gcr(r, g, b):
    r1, g1, b1 = r / 255.0, g / 255.0, b / 255.0
    c = 1 - r1
    m = 1 - g1
    y = 1 - b1
    k_max = min(c, m, y)
    return _gcr(c, m, y, k_max)


def clip(v, lo=0.0, hi=255.0):
    return max(lo, min(hi, v))


def scale_rgb(r, g, b):
    vals = [r, g, b]
    mn, mx = min(vals), max(vals)
    if mx <= 255.0 and mn >= 0.0:
        return r, g, b
    if mx - mn == 0:
        v = clip(mx, 0, 255)
        return v, v, v
    scale = 255.0 / (mx - mn)
    offset = -mn * scale
    return clip(r * scale + offset), clip(g * scale + offset), clip(b * scale + offset)


def apply_strategy(r, g, b, strategy):
    out_of_range = r < 0 or r > 255 or g < 0 or g > 255 or b < 0 or b > 255
    if not out_of_range:
        return r, g, b, False
    if strategy == "clip":
        return clip(r), clip(g), clip(b), True
    return scale_rgb(r, g, b), True