from typing import Dict, List, Tuple

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from loguru import logger
from numpy.typing import NDArray
from torch.amp import autocast
from torchvision.ops import nms

from ..d_fine.dfine import build_model


class Torch_model:
    def __init__(
        self,
        model_name: str,
        model_path: str,
        n_outputs: int,
        input_width: int = 640,
        input_height: int = 640,
        conf_thresh: float = 0.5,
        rect: bool = False,  # cuts paddings, inference is faster, accuracy might be lower
        half: bool = False,
        keep_ratio: bool = False,
        use_nms: bool = False,
        device: str = None,
    ):
        self.input_size = (input_width, input_height)
        self.n_outputs = n_outputs
        self.model_name = model_name
        self.model_path = model_path
        self.rect = rect
        self.half = half
        self.keep_ratio = keep_ratio
        self.use_nms = use_nms
        self.channels = 3
        self.debug_mode = False

        if isinstance(conf_thresh, float):
            self.conf_threshs = [conf_thresh] * self.n_outputs
        elif isinstance(conf_thresh, list):
            self.conf_threshs = conf_thresh

        if not device:
            self.device = torch.device("cpu")
            if torch.backends.mps.is_available():
                self.device = torch.device("mps")
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
        else:
            self.device = device

        self.np_dtype = np.float32
        if self.half:
            self.amp_enabled = True
        else:
            self.amp_enabled = False

        self._load_model()
        self._test_pred()

    def _load_model(self):
        self.model = build_model(
            self.model_name, self.n_outputs, self.device, img_size=self.input_size
        )
        self.model.load_state_dict(
            torch.load(self.model_path, weights_only=True, map_location=torch.device("cpu"))
        )
        self.model.eval()
        self.model.to(self.device)

        logger.info(f"Torch model, Device: {self.device}, AMP: {self.amp_enabled}")

    def _test_pred(self) -> None:
        random_image = np.random.randint(
            0, 255, size=(self.input_size[1], self.input_size[0], self.channels), dtype=np.uint8
        )
        processed_inputs, processed_sizes, original_sizes = self._prepare_inputs(random_image)
        preds = self._predict(processed_inputs)
        self._postprocess(preds, processed_sizes, original_sizes)

    @staticmethod
    def process_boxes(boxes, processed_sizes, orig_sizes, keep_ratio, device):
        boxes = boxes.cpu().numpy()
        final_boxes = np.zeros_like(boxes)
        for idx, box in enumerate(boxes):
            final_boxes[idx] = norm_xywh_to_abs_xyxy(
                box, processed_sizes[idx][0], processed_sizes[idx][1]
            )

        for i in range(len(orig_sizes)):
            if keep_ratio:
                final_boxes[i] = scale_boxes_ratio_kept(
                    final_boxes[i],
                    processed_sizes[i],
                    orig_sizes[i],
                )
            else:
                final_boxes[i] = scale_boxes(
                    final_boxes[i],
                    orig_sizes[i],
                    processed_sizes[i],
                )
        return torch.tensor(final_boxes).to(device)

    def _preds_postprocess(
        self,
        outputs,
        processed_sizes,
        original_sizes,
        num_top_queries=300,
        use_focal_loss=True,
    ) -> List[Dict[str, torch.Tensor]]:
        """
        returns List with BS length. Each element is a dict {"labels", "boxes", "scores"}
        """
        logits, boxes = outputs["pred_logits"], outputs["pred_boxes"]
        boxes = self.process_boxes(
            boxes, processed_sizes, original_sizes, self.keep_ratio, self.device
        )  # B x TopQ x 4

        if use_focal_loss:
            scores = F.sigmoid(logits)
            scores, index = torch.topk(scores.flatten(1), num_top_queries, dim=-1)
            labels = index - index // self.n_outputs * self.n_outputs
            index = index // self.n_outputs
            boxes = boxes.gather(dim=1, index=index.unsqueeze(-1).repeat(1, 1, boxes.shape[-1]))
        else:
            scores = F.softmax(logits)[:, :, :-1]
            scores, labels = scores.max(dim=-1)
            if scores.shape[1] > num_top_queries:
                scores, index = torch.topk(scores, num_top_queries, dim=-1)
                labels = torch.gather(labels, dim=1, index=index)
                boxes = torch.gather(
                    boxes, dim=1, index=index.unsqueeze(-1).tile(1, 1, boxes.shape[-1])
                )

        results = []
        for lab, box, sco in zip(labels, boxes, scores):
            result = dict(labels=lab, boxes=box, scores=sco)
            results.append(result)
        return results

    def _compute_nearest_size(self, shape, target_size, stride=32) -> Tuple[int, int]:
        """
        Get nearest size that is divisible by 32
        """
        scale = target_size / max(shape)
        new_shape = [int(round(dim * scale)) for dim in shape]

        # Make sure new dimensions are divisible by the stride
        new_shape = [max(stride, int(np.ceil(dim / stride) * stride)) for dim in new_shape]
        return new_shape

    def _preprocess(self, img: NDArray, stride: int = 32) -> torch.tensor:
        if not self.keep_ratio:  # simple resize
            img = cv2.resize(
                img, (self.input_size[1], self.input_size[0]), interpolation=cv2.INTER_AREA
            )
        elif self.rect:  # keep ratio and cut paddings
            target_height, target_width = self._compute_nearest_size(
                img.shape[:2], max(self.input_size[0], self.input_size[1])
            )
            img = letterbox(img, (target_height, target_width), stride=stride, auto=False)[0]
        else:  # keep ratio adding paddings
            img = letterbox(
                img, (self.input_size[1], self.input_size[0]), stride=stride, auto=False
            )[0]

        img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, then HWC to CHW
        img = np.ascontiguousarray(img, dtype=self.np_dtype)
        img /= 255.0

        # save debug image
        if self.debug_mode:
            debug_img = img.reshape([1, *img.shape])
            debug_img = debug_img[0].transpose(1, 2, 0)  # CHW to HWC
            debug_img = (debug_img * 255.0).astype(np.uint8)  # Convert to uint8
            debug_img = debug_img[:, :, ::-1]  # RGB to BGR for saving
            cv2.imwrite("torch_infer.jpg", debug_img)
        return img

    def _prepare_inputs(self, inputs):
        original_sizes = []
        processed_sizes = []

        if isinstance(inputs, np.ndarray) and inputs.ndim == 3:  # single image
            processed_inputs = self._preprocess(inputs)[None]
            original_sizes.append((inputs.shape[0], inputs.shape[1]))
            processed_sizes.append((processed_inputs[0].shape[1], processed_inputs[0].shape[2]))

        elif isinstance(inputs, np.ndarray) and inputs.ndim == 4:  # batch of images
            processed_inputs = np.zeros(
                (inputs.shape[0], self.channels, self.input_size[0], self.input_size[1]),
                dtype=self.np_dtype,
            )
            for idx, image in enumerate(inputs):
                processed_inputs[idx] = self._preprocess(image)
                original_sizes.append((image.shape[0], image.shape[1]))
                processed_sizes.append(
                    (processed_inputs[idx].shape[1], processed_inputs[idx].shape[2])
                )
        return torch.tensor(processed_inputs).to(self.device), processed_sizes, original_sizes

    @torch.no_grad()
    def _predict(self, inputs) -> Tuple[torch.tensor, torch.tensor, torch.tensor]:
        if self.amp_enabled:
            with autocast("cuda"):
                return self.model(inputs)
        return self.model(inputs)

    def _postprocess(
        self,
        preds: torch.tensor,
        processed_sizes: List[Tuple[int, int]],
        original_sizes: List[Tuple[int, int]],
    ):
        output = self._preds_postprocess(preds, processed_sizes, original_sizes)
        output = filter_preds(output, self.conf_threshs)
        if self.use_nms:
            for idx, res in enumerate(output):
                boxes, scores, classes = non_max_suppression(
                    res["boxes"],
                    res["scores"],
                    res["labels"],
                    iou_threshold=0.5,
                )
                output[idx]["boxes"] = boxes
                output[idx]["scores"] = scores
                output[idx]["labels"] = classes

        for res in output:
            res["labels"] = res["labels"].cpu().numpy()
            res["boxes"] = res["boxes"].cpu().numpy()
            res["scores"] = res["scores"].cpu().numpy()
        return output

    @torch.no_grad()
    def __call__(self, inputs: NDArray[np.uint8]) -> List[Dict[str, np.ndarray]]:
        """
        Input image as ndarray (BGR, HWC) or BHWC
        Output:
            List of batch size length. Each element is a dict {"labels", "boxes", "scores"}
            labels: np.ndarray of shape (N,), dtype np.int64
            boxes: np.ndarray of shape (N, 4), dtype np.float32, abs values
            scores: np.ndarray of shape (N,), dtype np.float32
        """
        processed_inputs, processed_sizes, original_sizes = self._prepare_inputs(inputs)
        preds = self._predict(processed_inputs)
        return self._postprocess(preds, processed_sizes, original_sizes)


