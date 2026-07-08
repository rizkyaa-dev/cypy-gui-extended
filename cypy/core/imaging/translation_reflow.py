from dataclasses import dataclass
import math
import re

import numpy as np
from PIL import ImageDraw

from cypy.core.imaging.bubble_geometry import analyze_bubble_geometry
from cypy.core.imaging.text_layout import cari_layout_teks_optimal, pilih_setting_teks
from cypy.core.settings import ProcessingSettings


@dataclass(frozen=True)
class RegionLayout:
    bubble_id: str
    box: tuple
    fit_box: tuple
    area: int
    is_accessory: bool


def reflow_translations_for_layout(
    image,
    translations,
    coordinates,
    target_language,
    settings=None,
):
    """Keep translated text inside visually suitable regions before rendering."""
    if not translations or not coordinates:
        return translations

    if (target_language or "").lower() in ("jepang", "japanese"):
        return translations

    cfg = settings or ProcessingSettings.from_config()
    draw = ImageDraw.Draw(image)
    layouts = _build_region_layouts(image, coordinates)
    adjusted = {str(key): str(value).strip() for key, value in translations.items()}

    for bubble_id, layout in _accessory_regions_by_size(layouts):
        text = adjusted.get(bubble_id, "").strip()
        if _is_skip_text(text) or _fits_readably(draw, text, layout.fit_box, target_language, cfg):
            continue

        prefix, overflow = _split_for_accessory_region(
            draw,
            text,
            layout.fit_box,
            target_language,
            cfg,
        )
        if not overflow:
            continue

        parent_id = _find_parent_region(bubble_id, layouts)
        if parent_id is None:
            continue

        adjusted[bubble_id] = prefix or _first_token(text)
        adjusted[parent_id] = _merge_without_duplicate(
            adjusted.get(parent_id, ""),
            overflow,
        )

    return adjusted


def _build_region_layouts(image, coordinates):
    layouts = {}
    image_area = max(1, image.width * image.height)

    for bubble_id, box in coordinates.items():
        clean_box = tuple(map(int, box))
        x1, y1, x2, y2 = clean_box
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        geometry = analyze_bubble_geometry(image, clean_box)
        fit_box = _default_fit_box(clean_box, geometry)
        area_ratio = (width * height) / float(image_area)
        layouts[str(bubble_id)] = RegionLayout(
            bubble_id=str(bubble_id),
            box=clean_box,
            fit_box=fit_box,
            area=width * height,
            is_accessory=_is_accessory_region(
                image,
                clean_box,
                geometry,
                area_ratio,
            ),
        )

    return layouts


def _default_fit_box(box, geometry):
    if geometry is None:
        return box

    if geometry.text_erase_mask is not None:
        label_box = _fit_box_from_existing_text(box, geometry)
        if label_box is not None:
            return label_box

    if geometry.layout_box is not None:
        return tuple(map(int, geometry.layout_box))
    if geometry.text_box is not None:
        return tuple(map(int, geometry.text_box))
    return box


def _is_accessory_region(image, box, geometry, area_ratio):
    if geometry is None or geometry.safe_mask is None:
        return False

    x1, y1, x2, y2 = box
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    if area_ratio > 0.012 or width > image.width * 0.14 or height > image.height * 0.13:
        return False

    safe_mask = np.asarray(geometry.safe_mask) > 0
    if safe_mask.ndim != 2 or not np.any(safe_mask):
        return False

    _, xs = np.where(safe_mask)
    safe_width = int(xs.max() - xs.min() + 1)
    return safe_width <= width * 0.72


def _fit_box_from_existing_text(box, geometry):
    mask = np.asarray(geometry.text_erase_mask) > 0
    if mask.ndim != 2 or not np.any(mask):
        return None

    x1, y1, x2, y2 = map(int, box)
    roi_x1, roi_y1, _, _ = geometry.roi_box
    ys, xs = np.where(mask)
    ink_x1 = roi_x1 + int(xs.min())
    ink_y1 = roi_y1 + int(ys.min())
    ink_x2 = roi_x1 + int(xs.max()) + 1
    ink_y2 = roi_y1 + int(ys.max()) + 1
    ink_width = max(1, ink_x2 - ink_x1)
    ink_height = max(1, ink_y2 - ink_y1)

    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)
    target_width = min(box_width, max(42, int(round(ink_width * 1.75))))
    target_height = min(box_height, max(28, int(round(ink_height * 1.65))))
    center_x = (ink_x1 + ink_x2) / 2.0
    center_y = (ink_y1 + ink_y2) / 2.0
    left = int(round(center_x - (target_width / 2.0)))
    top = int(round(center_y - (target_height / 2.0)))

    left = max(x1, min(left, x2 - target_width))
    top = max(y1, min(top, y2 - target_height))
    return (
        max(0, left),
        max(0, top),
        left + target_width,
        top + target_height,
    )


