from helper import plot_detected_bboxes
from detector.detector import Detector

from queue import Queue
import numpy as np
import yaml


from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition


with open('config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.SafeLoader)


class ProcessingThread(QThread):
    processed_frame = pyqtSignal(object)
    detecting_data_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = False
        self.frame_queue = Queue(maxsize=config["PROCESS_MAX_QUEUE_SIZE"])
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.detector = Detector(
            weight_dir=config["DETECTION"]["WEIGHT_PATH"], classes=config["DETECTION"]["CLASSES"])
        self.detector.predict(
            np.zeros((1280, 1280, 3), dtype=np.uint8), classes=[0])
        self.first_frame = True
        self.current_classes = []

    def add_frame(self, frame):
        self.mutex.lock()
        if self.frame_queue.qsize() < config["PROCESS_MAX_QUEUE_SIZE"]:
            self.frame_queue.put(frame.copy())
            self.condition.wakeAll()
        self.mutex.unlock()

    def run(self):
        self.running = True
        while self.running:
            self.mutex.lock()
            if self.frame_queue.empty():
                self.condition.wait(self.mutex)
            if not self.running:
                self.mutex.unlock()
                break
            frame = self.frame_queue.get()
            self.mutex.unlock()
            processed_frame = self.process_frame(frame)
            self.processed_frame.emit(processed_frame)

    def stop(self):
        self.running = False
        self.condition.wakeAll()
        self.wait()

    def process_frame(self, frame):
        detecting_data = {}
        bbox = None
        cls_count = {k: 0 for k in config["CLASSES_DICT"].keys()}

        if self.first_frame and len(self.current_classes) > 0:
            self.predictions = self.detector.predict(
                frame, classes=self.current_classes)
            frame, largest_bbox, target, cls_count = plot_detected_bboxes(frame, self.predictions,
                                                                          classes=self.current_classes,
                                                                          show_conf=False,
                                                                          draw_region=True)
        self.detecting_data_ready.emit(detecting_data)
        return frame, cls_count
