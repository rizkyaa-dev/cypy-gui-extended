import threading
from abc import ABC, abstractmethod


class BubbleDetector(ABC):
    @abstractmethod
    def detect(self, image):
        """Return candidate speech bubble boxes as [x1, y1, x2, y2]."""


class PrecomputedBubbleDetector(BubbleDetector):
    """Provides immutable preview detections to the processing pipeline."""

    def __init__(self, boxes):
        self.boxes = tuple(tuple(map(int, box)) for box in boxes)

    def detect(self, image):
        return [list(box) for box in self.boxes]


class YoloBubbleDetector(BubbleDetector):
    DEFAULT_STAGES = (
        {"conf": 0.28, "iou": 0.45},
        {"conf": 0.18, "iou": 0.55},
        {"conf": 0.10, "iou": 0.65},
    )

    def __init__(self, yolo_model, stages=None, lock=None):
        self.yolo_model = yolo_model
        self.stages = tuple(stages or self.DEFAULT_STAGES)
        self.lock = lock or threading.Lock()

    def detect(self, image):
        boxes = []

        for stage in self.stages:
            with self.lock:
                results = self.yolo_model.predict(
                    source=image,
                    conf=stage["conf"],
                    iou=stage["iou"],
                    verbose=False,
                )

            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                boxes.append([x1, y1, x2, y2])

        return boxes
