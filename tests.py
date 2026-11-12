import unittest
from model import (
    rgb_to_cmyk,
    cmyk_to_rgb,
    rgb_to_hls,
    hls_to_rgb,
    rgb_to_cmyk_ucr,
    rgb_to_cmyk_gcr,
)


class TestColorMath(unittest.TestCase):
    def test_rgb_to_cmyk_red(self):
        c, m, y, k = rgb_to_cmyk(255, 0, 0)
        self.assertAlmostEqual(c, 0.0, places=4)
        self.assertAlmostEqual(m, 1.0, places=4)
        self.assertAlmostEqual(y, 1.0, places=4)
        self.assertAlmostEqual(k, 0.0, places=4)

    def test_cmyk_to_rgb_red(self):
        r, g, b = cmyk_to_rgb(0.0, 1.0, 1.0, 0.0)
        self.assertAlmostEqual(r, 255.0, places=4)
        self.assertAlmostEqual(g, 0.0, places=4)
        self.assertAlmostEqual(b, 0.0, places=4)

    def test_rgb_to_hls_red(self):
        h, l, s = rgb_to_hls(255, 0, 0)
        self.assertAlmostEqual(h, 0.0, places=4)
        self.assertAlmostEqual(l, 0.5, places=4)
        self.assertAlmostEqual(s, 1.0, places=4)

    def test_hls_to_rgb_red(self):
        r, g, b = hls_to_rgb(0.0, 0.5, 1.0)
        self.assertAlmostEqual(r, 255.0, places=4)
        self.assertAlmostEqual(g, 0.0, places=4)
        self.assertAlmostEqual(b, 0.0, places=4)

    def test_rgb_to_cmyk_white(self):
        c, m, y, k = rgb_to_cmyk(255, 255, 255)
        self.assertAlmostEqual(c, 0.0, places=4)
        self.assertAlmostEqual(m, 0.0, places=4)
        self.assertAlmostEqual(y, 0.0, places=4)
        self.assertAlmostEqual(k, 0.0, places=4)

    def test_rgb_to_cmyk_black(self):
        c, m, y, k = rgb_to_cmyk(0, 0, 0)
        self.assertAlmostEqual(k, 1.0, places=4)

    def test_rgb_to_hls_green(self):
        h, l, s = rgb_to_hls(0, 255, 0)
        self.assertAlmostEqual(h, 120.0, places=4)
        self.assertAlmostEqual(l, 0.5, places=4)
        self.assertAlmostEqual(s, 1.0, places=4)

    def test_rgb_to_hls_blue(self):
        h, l, s = rgb_to_hls(0, 0, 255)
        self.assertAlmostEqual(h, 240.0, places=4)

    def test_ucr_black(self):
        c, m, y, k = rgb_to_cmyk_ucr(0, 0, 0)
        self.assertAlmostEqual(k, 1.0, places=4)

    def test_gcr_black(self):
        c, m, y, k = rgb_to_cmyk_gcr(0, 0, 0)
        self.assertAlmostEqual(k, 1.0, places=4)

    def test_gcr_gray(self):
        c, m, y, k = rgb_to_cmyk_gcr(128, 128, 128)
        self.assertAlmostEqual(c, 0.0, places=4)
        self.assertAlmostEqual(m, 0.0, places=4)
        self.assertAlmostEqual(y, 0.0, places=4)
        self.assertGreater(k, 0.0)


if __name__ == "__main__":
    unittest.main()