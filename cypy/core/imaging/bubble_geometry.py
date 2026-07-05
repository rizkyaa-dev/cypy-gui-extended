from dataclasses import dataclass
from typing import Any, Optional, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class BubbleGeometry:
    roi_box: Tuple[int, int, int, int]
    text_box: Tuple[int, int, int, int]
    interior_mask: Any


def analyze_bubble_geometry(image, box) -> Optional[BubbleGeometry]:
    """Find a safe rectangular text region inside a detected bubble ROI."""
    roi_box = _clamp_box(box, image.width, image.height)
    x1, y1, x2, y2 = roi_box
    if x2 - x1 < 20 or y2 - y1 < 20:
        return None

    gray = np.asarray(image.crop(roi_box).convert("L"))
    _, white = cv2.threshold(gray, 185, 255, cv2.THRESH_BINARY)
    component = _select_interior_component(white)
    if component is None:
        return None

    filled = _fill_component_holes(component)
    height, width = filled.shape
    inset = max(2, int(round(min(width, height) * 0.025)))
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (inset * 2 + 1, inset * 2 + 1),
    )
    safe_mask = cv2.erode(filled, kernel, iterations=1)
    local_text_box = largest_inner_rectangle(safe_mask)
    if local_text_box is None:
        return None

    tx1, ty1, tx2, ty2 = local_text_box
    roi_area = max(1, width * height)
    text_area = max(0, tx2 - tx1) * max(0, ty2 - ty1)
    if text_area < roi_area * 0.10:
        return None

    erase_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    interior_mask = cv2.erode(filled, erase_kernel, iterations=1)
    return BubbleGeometry(
        roi_box=roi_box,
        text_box=(x1 + tx1, y1 + ty1, x1 + tx2, y1 + ty2),
        interior_mask=interior_mask,
    )


def largest_inner_rectangle(mask):
    """Return the largest axis-aligned rectangle fully contained in a mask."""
    binary = np.asarray(mask) > 0
    if binary.ndim != 2 or not np.any(binary):
        return None

    height, width = binary.shape
    heights = np.zeros(width, dtype=np.int32)
    best_area = 0
    best_box = None

    for y in range(height):
        heights = np.where(binary[y], heights + 1, 0)
        stack = []

        for x in range(width + 1):
            current_height = int(heights[x]) if x < width else 0
            while stack and int(heights[stack[-1]]) > current_height:
                column = stack.pop()
                rect_height = int(heights[column])
                left = stack[-1] + 1 if stack else 0
                area = rect_height * (x - left)
                if area > best_area:
                    best_area = area
                    best_box = (left, y - rect_height + 1, x, y + 1)
            stack.append(x)

    return best_box


def _select_interior_component(white_mask):
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        white_mask,
        connectivity=8,
    )
    if count <= 1:
        return None

    height, width = white_mask.shape
    roi_area = max(1, height * width)
    center = np.array([width / 2.0, height / 2.0])
    diagonal = max(1.0, float(np.hypot(width, height)))
    best_label = None
    best_score = 0.0

    border_labels = set(labels[0, :])
    border_labels.update(labels[-1, :])
    border_labels.update(labels[:, 0])
    border_labels.update(labels[:, -1])

    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        area_ratio = area / float(roi_area)
        if area_ratio < 0.08 or area_ratio > 0.92:
            continue

        distance = float(np.linalg.norm(centroids[label] - center)) / diagonal
        center_score = max(0.25, 1.0 - distance)
        border_penalty = 0.18 if label in border_labels else 1.0
        score = area * center_score * border_penalty
        if score > best_score:
            best_score = score
            best_label = label

    if best_label is None:
        return None
    return np.where(labels == best_label, 255, 0).astype(np.uint8)


def _fill_component_holes(component):
    contours, _ = cv2.findContours(
        component,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    filled = np.zeros_like(component)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        cv2.drawContours(filled, [largest], -1, 255, thickness=cv2.FILLED)
    return filled


def _clamp_box(box, image_width, image_height):
    x1, y1, x2, y2 = map(int, box)
    x1 = max(0, min(image_width, x1))
    y1 = max(0, min(image_height, y1))
    x2 = max(x1, min(image_width, x2))
    y2 = max(y1, min(image_height, y2))
    return x1, y1, x2, y2
