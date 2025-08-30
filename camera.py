from PyQt6.QtCore import QThread, pyqtSignal
import cv2 as cv


class CameraThread(QThread):
    frame_ready = pyqtSignal(object)

    def __init__(self, video_source=0):
        super().__init__()
        self.video_source = video_source
        self.running = False
        self.cap = None

    def run(self):
        self.running = True
        self.cap = cv.VideoCapture(self.video_source)
        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv.CAP_PROP_BUFFERSIZE, 0)
        if not self.cap.isOpened():
            self.frame_ready.emit(None)
            return

        error_count = 0
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                error_count += 1
                print("Error reading frame. Skipping...")
                if error_count > 10:
                    break
                    # print("Reinitializing video capture...")
                    # self.cap.release()
                    # self.cap = cv.VideoCapture(
                    #     self.video_source, cv.CAP_FFMPEG)
                    # error_count = 0
                continue
            error_count = 0
            # frame = cv2.flip(frame, 0)
            self.frame_ready.emit(frame)
        self.cap.release()

    def stop(self):
        self.running = False
        self.wait()