def letterbox(
    im,
    new_shape=(640, 640),
    color=(114, 114, 114),
    auto=True,
    scale_fill=False,
    scaleup=True,
    stride=32,
):
    # Resize and pad image while meeting stride-multiple constraints
    shape = im.shape[:2]  # current shape [height, width]
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    # Scale ratio (new / old)
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    if not scaleup:  # only scale down, do not scale up (for better val mAP)
        r = min(r, 1.0)

    # Compute padding
    ratio = r, r  # width, height ratios
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding
    if auto:  # minimum rectangle
        dw, dh = np.mod(dw, stride), np.mod(dh, stride)  # wh padding
    elif scale_fill:  # stretch
        dw, dh = 0.0, 0.0
        new_unpad = (new_shape[1], new_shape[0])
        ratio = new_shape[1] / shape[1], new_shape[0] / shape[0]  # width, height ratios

    dw /= 2  # divide padding into 2 sides
    dh /= 2

    if shape[::-1] != new_unpad:  # resize
        im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_AREA)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    im = cv2.copyMakeBorder(
        im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
    )  # add border
    return im, ratio, (dw, dh)


def clip_boxes(boxes, shape):
    # Clip boxes (xyxy) to image shape (height, width)
    if isinstance(boxes, torch.Tensor):  # faster individually
        boxes[..., 0].clamp_(0, shape[1])  # x1
        boxes[..., 1].clamp_(0, shape[0])  # y1
        boxes[..., 2].clamp_(0, shape[1])  # x2
        boxes[..., 3].clamp_(0, shape[0])  # y2
    else:  # np.array (faster grouped)
        boxes[..., [0, 2]] = boxes[..., [0, 2]].clip(0, shape[1])  # x1, x2
        boxes[..., [1, 3]] = boxes[..., [1, 3]].clip(0, shape[0])  # y1, y2


