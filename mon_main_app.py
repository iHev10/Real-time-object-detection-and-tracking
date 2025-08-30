from camera import CameraThread
from mon_process import ProcessingThread
from send_socket_1 import SocketThread1
from send_socket_2 import SocketThread2
from sonycamera import CameraSettingsUI
from radar import RadarWidget

import cv2 as cv
import sys
import yaml
import os

from PyQt6.QtCore import QTimer, QTime, QRect, QPoint, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QPen
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QLabel, QVBoxLayout, QLineEdit


with open('config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.SafeLoader)

try:
    from PyQt6.uic import loadUiType
    main_ui, _ = loadUiType('ui/p_gui.ui')
except Exception as e:
    print(f"Error loading UI: {e}")
    sys.exit(1)


class DrawableQLabel(QLabel):
    roi_selected = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pixmap = QPixmap()
        self.setMouseTracking(True)
        self.drawing = False
        self.start_point = QPoint()
        self.current_rect = QRect()
        self._frame_size = (config["CAMERA"]["WIDTH"], config["CAMERA"]["HEIGHT"])
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        overlay_path = "ui/icons/r3.png"
        if os.path.exists(overlay_path):
            self.overlay = QPixmap(overlay_path)
        else:
            print(f"Overlay image not found: {overlay_path}")
            self.overlay = QPixmap()

        self.show_overlay = False

    def set_overlay_visible(self, visible):
        self.show_overlay = visible
        self.update()

    def setPixmap(self, pixmap):
        self.current_pixmap = pixmap
        self.update()

    def set_frame_size(self, width, height):
        self._frame_size = (width, height)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.current_rect = QRect(self.start_point, self.start_point)
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.current_rect = QRect(
                self.start_point, event.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if self.drawing:
            self.drawing = False
            widget_w = self.width()
            widget_h = self.height()

            x = int(self.current_rect.x() * (self._frame_size[0] / widget_w))
            y = int(self.current_rect.y() * (self._frame_size[1] / widget_h))
            w = int(self.current_rect.width() *
                    (self._frame_size[0] / widget_w))
            h = int(self.current_rect.height() *
                    (self._frame_size[1] / widget_h))

            self.roi_selected.emit(QRect(x, y, w, h))
            self.current_rect = QRect()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.current_pixmap.isNull():
            scaled_pix = self.current_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            x_offset = (self.width() - scaled_pix.width()) // 2
            y_offset = (self.height() - scaled_pix.height()) // 2

            painter.drawPixmap(x_offset, y_offset, scaled_pix)

            if self.show_overlay and not self.overlay.isNull():
                overlay_size = scaled_pix.width() // 10
                scaled_overlay = self.overlay.scaled(
                    overlay_size, overlay_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                overlay_x = x_offset + \
                    (scaled_pix.width() - scaled_overlay.width()) // 2
                overlay_y = y_offset + \
                    (scaled_pix.height() - scaled_overlay.height()) // 2
                painter.drawPixmap(overlay_x, overlay_y, scaled_overlay)

        if self.drawing and not self.current_rect.isNull():
            painter.setPen(QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine))
            painter.drawRect(self.current_rect)


class RadarWrapper(RadarWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setParent(parent)
        

class MainApp(QMainWindow, main_ui):
    def __init__(self):
        super().__init__()
        self._frame_size = (config["CAMERA"]["WIDTH"], config["CAMERA"]["HEIGHT"])
        self.setupUi(self)

        old_label = self.findChild(QLabel, "DET_L")
        if old_label:
            parent_widget = old_label.parent()

            if not parent_widget.layout():
                parent_widget.setLayout(QVBoxLayout())
                parent_widget.layout().setContentsMargins(0, 0, 0, 0)

            self.DET_L = DrawableQLabel()
            self.DET_L.set_frame_size(
                self._frame_size[0], self._frame_size[1])

            parent_widget.layout().addWidget(self.DET_L)
            old_label.deleteLater()
        else:
            self.DET_L = DrawableQLabel()
            self.setCentralWidget(self.DET_L)

        self.video_width = 1600
        self.video_height = 900

        self.frames = 0
        self.counts = {k: 0 for k in config["DETECTION"]["CLASSES_DICT"].keys()}

        self.camera_thread = CameraThread(
            video_source=config["CAMERA"]["VIDEO_SOURCE"])
        self.processing_thread = ProcessingThread()
        self.socket_thread_1 = SocketThread1()
        self.socket_thread_2 = SocketThread2()

        self.camera_thread.frame_ready.connect(self.handle_raw_frame)
        self.processing_thread.processed_frame.connect(self.update_ui)
        self.processing_thread.detecting_data_ready.connect(
            self.handle_detecting_data)

        self.clock = QTimer(self)
        self.clock.timeout.connect(self.update_time)
        self.clock.start(1000)

        self.setup_ui_connections()
        
        self.cam_set_dlg = CameraSettingsUI()
        
        self.radar_widget = RadarWrapper(self)
        self.radar_widget.setGeometry(1630, 250, 230, 230)

        # radar_data = {
        #     "trc_mode": 1, 
        #     "tg_locs": [45, 120, 300] 
        # }
        # self.radar_widget.set_radar_data(radar_data)

    def force_resize(self):
        self.DET_L.resize(self.DET_L.parent().size())

    def setup_ui_connections(self):
        
        self.START_DET.toggled.connect(self.start_camera)
        self.START_DET.setShortcut("d")
        self.TARGET.setShortcut("t")
        self.T_SETTINGS_APPLY.setShortcut("p")

        self.TILT_BAR.valueChanged.connect(self.tilt_set)

        self.TARGET.toggled.connect(self.update_classes)

        self.right_left = 0
        self.RIGHT.pressed.connect(lambda: self.right_button_pressed(1))
        self.RIGHT.released.connect(self.right_button_released)
        self.LEFT.pressed.connect(lambda: self.left_button_pressed(-1))
        self.LEFT.released.connect(self.left_button_released)

        self.up_down = 0
        self.UP.pressed.connect(lambda: self.up_button_pressed(1))
        self.UP.released.connect(self.up_button_released)
        self.DOWN.pressed.connect(lambda: self.down_button_pressed(-1))
        self.DOWN.released.connect(self.down_button_released)

        self.tilt_apply = 0
        self.T_SETTINGS_APPLY.pressed.connect(lambda: self.t_apply_pressed(1))
        self.T_SETTINGS_APPLY.released.connect(self.t_apply_released)
        
        self.CAMERA_SET.clicked.connect(self.cam_settings)

    def mouse_press_event(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.current_rect = QRect(self.start_point, self.start_point)
            self.DET_L.update()

    def mouse_move_event(self, event):
        if self.drawing:
            self.current_rect = QRect(
                self.start_point, event.pos()).normalized()
            self.DET_L.update()

    def mouse_release_event(self, event):
        if self.drawing:
            self.drawing = False
            widget_w = self.DET_L.width()
            widget_h = self.DET_L.height()

            x = int(self.current_rect.x() * (self.video_width / widget_w))
            y = int(self.current_rect.y() * (self.video_height / widget_h))
            w = int(self.current_rect.width() * (self.video_width / widget_w))
            h = int(self.current_rect.height() *
                    (self.video_height / widget_h))

            self.processing_thread.set_manual_roi((x, y, w, h))
            self.current_rect = QRect()
            self.DET_L.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if hasattr(self, 'current_rect') and self.drawing:
            painter = QPainter(self.DET_L)
            painter.setPen(QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine))
            painter.drawRect(self.current_rect)

    def update_time(self):
        self.TIME.setText(QTime.currentTime().toString("hh:mm:ss"))

    def tilt_set(self):
        self.TILT_DEG.setText(str(self.TILT_BAR.value()))

    @pyqtSlot()
    def right_button_pressed(self, value):
        self.right_left = value
        return self.right_left

    @pyqtSlot()
    def right_button_released(self):
        self.right_left = 0
        return self.right_left

    @pyqtSlot()
    def left_button_pressed(self, value):
        self.right_left = value
        return self.right_left

    @pyqtSlot()
    def left_button_released(self):
        self.right_left = 0
        return self.right_left

    @pyqtSlot()
    def up_button_pressed(self, value):
        self.up_down = value
        return self.up_down

    @pyqtSlot()
    def up_button_released(self):
        self.up_down = 0
        return self.up_down

    @pyqtSlot()
    def down_button_pressed(self, value):
        self.up_down = value
        return self.up_down

    @pyqtSlot()
    def down_button_released(self):
        self.up_down = 0
        return self.up_down

    @pyqtSlot()
    def t_apply_pressed(self, value):
        self.tilt_apply = value
        return self.tilt_apply

    @pyqtSlot()
    def t_apply_released(self):
        self.tilt_apply = 0
        return self.tilt_apply
    
    def cam_settings(self):
        self.cam_set_dlg.show()
        
    # def closeEvent(self, event):
    #     event.accept()    
        
    def closeEvent(self, event):
        if hasattr(self, 'cam_set_dlg') and self.cam_set_dlg.isVisible():
            self.cam_set_dlg.close()
        event.accept()    

    def list_classes(self):
        if self.START_DET.isChecked():
            return [cls for cls, btn in enumerate([self.TARGET, self.TARGET, self.TARGET, self.TARGET]) if btn.isChecked()]
        else:
            return []

    def handle_raw_frame(self, frame):
        if frame is not None:
            self.processing_thread.add_frame(frame)
        else:
            QMessageBox.warning(self, "خطا", "دوربین در دسترس نیست!")


###################################################################################

    def handle_detecting_data(self, detecting_data):

        combined_data_s1 = {
            **detecting_data,
            "monitoring_mode": int(self.START_DET.isChecked()),
            "change_tilt": int(self.tilt_apply),
            "max_tilt": self.TILT_BAR.value(),
            "manual_monitoring": int(self.MANUAL_MON.isChecked()),
            "right_left": self.right_left,
            "up_down": self.up_down,
            "pan_speed": int(self.MAN_PAN_SPEED.value()),
            "tilt_speed": int(self.MAN_TILT_SPEED.value()),
        }
        # try:
        #     pan = int(float(self.socket_thread_1.pan_tilt_ang.split("_")[0]))
        #     tilt = int(float(self.socket_thread_1.pan_tilt_ang.split("_")[1]))
        #     self.PAN.setValue(pan)
        #     self.TILT.setValue(tilt)

        #     radar_pan = (pan + 360) % 360
            
        #     flag = self.counts["target"] > 0
            
        #     radar_data = {
        #     "trc_mode": 1 if flag else 0,  ########################################## I SHOULD CHANGE THIS PART
        #     "tg_locs": [radar_pan]  
        #     }
        #     self.radar_widget.set_radar_data(radar_data)
            
        #     self.socket_thread_2.add_data(
        #         {"flag": int(flag), "pan": pan, "tilt": tilt})

        # except:
        #     print("unknown error!")

        self.socket_thread_1.add_data(combined_data_s1)
#####################################################################################

    def update_ui(self, processed_frame):
        if processed_frame[0] is not None:
            frame_rgb = cv.cvtColor(processed_frame[0], cv.COLOR_BGR2RGB)
            frame_rgb = cv.resize(frame_rgb, (1600, 900))
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w

            q_img = QImage(
                frame_rgb.data,
                w, h,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )
            self.DET_L.setPixmap(QPixmap.fromImage(q_img))

            self.counts = processed_frame[1] or {"target": 0}
            self.TARGET_NUM.display(self.counts["target"])

    def start_camera(self, checked):
        if checked:
            self.processing_thread.first_frame = True
            self.socket_thread_1.start()
            self.socket_thread_2.start()
            self.START_DET.setText("(d)")
            self.START_DET.setShortcut("d")
            self.processing_thread.current_classes = self.list_classes()
            self.camera_thread.start()
            self.processing_thread.start()
        else:
            self.processing_thread.first_frame = False
            self.processing_thread.current_classes = []
            self.START_DET.setText("(d)")
            self.START_DET.setShortcut("d")

    def update_classes(self):
        self.processing_thread.current_classes = self.list_classes()
