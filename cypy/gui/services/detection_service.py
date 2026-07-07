import cv2
import os

from cypy.core.detection.text_onnx import PPOCRTextDetector
from cypy.core.documents.image_pipeline import BubbleExtractionPipeline
from cypy.core.models import Box
from cypy.gui.models.job import DetectionPreview


class BubbleDetectionService:
    """Detects the same filtered bubble boxes used by image processing."""

    def __init__(self, detector, settings, pipeline=None, text_detector=None):
        self.settings = settings
        self.pipeline = pipeline or BubbleExtractionPipeline(detector, settings)
        self._text_detector = text_detector
        self._text_detector_loaded = text_detector is not None

    def detect(self, image_path):
        return self.detect_preview(image_path).boxes

    def detect_preview(self, image_path):
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Unable to read image: {image_path}")

        boxes = self.pipeline.detect_boxes(image, image_path)
        return DetectionPreview(
            boxes=tuple(self._to_box(box) for box in boxes),
            text_mask=self._detect_text_mask(image),
        )

    def _detect_text_mask(self, image):
        detector = self._load_text_detector()
        if detector is None:
            return None

        try:
            return detector.segment(image)
        except Exception:
            return None

    def _load_text_detector(self):
        if self._text_detector_loaded:
            return self._text_detector

        self._text_detector_loaded = True
        model_path = getattr(self.settings, "text_detector_model", "")
        if not model_path or not os.path.exists(model_path):
            return None

        try:
            self._text_detector = PPOCRTextDetector(
                model_path,
                min_score=self.settings.text_assist_min_score,
                box_threshold=self.settings.text_assist_box_threshold,
            )
        except Exception:
            self._text_detector = None
        return self._text_detector

    @staticmethod
    def _to_box(box):
        if len(box) != 4:
            raise ValueError(f"Invalid detection box: {box!r}")
        return Box(*map(int, box))
