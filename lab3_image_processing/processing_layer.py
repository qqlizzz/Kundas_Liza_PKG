# processing_layer.py
import numpy as np
from buffer_layer import EdgePadding


def _pad(img, pad, mode):
    return EdgePadding.clamp(img, pad) if mode == 'clamp' else EdgePadding.reflect(img, pad)


def _conv1d_h(img, kernel, mode):
    k = len(kernel); pad = k // 2
    padded = _pad(img, pad, mode)
    h, w, c = img.shape
    out = np.zeros((h, w, c), dtype=np.float64)
    for i, wt in enumerate(kernel):
        out += padded[:, i:i + w, :] * wt
    return out


def _conv1d_v(img, kernel, mode):
    k = len(kernel); pad = k // 2
    padded = _pad(img, pad, mode)
    h, w, c = img.shape
    out = np.zeros((h, w, c), dtype=np.float64)
    for i, wt in enumerate(kernel):
        out += padded[i:i + h, :, :] * wt
    return out


def make_box_kernel(k):
    return np.ones(k, dtype=np.float64) / k


def make_gaussian_kernel(k, sigma):
    half = k // 2
    x = np.arange(-half, half + 1, dtype=np.float64)
    g = np.exp(-(x * x) / (2.0 * sigma * sigma))
    return g / g.sum()


def separable_convolution(img, kernel_1d, pad_mode='reflect'):
    tmp = _conv1d_h(img.astype(np.float64), kernel_1d, pad_mode)
    out = _conv1d_v(tmp, kernel_1d, pad_mode)
    return np.clip(out, 0, 255).astype(np.uint8)


def gaussian_smooth(img, k, sigma, pad_mode='reflect'):
    return separable_convolution(img, make_gaussian_kernel(k, sigma), pad_mode)


def box_smooth(img, k, pad_mode='reflect'):
    return separable_convolution(img, make_box_kernel(k), pad_mode)


def median_filter_3x3(img):
    h, w, c = img.shape
    padded = EdgePadding.reflect(img, 1)
    out = np.zeros((h, w, c), dtype=np.uint8)
    for ch in range(c):
        win = np.stack([
            padded[dy:dy + h, dx:dx + w, ch]
            for dy in range(3) for dx in range(3)
        ], axis=0)
        out[:, :, ch] = np.median(win, axis=0).astype(np.uint8)
    return out


def linear_contrast(img, low_pct=2.0, high_pct=98.0):
    out = np.zeros_like(img)
    for ch in range(3):
        ch_data = img[:, :, ch].astype(np.float64)
        lo = np.percentile(ch_data, low_pct)
        hi = np.percentile(ch_data, high_pct)
        if hi - lo < 1e-6:
            out[:, :, ch] = img[:, :, ch]
            continue
        out[:, :, ch] = np.clip((ch_data - lo) * 255.0 / (hi - lo), 0, 255).astype(np.uint8)
    return out


def compute_histogram(channel):
    return np.bincount(channel.ravel(), minlength=256).astype(np.int64)


def build_cdf(hist):
    cdf = np.cumsum(hist).astype(np.float64)
    if cdf[-1] == 0:
        return cdf
    return cdf / cdf[-1]


def equalize_hist_channel(channel):
    hist = compute_histogram(channel)
    cdf = build_cdf(hist)
    lut = np.clip(np.round(cdf * 255), 0, 255).astype(np.uint8)
    return lut[channel]


def equalize_rgb(img):
    out = np.zeros_like(img)
    for ch in range(3):
        out[:, :, ch] = equalize_hist_channel(img[:, :, ch])
    return out


def equalize_hsv(img):
    from buffer_layer import BufferWrapper
    h, s, v = BufferWrapper.to_hsv(img)
    v_eq = equalize_hist_channel(np.clip(v, 0, 255).astype(np.uint8))
    return BufferWrapper.from_hsv(h, s, v_eq.astype(np.float64))


def clahe_channel(channel, tile_size=32, clip_limit=2.0):
    h, w = channel.shape
    n_tiles_y = max(1, h // tile_size)
    n_tiles_x = max(1, w // tile_size)
    tile_h = h // n_tiles_y
    tile_w = w // n_tiles_x
    luts = np.zeros((n_tiles_y, n_tiles_x, 256), dtype=np.uint8)
    for ty in range(n_tiles_y):
        for tx in range(n_tiles_x):
            y0 = ty * tile_h
            x0 = tx * tile_w
            y1 = y0 + tile_h if ty < n_tiles_y - 1 else h
            x1 = x0 + tile_w if tx < n_tiles_x - 1 else w
            tile = channel[y0:y1, x0:x1]
            hist = np.bincount(tile.ravel(), minlength=256).astype(np.float64)
            total = hist.sum()
            limit = clip_limit * total / 256.0
            excess = np.maximum(hist - limit, 0).sum()
            hist = np.minimum(hist, limit)
            hist += excess / 256.0
            cdf = np.cumsum(hist)
            if cdf[-1] > 0:
                cdf = cdf / cdf[-1]
            luts[ty, tx] = np.clip(np.round(cdf * 255), 0, 255).astype(np.uint8)
    out = np.zeros_like(channel, dtype=np.float64)
    ys = np.arange(h); xs = np.arange(w)
    ty_f = (ys / tile_h).astype(int).clip(0, n_tiles_y - 1)
    tx_f = (xs / tile_w).astype(int).clip(0, n_tiles_x - 1)
    fy = (ys / tile_h) - ty_f
    fx = (xs / tile_w) - tx_f
    ty_n = np.clip(ty_f + 1, 0, n_tiles_y - 1)
    tx_n = np.clip(tx_f + 1, 0, n_tiles_x - 1)
    for yy in range(h):
        ty = ty_f[yy]; ty2 = ty_n[yy]; wy = fy[yy]
        for xx in range(w):
            tx = tx_f[xx]; tx2 = tx_n[xx]; wx = fx[xx]
            val = channel[yy, xx]
            v00 = luts[ty, tx, val]; v01 = luts[ty, tx2, val]
            v10 = luts[ty2, tx, val]; v11 = luts[ty2, tx2, val]
            top = v00 * (1 - wx) + v01 * wx
            bot = v10 * (1 - wx) + v11 * wx
            out[yy, xx] = top * (1 - wy) + bot * wy
    return np.clip(out, 0, 255).astype(np.uint8)


def clahe(img, tile_size=32, clip_limit=2.0):
    from buffer_layer import BufferWrapper
    h, s, v = BufferWrapper.to_hsv(img)
    v_eq = clahe_channel(np.clip(v, 0, 255).astype(np.uint8), tile_size, clip_limit)
    return BufferWrapper.from_hsv(h, s, v_eq.astype(np.float64))