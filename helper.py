import math
import numpy as np
import yaml

import cv2
import cvzone


with open('config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.SafeLoader)


TRACK_DET_CONF = config["TRACKER"]["TRACK_DET_CONF"]


def color_from_id(id):
    if id is not None:
        np.random.seed(id)
        return np.random.randint(0, 255, size=3).tolist()
    else:
        return [0, 0, 0]


def plot_detected_bboxes(img, predictions, classes=[0, 1], show_conf=False, draw_region=False):
    if type(img) == str:
        img = cv2.imread(img)

    cls_count = {k: 0 for k in config["CLASSES_DICT"].keys()}

    largest_area = 0
    largest_box = None
    target = None
    for pred in predictions:
        x1, y1, x2, y2, conf, cls = pred
        cls_c = (128, 0, 128) if int(cls) == 0 else (144, 238, 144)
        if cls in classes:
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            w, h = x2 - x1, y2 - y1
            area = w * h
            if area > largest_area and conf >= TRACK_DET_CONF:
                largest_area = area
                largest_box = [x1, y1, w, h]
            cv2.rectangle(img, (x1, y1), (x2, y2), cls_c, 5)
            if show_conf:
                cvzone.putTextRect(img, text=str(
                    np.round(conf, 2)), pos=(x1, y1), scale=2)

            for name, idx in config["CLASSES_DICT"].items():
                if int(cls) == idx:
                    cls_count[name] += 1

    if largest_box:
        [x, y, w, h] = largest_box
        target = img[y:y+h, x:x+w]

    return img, largest_box, target, cls_count
