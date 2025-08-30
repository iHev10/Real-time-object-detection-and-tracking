from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QRadialGradient, QBrush
from PyQt6.QtCore import Qt, QPoint, QTimer
import sys
import math

class RadarWidget(QWidget):
    def __init__(self):
        super().__init__()
        # self.setMinimumSize(400, 400)
        self.sweep_angle = 0
        self.trail_points = []
        self.tracker_mode = 0
        self.target_angles = []

        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_sweep)
        self.timer.start(16)

    def set_radar_data(self, radar_data):
        self.tracker_mode = radar_data.get("trc_mode", 0)
        self.target_angles = radar_data.get("tg_locs", [])
        self.update()

    def animate_sweep(self):
        self.sweep_angle = (self.sweep_angle + 3) % 360
        rad = math.radians(self.sweep_angle + 90)
        center = QPoint(self.width() // 2, self.height() // 2)
        radius = min(self.width(), self.height()) // 2 - 40
        self.trail_points.append((center.x() + radius * math.cos(rad),
                                  center.y() + radius * math.sin(rad)))
        if len(self.trail_points) > 20:
            self.trail_points.pop(0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPoint(self.width() // 2, self.height() // 2)
        radius = min(self.width(), self.height()) // 2 - 40

        # Background
        gradient = QRadialGradient(center.x(), center.y(), radius + 50)
        gradient.setColorAt(0, QColor(30, 40, 60))
        gradient.setColorAt(0.7, QColor(10, 20, 30))
        gradient.setColorAt(1, QColor(5, 10, 10))
        painter.fillRect(self.rect(), QBrush(gradient))

        # Grid points
        painter.setPen(QPen(QColor(0, 255, 255, 20), 1))
        for r in range(1, 6):
            for angle in range(0, 360, 10):
                rad = math.radians(angle + 90)
                x = center.x() + (radius * r // 5) * math.cos(rad)
                y = center.y() + (radius * r // 5) * math.sin(rad)
                painter.drawPoint(int(x), int(y))

        # Radar circles
        for r in range(1, 6):
            alpha = 100 if r == 5 else 50
            painter.setPen(QPen(QColor(0, 255, 255, alpha), 2.5))
            painter.drawEllipse(center, radius * r // 5, radius * r // 5)

        # Degree lines and labels (0° at bottom, clockwise)
        for angle in range(0, 360, 15):
            rad = math.radians(angle + 90)
            x = center.x() + radius * math.cos(rad)
            y = center.y() + radius * math.sin(rad)
            painter.setPen(QPen(QColor(0, 255, 255, 60), 1.5))
            painter.drawLine(center, QPoint(int(x), int(y)))

            if angle % 30 == 0:
                label_x = center.x() + (radius + 20) * math.cos(rad)
                label_y = center.y() + (radius + 20) * math.sin(rad)
                painter.setPen(QPen(QColor(180, 255, 255, 180)))
                painter.setFont(QFont("Arial", 10))
                painter.drawText(int(label_x) - 12, int(label_y) + 6, f"{angle}°")

        # Sweep animation
        steps = 300
        fade_span = 60
        for i in range(steps):
            fade_angle = self.sweep_angle - (fade_span * i / steps)
            fade_rad = math.radians(fade_angle + 90)
            x = center.x() + radius * math.cos(fade_rad)
            y = center.y() + radius * math.sin(fade_rad)
            alpha = int(200 * (1 - i / steps))
            color = QColor(0, 255, 180, alpha)
            painter.setPen(QPen(color, 2))
            painter.drawLine(center, QPoint(int(x), int(y)))

        for angle in self.target_angles:
            rad = math.radians(angle + 90)
            x = center.x() + radius * math.cos(rad)
            y = center.y() + radius * math.sin(rad)
            pulse_size = 12 + 5 * math.sin(self.sweep_angle * math.pi / 90)

            if self.tracker_mode == 0:
                fill_color = QColor(0, 255, 0, 220)  # سبز
                border_color = QColor(0, 255, 0, 150)
                core_color = QColor(200, 255, 200, 200)
            else:
                fill_color = QColor(255, 0, 0, 230)  # قرمز
                border_color = QColor(255, 100, 100, 150)
                core_color = QColor(255, 180, 180, 220)

            painter.setBrush(fill_color)
            painter.setPen(QPen(border_color, 3))
            painter.drawEllipse(QPoint(int(x), int(y)), int(pulse_size), int(pulse_size))

            painter.setBrush(core_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(int(x), int(y)), 8, 8)

        # Center glow
        painter.setBrush(QColor(0, 255, 255, 100))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, 20, 20)
        painter.setBrush(QColor(0, 255, 255, 255))
        painter.drawEllipse(center, 8, 8)


class RadarUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("360° Radar Viewer")
        self.setStyleSheet("background-color: #0f1419;")
        self.radar = RadarWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.radar)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
        self.resize(600, 650)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RadarUI()

    # radar_data = {
    #     "trc_mode": 0,
    #     "tg_locs": [45, 120, 300]
    # }

    radar_data = {
        "trc_mode": 1,
        "tg_locs": [180]
    }

    window.radar.set_radar_data(radar_data)
    window.show()
    sys.exit(app.exec())
