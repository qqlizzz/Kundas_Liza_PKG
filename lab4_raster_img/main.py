import sys
import time
import random
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, QSpinBox, 
                             QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
                             QSplitter, QLineEdit, QGroupBox, QFormLayout)
from PyQt5.QtGui import QColor, QPen, QBrush, QPainter, QFont
from PyQt5.QtCore import Qt, QRectF

# Попытка импорта matplotlib для графика
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ==========================================
# 1. ВИРТУАЛЬНЫЙ РАСТР (Шаг 1)
# ==========================================
class VirtualGrid:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.grid = [[0.0 for _ in range(width)] for _ in range(height)]

    def clear(self):
        for y in range(self.height):
            for x in range(self.width):
                self.grid[y][x] = 0.0

    def set_pixel(self, x, y, intensity=1.0):
        if 0 <= x < self.width and 0 <= y < self.height:
            # Накопление интенсивности (для сглаживания)
            self.grid[y][x] = min(1.0, self.grid[y][x] + intensity)

    def get_pixel(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return 0.0

# ==========================================
# 2. АЛГОРИТМЫ (Шаг 2)
# ==========================================
class RasterEngine:
    @staticmethod
    def dda_line(x0, y0, x1, y1, target):
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            target.set_pixel(round(x0), round(y0), 1.0)
            return
        x_inc = dx / steps
        y_inc = dy / steps
        x = x0
        y = y0
        for _ in range(int(steps) + 1):
            target.set_pixel(round(x), round(y), 1.0)
            x += x_inc
            y += y_inc

    @staticmethod
    def bresenham_line(x0, y0, x1, y1, target):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            target.set_pixel(x0, y0, 1.0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    @staticmethod
    def wu_line(x0, y0, x1, y1, target):
        def fpart(x): return x - math.floor(x)
        def rfpart(x): return 1 - fpart(x)

        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0
            
        dx = x1 - x0
        dy = y1 - y0
        gradient = dy / dx if dx != 0 else 0

        # Первая конечная точка
        xend = round(x0)
        yend = y0 + gradient * (xend - x0)
        xgap = rfpart(x0 + 0.5)
        xpxl1 = xend
        ypxl1 = math.floor(yend)
        if steep:
            target.set_pixel(ypxl1, xpxl1, rfpart(yend) * xgap)
            target.set_pixel(ypxl1 + 1, xpxl1, fpart(yend) * xgap)
        else:
            target.set_pixel(xpxl1, ypxl1, rfpart(yend) * xgap)
            target.set_pixel(xpxl1, ypxl1 + 1, fpart(yend) * xgap)
        intery = yend + gradient

        # Вторая конечная точка
        xend = round(x1)
        yend = y1 + gradient * (xend - x1)
        xgap = fpart(x1 + 0.5)
        xpxl2 = xend
        ypxl2 = math.floor(yend)
        if steep:
            target.set_pixel(ypxl2, xpxl2, rfpart(yend) * xgap)
            target.set_pixel(ypxl2 + 1, xpxl2, fpart(yend) * xgap)
        else:
            target.set_pixel(xpxl2, ypxl2, rfpart(yend) * xgap)
            target.set_pixel(xpxl2, ypxl2 + 1, fpart(yend) * xgap)

        # Основной цикл
        if steep:
            for x in range(xpxl1 + 1, xpxl2):
                target.set_pixel(math.floor(intery), x, rfpart(intery))
                target.set_pixel(math.floor(intery) + 1, x, fpart(intery))
                intery += gradient
        else:
            for x in range(xpxl1 + 1, xpxl2):
                target.set_pixel(x, math.floor(intery), rfpart(intery))
                target.set_pixel(x, math.floor(intery) + 1, fpart(intery))
                intery += gradient

    @staticmethod
    def bresenham_circle(xc, yc, r, target):
        x = 0
        y = r
        d = 3 - 2 * r
        while y >= x:
            target.set_pixel(xc + x, yc + y, 1.0)
            target.set_pixel(xc - x, yc + y, 1.0)
            target.set_pixel(xc + x, yc - y, 1.0)
            target.set_pixel(xc - x, yc - y, 1.0)
            target.set_pixel(xc + y, yc + x, 1.0)
            target.set_pixel(xc - y, yc + x, 1.0)
            target.set_pixel(xc + y, yc - x, 1.0)
            target.set_pixel(xc - y, yc - x, 1.0)
            if d < 0:
                d = d + 4 * x + 6
            else:
                d = d + 4 * (x - y) + 10
                y -= 1
            x += 1

    @staticmethod
    def castle_piteway_ellipse(xc, yc, rx, ry, target):
        """Целочисленный алгоритм Кастла-Питвея для эллипса (дуги)"""
        x = 0
        y = ry
        # Начальное значение решающей функции
        d1 = (ry * ry) - (rx * rx * ry) + (0.25 * rx * rx)
        dx = 2 * ry * ry * x
        dy = 2 * rx * rx * y

        # Первая часть дуги
        while dx < dy:
            # Рисуем 4 симметричные точки
            target.set_pixel(xc + x, yc + y, 1.0)
            target.set_pixel(xc - x, yc + y, 1.0)
            target.set_pixel(xc + x, yc - y, 1.0)
            target.set_pixel(xc - x, yc - y, 1.0)

            if d1 < 0:
                x += 1
                dx += 2 * ry * ry
                d1 += dx + (ry * ry)
            else:
                x += 1
                y -= 1
                dx += 2 * ry * ry
                dy -= 2 * rx * rx
                d1 += dx - dy + (ry * ry)

        # Вторая часть дуги
        d2 = ((ry * ry) * ((x + 0.5) * (x + 0.5))) + \
             ((rx * rx) * ((y - 1) * (y - 1))) - \
             (rx * rx * ry * ry)

        while y >= 0:
            target.set_pixel(xc + x, yc + y, 1.0)
            target.set_pixel(xc - x, yc + y, 1.0)
            target.set_pixel(xc + x, yc - y, 1.0)
            target.set_pixel(xc - x, yc - y, 1.0)

            if d2 > 0:
                y -= 1
                dy -= 2 * rx * rx
                d2 += (rx * rx) - dy
            else:
                y -= 1
                x += 1
                dx += 2 * ry * ry
                dy -= 2 * rx * rx
                d2 += dx - dy + (rx * rx)

# ==========================================
# 3. ОТРИСОВКА (UI)
# ==========================================
class GridPainter(QGraphicsView):
    def __init__(self, grid, parent=None):
        super().__init__(parent)
        self.grid = grid
        self.pixel_size = 1
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing, False) # Отключаем сглаживание для четкости пикселей
        self.render_grid()

    def set_pixel_size(self, size):
        self.pixel_size = size
        self.render_grid()

    def render_grid(self):
        self.scene.clear()
        w = self.grid.width
        h = self.grid.height
        
        # 1. Сетка (если масштаб достаточно большой)
        if self.pixel_size >= 5:
            grid_pen = QPen(QColor(220, 220, 220))
            step = 10  # Каждые 10 пикселей
            for x in range(0, w, step):
                self.scene.addLine(x * self.pixel_size, 0, x * self.pixel_size, h * self.pixel_size, grid_pen)
            for y in range(0, h, step):
                self.scene.addLine(0, y * self.pixel_size, w * self.pixel_size, y * self.pixel_size, grid_pen)

        # 2. Пиксели
        for y in range(h):
            for x in range(w):
                intensity = self.grid.get_pixel(x, y)
                if intensity > 0:
                    rect = QRectF(x * self.pixel_size, y * self.pixel_size, self.pixel_size, self.pixel_size)
                    color = QColor(0, 0, 0, int(255 * intensity))
                    self.scene.addRect(rect, QPen(Qt.NoPen), QBrush(color))
        
        # 3. Оси координат
        axis_pen_x = QPen(Qt.red, 2)
        axis_pen_y = QPen(Qt.green, 2)
        # Ось X (сверху, так как экранная Y растет вниз)
        self.scene.addLine(0, 0, w * self.pixel_size, 0, axis_pen_x)
        # Ось Y (слева)
        self.scene.addLine(0, 0, 0, h * self.pixel_size, axis_pen_y)

        # Подписи (для наглядности)
        font = QFont("Arial", 10)
        text_x = self.scene.addText("X", font)
        text_x.setPos(w * self.pixel_size - 20, 5)
        text_x.setDefaultTextColor(Qt.red)
        
        text_y = self.scene.addText("Y", font)
        text_y.setPos(5, h * self.pixel_size - 20)
        text_y.setDefaultTextColor(Qt.green)

        self.scene.setSceneRect(0, 0, w * self.pixel_size, h * self.pixel_size)
        self.setSceneRect(0, 0, w * self.pixel_size, h * self.pixel_size)

# ==========================================
# 4. ГЛАВНОЕ ОКНО
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ЛР4 - Базовые растровые алгоритмы (Полная версия)")
        self.resize(1200, 700)
        self.grid = VirtualGrid(800, 600)
        self.painter = GridPainter(self.grid)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central) # Основной слой - горизонтальный

        # --- ЛЕВАЯ ПАНЕЛЬ (Управление) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Выбор алгоритма
        algo_group = QGroupBox("Алгоритм")
        algo_layout = QVBoxLayout(algo_group)
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["ЦДА (DDA)", "Брезенхем (Линия)", "Ву (Сглаживание)", 
                                  "Брезенхем (Окружность)", "Кастл-Питвей (Эллипс)"])
        algo_layout.addWidget(self.algo_combo)
        left_layout.addWidget(algo_group)

        # Ввод координат
        coord_group = QGroupBox("Параметры")
        coord_layout = QFormLayout(coord_group)
        
        self.in_x1 = QLineEdit("50")
        self.in_y1 = QLineEdit("50")
        self.in_x2 = QLineEdit("750")
        self.in_y2 = QLineEdit("550")
        self.in_r = QLineEdit("200") # Для окружности/эллипса
        
        coord_layout.addRow("X1 / X центра:", self.in_x1)
        coord_layout.addRow("Y1 / Y центра:", self.in_y1)
        coord_layout.addRow("X2 / Радиус X:", self.in_x2)
        coord_layout.addRow("Y2 / Радиус Y:", self.in_y2)
        # self.in_r не используем отдельно, замапили на X2/Y2 для эллипса
        
        left_layout.addWidget(coord_group)

        # Кнопки
        btn_layout = QVBoxLayout()
        self.btn_draw = QPushButton("Нарисовать")
        self.btn_draw.clicked.connect(self.draw_demo)
        btn_layout.addWidget(self.btn_draw)

        self.btn_bench = QPushButton("Бенчмарк (100k линий + 50k окр.)")
        self.btn_bench.clicked.connect(self.run_benchmark)
        btn_layout.addWidget(self.btn_bench)

        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.clicked.connect(self.clear_grid)
        btn_layout.addWidget(self.btn_clear)
        
        left_layout.addLayout(btn_layout)

        # Масштаб
        zoom_group = QGroupBox("Масштаб")
        zoom_layout = QHBoxLayout(zoom_group)
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(1, 20)
        self.zoom_spin.setValue(1)
        self.zoom_spin.valueChanged.connect(self.change_zoom)
        zoom_layout.addWidget(QLabel("Размер пикселя:"))
        zoom_layout.addWidget(self.zoom_spin)
        left_layout.addWidget(zoom_group)

        # Информация
        self.info_label = QLabel("Время: --")
        self.info_label.setStyleSheet("font-weight: bold; color: blue;")
        left_layout.addWidget(self.info_label)
        
        # Пояснение (сглаживание)
        help_text = QLabel("Примечание: при алгоритме Ву интенсивность пикселя\n(альфа-канал) зависит от дробной части координаты.\nЧерные пиксели - основная линия, серые - сглаживание.")
        help_text.setWordWrap(True)
        left_layout.addWidget(help_text)

        left_layout.addStretch() # Прижимаем все вверх
        left_panel.setFixedWidth(300)

        # --- ПРАВАЯ ПАНЕЛЬ (Холст и График) ---
        right_panel = QSplitter(Qt.Vertical)
        
        # Холст
        right_panel.addWidget(self.painter)
        
        # График (если установлен matplotlib)
        if HAS_MATPLOTLIB:
            self.figure = Figure(figsize=(5, 2), tight_layout=True)
            self.canvas = FigureCanvas(self.figure)
            right_panel.addWidget(self.canvas)
        else:
            self.graph_placeholder = QLabel("Для отображения графика установите matplotlib:\npip install matplotlib")
            self.graph_placeholder.setAlignment(Qt.AlignCenter)
            right_panel.addWidget(self.graph_placeholder)

        right_panel.setSizes([500, 200])

        layout.addWidget(left_panel)
        layout.addWidget(right_panel)

    def clear_grid(self):
        self.grid.clear()
        self.painter.render_grid()

    def change_zoom(self):
        self.painter.set_pixel_size(self.zoom_spin.value())

    def draw_demo(self):
        self.grid.clear()
        algo = self.algo_combo.currentText()
        
        try:
            x1 = int(self.in_x1.text())
            y1 = int(self.in_y1.text())
            x2 = int(self.in_x2.text())
            y2 = int(self.in_y2.text())
        except ValueError:
            self.info_label.setText("Ошибка: введите целые числа в поля координат!")
            return

        start = time.perf_counter()

        if algo == "ЦДА (DDA)":
            RasterEngine.dda_line(x1, y1, x2, y2, self.grid)
        elif algo == "Брезенхем (Линия)":
            RasterEngine.bresenham_line(x1, y1, x2, y2, self.grid)
        elif algo == "Ву (Сглаживание)":
            RasterEngine.wu_line(x1, y1, x2, y2, self.grid)
        elif algo == "Брезенхем (Окружность)":
            # Используем X1, Y1 как центр, X2 как радиус
            RasterEngine.bresenham_circle(x1, y1, abs(x2), self.grid)
        elif algo == "Кастл-Питвей (Эллипс)":
            # Используем X1, Y1 как центр, X2, Y2 как радиусы
            RasterEngine.castle_piteway_ellipse(x1, y1, abs(x2), abs(y2), self.grid)

        elapsed = (time.perf_counter() - start) * 1000
        self.info_label.setText(f"Время: {elapsed:.3f} мс")
        self.painter.render_grid()

    def run_benchmark(self):
        self.grid.clear()
        
        # Для графика будем собирать данные
        num_points = [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]
        times = []

        # Прогрев (чтобы кэш процессора не влиял на первый замер)
        for _ in range(1000):
            RasterEngine.bresenham_line(0, 0, 10, 10, self.grid)

        for n in num_points:
            start = time.perf_counter()
            # Генерация n случайных линий
            for _ in range(n):
                x0 = random.randint(0, 799)
                y0 = random.randint(0, 599)
                x1 = random.randint(0, 799)
                y1 = random.randint(0, 599)
                RasterEngine.bresenham_line(x0, y0, x1, y1, self.grid)
            
            # И еще немного окружностей (пропорционально)
            for _ in range(n // 2):
                xc = random.randint(0, 799)
                yc = random.randint(0, 599)
                r = random.randint(1, 100)
                RasterEngine.bresenham_circle(xc, yc, r, self.grid)
                
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            
            # Обновляем лейбл, чтобы не казалось, что прога зависла
            self.info_label.setText(f"Бенчмарк... {n} линий: {elapsed:.1f} мс")
            QApplication.processEvents() # Даем UI обновиться

        # Итоговый результат
        total_time = times[-1]
        self.info_label.setText(f"Бенчмарк (100k линий + 50k окр.): {total_time:.2f} мс")
        self.painter.render_grid()

        # Строим график
        if HAS_MATPLOTLIB:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.plot(num_points, times, 'b-o', label='Время выполнения')
            ax.set_title('Зависимость времени от количества примитивов')
            ax.set_xlabel('Количество линий (шт)')
            ax.set_ylabel('Время (мс)')
            ax.grid(True)
            ax.legend()
            self.canvas.draw()
        else:
            self.info_label.setText(self.info_label.text() + " (Установите matplotlib для графика)")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())