def scale_boxes_ratio_kept(boxes, img1_shape, img0_shape, ratio_pad=None, padding=True):
    # Rescale boxes (xyxy) from img1_shape to img0_shape
    if ratio_pad is None:  # calculate from img0_shape
        gain = min(
            img1_shape[0] / img0_shape[0], img1_shape[1] / img0_shape[1]
        )  # gain  = old / new
        pad = (
            round((img1_shape[1] - img0_shape[1] * gain) / 2 - 0.1),
            round((img1_shape[0] - img0_shape[0] * gain) / 2 - 0.1),
        )  # wh padding
    else:
        gain = ratio_pad[0][0]
        pad = ratio_pad[1]

    if padding:
        boxes[..., [0, 2]] -= pad[0]  # x padding
        boxes[..., [1, 3]] -= pad[1]  # y padding
    boxes[..., :4] /= gain
    clip_boxes(boxes, img0_shape)
    return boxes


def scale_boxes(boxes, orig_shape, resized_shape):
    scale_x = orig_shape[1] / resized_shape[1]
    scale_y = orig_shape[0] / resized_shape[0]
    boxes[:, 0] *= scale_x
    boxes[:, 2] *= scale_x
    boxes[:, 1] *= scale_y
    boxes[:, 3] *= scale_y
    return boxes