def _accessory_regions_by_size(layouts):
    return sorted(
        ((bubble_id, layout) for bubble_id, layout in layouts.items() if layout.is_accessory),
        key=lambda item: item[1].area,
    )


def _fits_readably(draw, text, box, target_language, settings):
    fitted = _measure_fit(draw, text, box, target_language, settings)
    return fitted is not None and fitted.font_size >= _readable_font_floor(box)


def _measure_fit(draw, text, box, target_language, settings):
    text = str(text).strip()
    if not text:
        return None

    x1, y1, x2, y2 = map(int, box)
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    layout_settings = pilih_setting_teks(width, height, text)
    layout_settings = {
        **layout_settings,
        "skala_w": 0.96,
        "skala_h": 0.92,
        "font_scale": 0.98,
    }
    return cari_layout_teks_optimal(
        draw,
        text,
        target_language,
        settings,
        layout_settings,
        width * layout_settings["skala_w"],
        height * layout_settings["skala_h"],
    )


def _readable_font_floor(box):
    x1, y1, x2, y2 = map(int, box)
    short_side = min(max(1, x2 - x1), max(1, y2 - y1))
    return max(8, min(13, int(round(short_side * 0.23))))


def _split_for_accessory_region(draw, text, box, target_language, settings):
    words = str(text).strip().split()
    if len(words) <= 1:
        return text, ""

    best_prefix = ""
    best_index = 0
    word_limit = _accessory_prefix_word_limit(box)
    for index in range(1, min(len(words), word_limit) + 1):
        prefix = " ".join(words[:index])
        if _fits_readably(draw, prefix, box, target_language, settings):
            best_prefix = prefix
            best_index = index
        else:
            break

    if not best_prefix:
        return words[0], " ".join(words[1:])

    return best_prefix, " ".join(words[best_index:])


def _accessory_prefix_word_limit(box):
    x1, y1, x2, y2 = map(int, box)
    area = max(1, x2 - x1) * max(1, y2 - y1)
    if area < 4500:
        return 1
    if area < 9000:
        return 2
    return 3


def _find_parent_region(bubble_id, layouts):
    source = layouts.get(bubble_id)
    if source is None:
        return None

    source_diag = _box_diagonal(source.box)
    candidates = []
    for candidate_id, candidate in layouts.items():
        if candidate_id == bubble_id or candidate.is_accessory:
            continue
        if candidate.area <= source.area * 1.25:
            continue

        gap = _box_gap(source.box, candidate.box)
        center_distance = _center_distance(source.box, candidate.box)
        if gap > max(18.0, source_diag * 0.85) and center_distance > source_diag * 2.3:
            continue

        score = (
            (gap * 2.0)
            + (center_distance * 0.20)
            - min(12.0, candidate.area / max(1, source.area))
        )
        candidates.append((score, candidate_id))

    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def _merge_without_duplicate(existing, addition):
    existing = str(existing).strip()
    addition = str(addition).strip()
    if not addition:
        return existing
    if not existing or _is_skip_text(existing):
        return addition

    existing_tokens = _normalized_tokens(existing)
    addition_tokens = _normalized_tokens(addition)
    if not addition_tokens:
        return existing
    if _contains_token_sequence(existing_tokens, addition_tokens):
        return existing

    overlap = _suffix_prefix_overlap(existing_tokens, addition_tokens)
    remaining = addition.split()[overlap:]
    if not remaining:
        return existing
    return f"{existing} {' '.join(remaining)}".strip()


def _contains_token_sequence(tokens, needle):
    if len(needle) > len(tokens):
        return False

    for index in range(0, len(tokens) - len(needle) + 1):
        if tokens[index:index + len(needle)] == needle:
            return True
    return False


def _suffix_prefix_overlap(left, right):
    limit = min(len(left), len(right))
    for size in range(limit, 0, -1):
        if left[-size:] == right[:size]:
            return size
    return 0


def _normalized_tokens(text):
    return re.findall(r"[\w']+", str(text).lower())


def _is_skip_text(text):
    return str(text).strip().upper() == "SKIP"


def _first_token(text):
    tokens = str(text).strip().split()
    return tokens[0] if tokens else ""


def _box_gap(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    dx = max(bx1 - ax2, ax1 - bx2, 0)
    dy = max(by1 - ay2, ay1 - by2, 0)
    return math.hypot(dx, dy)


def _center_distance(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return math.hypot(
        ((ax1 + ax2) / 2.0) - ((bx1 + bx2) / 2.0),
        ((ay1 + ay2) / 2.0) - ((by1 + by2) / 2.0),
    )


def _box_diagonal(box):
    x1, y1, x2, y2 = box
    return math.hypot(max(1, x2 - x1), max(1, y2 - y1))
