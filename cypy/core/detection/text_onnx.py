import cv2
import numpy as np
import onnxruntime
from dataclasses import dataclass

from cypy.core.models import TextSegmentationMask


@dataclass(frozen=True)
class TextBox:
    x1: int
    y1: int
    x2: int
    y2: int
    score: float = 1.0

    def as_list(self):
        return [self.x1, self.y1, self.x2, self.y2]


class PPOCRTextDetector:
    """Lightweight ONNX adapter for PP-OCR detection score maps."""

    def __init__(
        self,
        model_path,
        min_score=0.30,
        box_threshold=0.50,
        max_side=960,
    ):
        opts = onnxruntime.SessionOptions()
        opts.log_severity_level = 3
        self.session = onnxruntime.InferenceSession(model_path, sess_options=opts)
        self.input_name = self.session.get_inputs()[0].name
        self.min_score = float(min_score)
        self.box_threshold = float(box_threshold)
        self.max_side = int(max_side)

    def detect(self, image):
        if image is None or image.size == 0:
            return ()

        score_map, scale_x, scale_y = self._predict_score_map(image)
        return tuple(self._extract_boxes(score_map, image.shape[1], image.shape[0], scale_x, scale_y))

    def segment(self, image):
        if image is None or image.size == 0:
            return None

        score_map, _, _ = self._predict_score_map(image)
        bitmap = self._score_bitmap(score_map, dilate=False)
        original_height, original_width = image.shape[:2]
        resized = cv2.resize(
            bitmap,
            (original_width, original_height),
            interpolation=cv2.INTER_NEAREST,
        )
        return TextSegmentationMask(
            width=original_width,
            height=original_height,
            mask=resized.copy(),
        )

    def _predict_score_map(self, image):
        prepared, scale_x, scale_y = self._preprocess(image)
        output = self.session.run(None, {self.input_name: prepared})[0]
        score_map = self._score_map(output, prepared.shape[3], prepared.shape[2])
        return score_map, scale_x, scale_y

    def _preprocess(self, image):
        height, width = image.shape[:2]
        scale = min(1.0, self.max_side / float(max(height, width)))
        target_width = max(32, int(width * scale))
        target_height = max(32, int(height * scale))
        target_width = max(32, (target_width // 32) * 32)
        target_height = max(32, (target_height // 32) * 32)

        resized = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (rgb - mean) / std
        chw = np.transpose(normalized, (2, 0, 1))
        return np.expand_dims(chw, axis=0).astype(np.float32), target_width / width, target_height / height

    @staticmethod
    def _score_map(output, target_width, target_height):
        score_map = np.squeeze(output).astype(np.float32)
        if score_map.ndim != 2:
            raise ValueError(f"Unexpected PP-OCR output shape: {output.shape!r}")
        if score_map.shape != (target_height, target_width):
            score_map = cv2.resize(score_map, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
        return score_map

    def _extract_boxes(self, score_map, original_width, original_height, scale_x, scale_y):
        bitmap = self._score_bitmap(score_map, dilate=True)
        contours, _ = cv2.findContours(bitmap, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            if width < 3 or height < 3:
                continue

            region = score_map[y : y + height, x : x + width]
            score = float(np.mean(region)) if region.size else 0.0
            if score < self.box_threshold:
                continue

            x1 = max(0, int(round(x / scale_x)))
            y1 = max(0, int(round(y / scale_y)))
            x2 = min(original_width, int(round((x + width) / scale_x)))
            y2 = min(original_height, int(round((y + height) / scale_y)))
            if x2 <= x1 or y2 <= y1:
                continue
            boxes.append(TextBox(x1, y1, x2, y2, score))

        return sorted(boxes, key=lambda box: (box.y1, box.x1))

    def _score_bitmap(self, score_map, dilate=False):
        bitmap = (score_map >= self.min_score).astype(np.uint8) * 255
        if dilate:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            bitmap = cv2.dilate(bitmap, kernel, iterations=1)
        return bitmap