def norm_xywh_to_abs_xyxy(boxes: np.ndarray, h: int, w: int, clip=True):
    """
    Normalised (x_c, y_c, w, h) -> absolute (x1, y1, x2, y2)
    Keeps full floating-point precision; no rounding.
    """
    x_c, y_c, bw, bh = boxes.T
    x_min = x_c * w - bw * w / 2
    y_min = y_c * h - bh * h / 2
    x_max = x_c * w + bw * w / 2
    y_max = y_c * h + bh * h / 2

    if clip:
        x_min = np.clip(x_min, 0, w - 1)
        y_min = np.clip(y_min, 0, h - 1)
        x_max = np.clip(x_max, 0, w - 1)
        y_max = np.clip(y_max, 0, h - 1)

    return np.stack([x_min, y_min, x_max, y_max], axis=1)


def filter_preds(preds, conf_threshs: List[float]):
    conf_threshs = torch.tensor(conf_threshs, device=preds[0]["scores"].device)
    for pred in preds:
        mask = pred["scores"] >= conf_threshs[pred["labels"]]
        pred["scores"] = pred["scores"][mask]
        pred["boxes"] = pred["boxes"][mask]
        pred["labels"] = pred["labels"][mask]
    return preds


def non_max_suppression(boxes, scores, classes, iou_threshold=0.5):
    """
    Applies Non-Maximum Suppression (NMS) to filter bounding boxes.

    Parameters:
    - boxes (torch.Tensor): Tensor of shape (N, 4) containing bounding boxes in [x1, y1, x2, y2] format.
    - scores (torch.Tensor): Tensor of shape (N,) containing confidence scores for each box.
    - classes (torch.Tensor): Tensor of shape (N,) containing class indices for each box.
    - score_threshold (float): Minimum confidence score to consider a box for NMS.
    - iou_threshold (float): Intersection Over Union (IOU) threshold for NMS.

    Returns:
    - filtered_boxes (torch.Tensor): Tensor containing filtered bounding boxes after NMS.
    - filtered_scores (torch.Tensor): Tensor containing confidence scores of the filtered boxes.
    - filtered_classes (torch.Tensor): Tensor containing class indices of the filtered boxes.
    """
    # Prepare lists to collect the filtered boxes, scores, and classes
    filtered_boxes = []
    filtered_scores = []
    filtered_classes = []

    # Get unique classes present in the detections
    unique_classes = classes.unique()

    # Step 2: Perform NMS for each class separately
    for unique_class in unique_classes:
        # Get indices of boxes belonging to the current class
        cls_mask = classes == unique_class
        cls_boxes = boxes[cls_mask]
        cls_scores = scores[cls_mask]

        # Apply NMS for the current class
        nms_indices = nms(cls_boxes, cls_scores, iou_threshold)

        # Collect the filtered boxes, scores, and classes
        filtered_boxes.append(cls_boxes[nms_indices])
        filtered_scores.append(cls_scores[nms_indices])
        filtered_classes.append(classes[cls_mask][nms_indices])

    # Step 3: Concatenate the results
    if filtered_boxes:
        filtered_boxes = torch.cat(filtered_boxes)
        filtered_scores = torch.cat(filtered_scores)
        filtered_classes = torch.cat(filtered_classes)
    else:
        # If no boxes remain after NMS, return empty tensors
        filtered_boxes = torch.empty((0, 4))
        filtered_scores = torch.empty((0,))
        filtered_classes = torch.empty((0,), dtype=classes.dtype)

    return filtered_boxes, filtered_scores, filtered_classes


if __name__ == "__main__":
    from pathlib import Path

    from src.dl.infer import run_videos

    model = Torch_model(
        model_name="m",
        model_path="/Users/argosaakyan/Data/firevision/models/baseline_m_2025-06-23/model.pt",
        n_outputs=2,
        input_width=640,
        input_height=640,
        conf_thresh=0.4,
        device="mps",
    )

    run_videos(
        torch_model=model,
        folder_path=Path("/Users/argosaakyan/Data/firevision/datasets"),
        output_path=Path("/Users/argosaakyan/Data/firevision/ex"),
        label_to_name={0: "fire", 1: "no fire"},
        to_crop=False,
        paddings=0,
    )
