import cv2

from cypy.core.documents.image_pipeline import BubbleExtractionPipeline
from cypy.core.models import Box


class BubbleDetectionService:
    """Detects the same filtered bubble boxes used by image processing."""

    def __init__(self, detector, settings, pipeline=None):
        self.pipeline = pipeline or BubbleExtractionPipeline(detector, settings)

    def detect(self, image_path):
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Unable to read image: {image_path}")

        boxes = self.pipeline.detect_boxes(image, image_path)
        return tuple(self._to_box(box) for box in boxes)

    @staticmethod
    def _to_box(box):
        if len(box) != 4:
            raise ValueError(f"Invalid detection box: {box!r}")
        return Box(*map(int, box))
