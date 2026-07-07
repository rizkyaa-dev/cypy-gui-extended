import cv2
import numpy as np

from cypy.core.detection.box_filters import (
    _area_box,
    _irisan_box,
    gabung_kotak_tumpang_tindih,
)


def _clamp_box(box, width, height):
    x1, y1, x2, y2 = map(int, box)
    return [
        max(0, min(width, x1)),
        max(0, min(height, y1)),
        max(0, min(width, x2)),
        max(0, min(height, y2)),
    ]


def _expand_box(box, margin, width, height):
    x1, y1, x2, y2 = box
    return _clamp_box([x1 - margin, y1 - margin, x2 + margin, y2 + margin], width, height)


def _box_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _center_inside(center, box):
    x, y = center
    x1, y1, x2, y2 = box
    return x1 <= x <= x2 and y1 <= y <= y2


class TextAssistedBoxRefiner:
    """Uses text detections as evidence to refine YOLO speech-bubble boxes."""

    def __init__(
        self,
        text_detector,
        settings,
        min_text_overlap=0.12,
        false_positive_area_ratio=0.025,
    ):
        self.text_detector = text_detector
        self.settings = settings
        self.min_text_overlap = float(min_text_overlap)
        self.false_positive_area_ratio = float(false_positive_area_ratio)

    def refine(self, image, bubble_boxes):
        if self.text_detector is None:
            return bubble_boxes

        try:
            text_boxes = [box.as_list() for box in self.text_detector.detect(image)]
        except Exception:
            return bubble_boxes

        if not text_boxes:
            return bubble_boxes

        height, width = image.shape[:2]
        refined = self._expand_bubbles_around_text(
            bubble_boxes,
            text_boxes,
            width,
            height,
        )
        refined = self._drop_small_textless_false_positives(
            refined,
            text_boxes,
            width,
            height,
        )

        if self.settings.text_assist_orphan_recovery:
            refined.extend(self._recover_orphan_text_bubbles(image, refined, text_boxes))

        return gabung_kotak_tumpang_tindih(refined, settings=self.settings)

    def _expand_bubbles_around_text(self, bubble_boxes, text_boxes, width, height):
        margin = max(0, int(self.settings.text_assist_expand_margin))
        refined = []

        for bubble in bubble_boxes:
            expanded_probe = _expand_box(bubble, margin, width, height)
            linked_texts = [
                text
                for text in text_boxes
                if self._text_belongs_to_bubble(text, bubble, expanded_probe)
            ]

            if not linked_texts:
                refined.append(bubble)
                continue

            x1, y1, x2, y2 = bubble
            for text in linked_texts:
                tx1, ty1, tx2, ty2 = text
                x1 = min(x1, tx1 - margin)
                y1 = min(y1, ty1 - margin)
                x2 = max(x2, tx2 + margin)
                y2 = max(y2, ty2 + margin)
            refined.append(_clamp_box([x1, y1, x2, y2], width, height))

        return refined

    def _text_belongs_to_bubble(self, text, bubble, expanded_probe):
        text_area = max(1, _area_box(text))
        overlap_ratio = _irisan_box(text, bubble) / float(text_area)
        if overlap_ratio >= self.min_text_overlap:
            return True
        return _center_inside(_box_center(text), expanded_probe)

    def _drop_small_textless_false_positives(self, bubble_boxes, text_boxes, width, height):
        image_area = max(1, width * height)
        kept = []

        for bubble in bubble_boxes:
            bubble_area_ratio = _area_box(bubble) / float(image_area)
            has_text = any(_irisan_box(bubble, text) > 0 for text in text_boxes)
            if not has_text and bubble_area_ratio <= self.false_positive_area_ratio:
                continue
            kept.append(bubble)

        return kept

    def _recover_orphan_text_bubbles(self, image, bubble_boxes, text_boxes):
        height, width = image.shape[:2]
        recovered = []

        for text in text_boxes:
            if any(_irisan_box(text, bubble) > 0 for bubble in bubble_boxes):
                continue

            candidate = self._candidate_from_text_region(image, text)
            if candidate is not None:
                recovered.append(_clamp_box(candidate, width, height))

        return recovered

    def _candidate_from_text_region(self, image, text_box):
        height, width = image.shape[:2]
        margin = max(18, int(self.settings.text_assist_expand_margin) * 2)
        probe = _expand_box(text_box, margin, width, height)
        px1, py1, px2, py2 = probe
        crop = image[py1:py2, px1:px2]
        if crop.size == 0:
            return None

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        white_mask = (gray >= 210).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
        contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        local_center = (
            int((_box_center(text_box)[0] - px1)),
            int((_box_center(text_box)[1] - py1)),
        )
        best = None
        best_area = 0

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < 8 or h < 8:
                continue
            if not (x <= local_center[0] <= x + w and y <= local_center[1] <= y + h):
                continue

            area = w * h
            if area > best_area:
                best = [px1 + x, py1 + y, px1 + x + w, py1 + y + h]
                best_area = area

        if best is None:
            best = _expand_box(text_box, margin // 2, width, height)

        if not self._candidate_is_reasonable(best, width, height):
            return None
        return best

    @staticmethod
    def _candidate_is_reasonable(box, width, height):
        box_width = max(1, box[2] - box[0])
        box_height = max(1, box[3] - box[1])
        area_ratio = (box_width * box_height) / float(max(1, width * height))
        ratio = box_width / float(box_height)
        return area_ratio <= 0.16 and 0.18 <= ratio <= 5.5
