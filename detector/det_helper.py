import math


def prepare_yolo_for_draw_bboxes(dets):
    predictions = []
    for res in dets:
        boxes = res.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            conf = math.ceil(box.conf[0] * 100) / 100
            cls = int(box.cls[0])
            predictions.append([x1, y1, x2, y2, conf, cls])
    return predictions


def prepare_rfdetr_for_draw_bboxes(dets):
    predictions = []
    for (box, conf, cls) in zip(dets.xyxy, dets.confidence, dets.class_id):
        x1, y1, x2, y2 = box
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        conf = math.ceil(conf * 100) / 100
        cls = int(cls)
        predictions.append([x1, y1, x2, y2, conf, cls])
    return predictions


def prepare_dfine_for_draw_bboxes(dets):
    predictions = []
    boxes = dets.get("boxes", [])
    labels = dets.get("labels", [])
    scores = dets.get("scores", [])
    for box, cls, conf in zip(boxes, labels, scores):
        x1, y1, x2, y2 = box
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        conf = math.ceil(conf * 100) / 100
        cls = int(cls)
        predictions.append([x1, y1, x2, y2, conf, cls])
    return predictions
