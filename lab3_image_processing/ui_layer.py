# ui_layer.py
import numpy as np
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QFileDialog, QComboBox,
                             QSlider, QGroupBox, QSpinBox)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen
from PyQt5.QtCore import Qt
from buffer_layer import BufferWrapper
from processing_layer import (gaussian_smooth, box_smooth, median_filter_3x3,
                              linear_contrast, equalize_rgb, equalize_hsv,
                              clahe, compute_histogram)


class HistogramWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.hist = None
        self.setMinimumSize(300, 150)

    def set_hist(self, hist):
        self.hist = hist
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        if self.hist is None:
            return
        w = self.width(); h = self.height()
        mx = self.hist.max()
        if mx == 0:
            return
        painter.setPen(QPen(QColor(0, 0, 0)))
        for i in range(256):
            x = int(i * w / 256)
            bar_h = int(self.hist[i] / mx * (h - 10))
            painter.drawLine(x, h - 1, x, h - 1 - bar_h)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lab 3 — Variant 2")
        self.original = None
        self.processed = None
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        images_layout = QVBoxLayout()
        self.lbl_orig = QLabel("Original")
        self.lbl_proc = QLabel("Processed")
        for lbl in (self.lbl_orig, self.lbl_proc):
            lbl.setMinimumSize(400, 400)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("border: 1px solid gray;")
            images_layout.addWidget(lbl)
        main_layout.addLayout(images_layout, 2)

        ctrl_layout = QVBoxLayout()

        btn_load = QPushButton("Load image")
        btn_load.clicked.connect(self.load_image)
        ctrl_layout.addWidget(btn_load)

        self.combo_method = QComboBox()
        self.combo_method.addItems([
            "Gaussian smooth",
            "Box smooth",
            "Median 3x3",
            "Linear contrast",
            "Equalize RGB",
            "Equalize HSV (V only)",
            "CLAHE (HSV, V only)",
        ])
        ctrl_layout.addWidget(QLabel("Method:"))
        ctrl_layout.addWidget(self.combo_method)

        self.combo_edge = QComboBox()
        self.combo_edge.addItems(["reflect", "clamp"])
        ctrl_layout.addWidget(QLabel("Edge padding:"))
        ctrl_layout.addWidget(self.combo_edge)

        self.spin_k = QSpinBox()
        self.spin_k.setRange(3, 31)
        self.spin_k.setSingleStep(2)
        self.spin_k.setValue(5)
        ctrl_layout.addWidget(QLabel("Kernel size (odd):"))
        ctrl_layout.addWidget(self.spin_k)

        self.slider_sigma = QSlider(Qt.Horizontal)
        self.slider_sigma.setRange(1, 200)
        self.slider_sigma.setValue(30)
        ctrl_layout.addWidget(QLabel("Sigma x0.1:"))
        ctrl_layout.addWidget(self.slider_sigma)

        self.spin_tile = QSpinBox()
        self.spin_tile.setRange(4, 128)
        self.spin_tile.setValue(32)
        ctrl_layout.addWidget(QLabel("CLAHE tile size:"))
        ctrl_layout.addWidget(self.spin_tile)

        self.slider_clip = QSlider(Qt.Horizontal)
        self.slider_clip.setRange(1, 100)
        self.slider_clip.setValue(20)
        ctrl_layout.addWidget(QLabel("CLAHE clip limit x0.1:"))
        ctrl_layout.addWidget(self.slider_clip)

        btn_apply = QPushButton("Apply")
        btn_apply.clicked.connect(self.apply)
        ctrl_layout.addWidget(btn_apply)

        btn_save = QPushButton("Save result")
        btn_save.clicked.connect(self.save_result)
        ctrl_layout.addWidget(btn_save)

        hist_group = QGroupBox("Histogram (gray)")
        hist_layout = QVBoxLayout()
        self.hist_orig = HistogramWidget()
        self.hist_proc = HistogramWidget()
        hist_layout.addWidget(QLabel("Original:"))
        hist_layout.addWidget(self.hist_orig)
        hist_layout.addWidget(QLabel("Processed:"))
        hist_layout.addWidget(self.hist_proc)
        hist_group.setLayout(hist_layout)
        ctrl_layout.addWidget(hist_group)

        main_layout.addLayout(ctrl_layout, 1)

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "Images (*.png *.jpg *.bmp *.jpeg)")
        if not path:
            return
        qimg = QImage(path)
        self.original = BufferWrapper.qimage_to_numpy(qimg)
        self.processed = self.original.copy()
        self._update_views()

    def _update_views(self):
        if self.original is not None:
            self.lbl_orig.setPixmap(QPixmap.fromImage(
                BufferWrapper.numpy_to_qimage(self.original)).scaled(
                self.lbl_orig.size(), Qt.KeepAspectRatio))
            gray_o = BufferWrapper.to_gray_float(self.original).astype(np.uint8)
            self.hist_orig.set_hist(compute_histogram(gray_o))
        if self.processed is not None:
            self.lbl_proc.setPixmap(QPixmap.fromImage(
                BufferWrapper.numpy_to_qimage(self.processed)).scaled(
                self.lbl_proc.size(), Qt.KeepAspectRatio))
            gray_p = BufferWrapper.to_gray_float(self.processed).astype(np.uint8)
            self.hist_proc.set_hist(compute_histogram(gray_p))

    def apply(self):
        if self.original is None:
            return
        method = self.combo_method.currentText()
        edge = self.combo_edge.currentText()
        k = self.spin_k.value()
        if k % 2 == 0:
            k += 1
        sigma = self.slider_sigma.value() / 10.0
        tile = self.spin_tile.value()
        clip = self.slider_clip.value() / 10.0

        img = self.original
        if method == "Gaussian smooth":
            out = gaussian_smooth(img, k, sigma, edge)
        elif method == "Box smooth":
            out = box_smooth(img, k, edge)
        elif method == "Median 3x3":
            out = median_filter_3x3(img)
        elif method == "Linear contrast":
            out = linear_contrast(img)
        elif method == "Equalize RGB":
            out = equalize_rgb(img)
        elif method == "Equalize HSV (V only)":
            out = equalize_hsv(img)
        elif method == "CLAHE (HSV, V only)":
            out = clahe(img, tile, clip)
        else:
            out = img
        self.processed = out
        self._update_views()

    def save_result(self):
        if self.processed is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save", "result.png", "PNG (*.png);;JPEG (*.jpg)")
        if path:
            BufferWrapper.numpy_to_qimage(self.processed).save(path)