# buffer_layer.py
import numpy as np
from PyQt5.QtGui import QImage


class EdgePadding:
    @staticmethod
    def clamp(img, pad):
        return np.pad(img, ((pad, pad), (pad, pad), (0, 0)), mode='edge')

    @staticmethod
    def reflect(img, pad):
        return np.pad(img, ((pad, pad), (pad, pad), (0, 0)), mode='reflect')


class BufferWrapper:
    @staticmethod
    def qimage_to_numpy(qimg):
        qimg = qimg.convertToFormat(QImage.Format_RGB888)
        w, h = qimg.width(), qimg.height()
        ptr = qimg.bits()
        ptr.setsize(qimg.byteCount())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, qimg.bytesPerLine()))
        return arr[:, : w * 3].reshape((h, w, 3)).copy()

    @staticmethod
    def numpy_to_qimage(arr):
        arr = np.ascontiguousarray(arr.astype(np.uint8))
        h, w, _ = arr.shape
        return QImage(arr.data, w, h, 3 * w, QImage.Format_RGB888).copy()

    @staticmethod
    def to_gray_float(rgb):
        return (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]).astype(np.float64)

    @staticmethod
    def to_hsv(rgb):
        rgb_f = rgb.astype(np.float64) / 255.0
        r, g, b = rgb_f[:, :, 0], rgb_f[:, :, 1], rgb_f[:, :, 2]
        mx = np.max(rgb_f, axis=2)
        mn = np.min(rgb_f, axis=2)
        diff = mx - mn
        v = mx
        s = np.where(mx > 0, diff / np.maximum(mx, 1e-12), 0.0)
        h = np.zeros_like(mx)
        mask = diff > 1e-12
        m = mask & (mx == r); h[m] = (60 * ((g[m] - b[m]) / diff[m])) % 360
        m = mask & (mx == g); h[m] = 60 * ((b[m] - r[m]) / diff[m]) + 120
        m = mask & (mx == b); h[m] = 60 * ((r[m] - g[m]) / diff[m]) + 240
        return h, s, v * 255.0

    @staticmethod
    def from_hsv(h, s, v):
        h = h % 360.0
        s = np.clip(s, 0, 1)
        v = np.clip(v, 0, 255) / 255.0
        c = v * s
        x = c * (1 - np.abs((h / 60.0) % 2 - 1))
        m = v - c
        r = np.zeros_like(h); g = np.zeros_like(h); b = np.zeros_like(h)
        idx = (0 <= h) & (h < 60);   r[idx], g[idx], b[idx] = c[idx], x[idx], 0
        idx = (60 <= h) & (h < 120); r[idx], g[idx], b[idx] = x[idx], c[idx], 0
        idx = (120 <= h) & (h < 180); r[idx], g[idx], b[idx] = 0, c[idx], x[idx]
        idx = (180 <= h) & (h < 240); r[idx], g[idx], b[idx] = 0, x[idx], c[idx]
        idx = (240 <= h) & (h < 300); r[idx], g[idx], b[idx] = x[idx], 0, c[idx]
        idx = (300 <= h) & (h < 360); r[idx], g[idx], b[idx] = c[idx], 0, x[idx]
        out = np.stack([r + m, g + m, b + m], axis=2) * 255.0
        return np.clip(out, 0, 255).astype(np.uint8)