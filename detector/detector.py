"""
Define Detector class
"""
import det_helper
import torch
from rfdetr import RFDETRMedium
from ultralytics import YOLO
from custom_d_fine.src.infer.torch_model import Torch_model
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


class Detector:
    def __init__(self, classes=[0, 1], model_name="yolo", weight_dir="detector/weights/yolo11n.pt", img_size=(640, 640), conf=0.3):
        self.model_name = model_name.lower()
        self.weight_dir = weight_dir
        self.img_size = img_size
        self.classes = classes
        self.conf = conf
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = self.load()
        self.dets = None
        self.final_dets = None

    def load(self):
        if self.model_name.startswith("y"):
            model = YOLO(self.weight_dir, task="detect")
            if self.weight_dir.split(".")[1] == "pt":
                model.fuse()
        elif self.model_name.startswith("r"):
            model = RFDETRMedium(pretrain_weights=self.weight_dir,
                                 resolution=self.img_size[0],
                                 device=self.device,
                                 )
            model.optimize_for_inference()
        elif self.model_name.startswith("d"):
            model = Torch_model(
                model_name="s",
                model_path=self.weight_dir,
                n_outputs=len(self.classes),
                input_width=self.img_size[1],
                input_height=self.img_size[0],
                conf_thresh=self.conf,
                rect=False,
                half=True,
            )
        else:
            raise ValueError(f"Unsupported model_name: {self.model_name}")
        return model

    def predict(self, img):
        if self.model_name.startswith("y"):
            self.dets = self.model(
                img, stream=True, classes=self.classes, imgsz=self.img_size, verbose=False, device=self.device, conf=self.conf)
            self.final_dets = det_helper.prepare_yolo_for_draw_bboxes(self.dets)
        elif self.model_name.startswith("r"):
            self.dets = self.model.predict(img, threshold=self.conf)
            self.final_dets = det_helper.prepare_rfdetr_for_draw_bboxes(self.dets)
        elif self.model_name.startswith("d"):
            self.dets = self.model(img)
            self.final_dets = det_helper.prepare_dfine_for_draw_bboxes(self.dets[0]) if isinstance(
                self.dets, list) else det_helper.prepare_dfine_for_draw_bboxes(self.dets)
        else:
            raise ValueError(f"Unsupported model_name: {self.model_name}")
        return self.final_dets


if __name__ == "__main__":
    import cv2
    detector = Detector(classes=[0, 1], model_name="d",
                        weight_dir="detector/weights/model.pt", conf=0.5)
    img = cv2.imread("detector/1.jpg")
    results = detector.predict(img)
    print("Detections:", results)
