from dataclasses import dataclass
from typing import Any, Optional, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class BubbleGeometry:
    roi_box: Tuple[int, int, int, int]
    text_box: Tuple[int, int, int, int]
    interior_mask: Any
    safe_mask: Any = None
    layout_mask: Any = None
    layout_box: Optional[Tuple[int, int, int, int]] = None
    text_erase_mask: Any = None


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
    text_erase_mask = _detect_existing_text_mask(gray, safe_mask)
    text_anchor_box = _detect_vertical_text_anchor_box(gray, safe_mask, local_text_box)
    layout_mask = _build_layout_mask(safe_mask, local_text_box, text_anchor_box)
    lx1, ly1, lx2, ly2 = _mask_bounds(layout_mask) or local_text_box
    return BubbleGeometry(
        roi_box=roi_box,
        text_box=(x1 + tx1, y1 + ty1, x1 + tx2, y1 + ty2),
        interior_mask=interior_mask,
        safe_mask=safe_mask,
        layout_mask=layout_mask,
        layout_box=(x1 + lx1, y1 + ly1, x1 + lx2, y1 + ly2),
        text_erase_mask=text_erase_mask,
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


def _detect_existing_text_mask(gray, safe_mask):
    """Return a conservative mask for dark existing text inside the bubble."""
    safe = np.asarray(safe_mask) > 0
    if not np.any(safe):
        return None

    ink = (gray < 230) & safe
    dark = (gray < 145) & safe
    ink = ink.astype(np.uint8) * 255
    dark = dark.astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 5))
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel, iterations=1)
    dark = cv2.dilate(dark, kernel, iterations=1)

    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cleaned = np.zeros_like(ink)
    height, width = dark.shape
    roi_area = max(1, height * width)

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area_ratio = (w * h) / float(roi_area)
        if area_ratio < 0.0004 or area_ratio > 0.35:
            continue
        if w > width * 0.92 and h > height * 0.20:
            continue
        local = np.zeros_like(ink)
        cv2.drawContours(local, [contour], -1, 255, thickness=cv2.FILLED)
        if np.any(cv2.bitwise_and(local, dark)):
            cleaned = cv2.bitwise_or(cleaned, local)

    if not np.any(cleaned):
        return None
    return cv2.dilate(cleaned, kernel, iterations=1)


def _detect_vertical_text_anchor_box(gray, safe_mask, inner_box):
    safe = np.asarray(safe_mask) > 0
    if not np.any(safe) or inner_box is None:
        return None

    ix1, iy1, ix2, iy2 = map(int, inner_box)
    inner_height = max(1, iy2 - iy1)
    dark = ((np.asarray(gray) < 130) & safe).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 15))
    grouped = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, kernel, iterations=1)
    grouped = cv2.dilate(grouped, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 5)), iterations=1)
    contours, _ = cv2.findContours(grouped, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < 4 or h < max(60, int(inner_height * 0.32)):
            continue

        aspect = h / float(max(1, w))
        if aspect < 3.0:
            continue

        component = (x, y, x + w, y + h)
        center_x = x + (w / 2.0)
        if not (ix1 <= center_x <= ix2):
            continue

        overlap = _box_intersection_area(component, inner_box)
        if overlap / float(max(1, w * h)) < 0.14:
            continue

        candidates.append(component)

    if not candidates:
        return None

    x1 = min(box[0] for box in candidates)
    y1 = min(box[1] for box in candidates)
    x2 = max(box[2] for box in candidates)
    y2 = max(box[3] for box in candidates)
    center_x = (x1 + x2) / 2.0
    if not (ix1 <= center_x <= ix2):
        return None
    return x1, y1, x2, y2


def _box_intersection_area(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return max(0, min(ax2, bx2) - max(ax1, bx1)) * max(0, min(ay2, by2) - max(ay1, by1))


def _build_layout_mask(safe_mask, inner_box, anchor_box=None):
    """Constrain text layout to the strongest rectangle inside the bubble mask."""
    binary = (np.asarray(safe_mask) > 0).astype(np.uint8) * 255
    if binary.ndim != 2 or inner_box is None:
        return safe_mask

    height, width = binary.shape
    x1, y1, x2, y2 = map(int, inner_box)
    if x2 <= x1 or y2 <= y1:
        return safe_mask

    box_width = x2 - x1
    box_height = y2 - y1
    pad_x = max(3, int(round(box_width * 0.10)))
    pad_y = max(3, int(round(box_height * 0.08)))
    gx1 = max(0, x1 - pad_x)
    gy1 = max(0, y1 - pad_y)
    gx2 = min(width, x2 + pad_x)
    gy2 = min(height, y2 + pad_y)

    gate = np.zeros_like(binary)
    gate[gy1:gy2, gx1:gx2] = 255
    layout_mask = _maybe_shift_layout_gate(binary, gate, (gx1, gy1, gx2, gy2), anchor_box)
    if not np.any(layout_mask):
        layout_mask = np.zeros_like(binary)
        layout_mask[y1:y2, x1:x2] = 255
    return layout_mask


def _maybe_shift_layout_gate(binary, gate, gate_box, anchor_box):
    layout_mask = cv2.bitwise_and(binary, gate)
    if anchor_box is None or not np.any(layout_mask):
        return layout_mask

    gx1, gy1, gx2, gy2 = gate_box
    gate_width = gx2 - gx1
    if gate_width <= 0:
        return layout_mask

    ax1, _, ax2, _ = map(int, anchor_box)
    anchor_center_x = (ax1 + ax2) / 2.0
    gate_center_x = (gx1 + gx2) / 2.0
    delta_x = int(round(anchor_center_x - gate_center_x))
    if abs(delta_x) < max(8, int(round(gate_width * 0.15))):
        return layout_mask

    max_shift = max(1, int(round(gate_width * 0.42)))
    delta_x = max(-max_shift, min(max_shift, delta_x))
    shifted_x1 = max(0, min(binary.shape[1] - gate_width, gx1 + delta_x))
    shifted_x2 = shifted_x1 + gate_width

    shifted_gate = np.zeros_like(binary)
    shifted_gate[gy1:gy2, shifted_x1:shifted_x2] = 255
    shifted_mask = cv2.bitwise_and(binary, shifted_gate)
    if not np.any(shifted_mask):
        return layout_mask

    original_area = float(np.sum(layout_mask > 0))
    shifted_area = float(np.sum(shifted_mask > 0))
    if shifted_area < original_area * 0.55:
        return layout_mask
    if _max_row_width(shifted_mask) < _max_row_width(layout_mask) * 0.65:
        return layout_mask
    return shifted_mask


def _max_row_width(mask):
    binary = np.asarray(mask) > 0
    if binary.ndim != 2:
        return 0
    return max((_longest_true_run(row) for row in binary), default=0)


def _longest_true_run(row):
    best = count = 0
    for value in row:
        if value:
            count += 1
            best = max(best, count)
        else:
            count = 0
    return best


def _mask_bounds(mask):
    binary = np.asarray(mask) > 0
    if binary.ndim != 2 or not np.any(binary):
        return None
    ys, xs = np.where(binary)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _clamp_box(box, image_width, image_height):
    x1, y1, x2, y2 = map(int, box)
    x1 = max(0, min(image_width, x1))
    y1 = max(0, min(image_height, y1))
    x2 = max(x1, min(image_width, x2))
    y2 = max(y1, min(image_height, y2))
    return x1, y1, x2, y2
