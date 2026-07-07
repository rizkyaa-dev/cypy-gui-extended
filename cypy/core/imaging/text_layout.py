from dataclasses import dataclass

from cypy.core.imaging.fonts import _get_font_for_text, _has_non_latin
from cypy.core.imaging.line_breaker import balanced_wrap_candidates
from cypy.core.settings import ProcessingSettings


def _settings(settings=None):
    return settings or ProcessingSettings.from_config()


@dataclass(frozen=True)
class TextFitResult:
    font_size: int
    wrapped_text: str
    spacing: int
    bbox: tuple
    hyphenated: bool = False


def pecah_kata_hyphen_jika_panjang(draw, word, font, max_w):
    word = str(word)
    bbox = draw.textbbox((0, 0), word, font=font)
    word_w = bbox[2] - bbox[0]

    if word_w <= max_w or "-" not in word:
        return [word]

    tokens = []
    parts = word.split("-")
    for index, part in enumerate(parts):
        if not part:
            continue
        token = part + "-" if index < len(parts) - 1 else part
        tokens.extend(_split_token_to_width(draw, token, font, max_w))

    return tokens if tokens else [word]


def _split_token_to_width(draw, token, font, max_w):
    chunks = []
    current = ""

    for char in str(token):
        candidate = current + char
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if current and bbox[2] - bbox[0] > max_w:
            chunks.append(current)
            current = char
        else:
            current = candidate

    if current:
        chunks.append(current)
    return chunks


def bungkus_teks_per_kata(draw, text, font, max_w):
    text = str(text)
    char_wrap = " " not in text and _has_non_latin(text)
    raw_words = list(text) if char_wrap else text.split()

    if not raw_words:
        return ""

    words = []
    for word in raw_words:
        words.extend(pecah_kata_hyphen_jika_panjang(draw, word, font, max_w))

    lines = []
    current = ""

    for word in words:
        candidate = word if current == "" else (current + word if char_wrap else current + " " + word)
        bbox = draw.textbbox((0, 0), candidate, font=font)
        candidate_w = bbox[2] - bbox[0]

        if candidate_w <= max_w:
            current = candidate
        else:
            if current:
                lines.append(current)
                current = word
            else:
                lines.append(word)
                current = ""

    if current:
        lines.append(current)

    return "\n".join(lines)


def hitung_bbox_multiline(draw, text, font, spacing, stroke_width=0):
    return draw.multiline_textbbox(
        (0, 0),
        text,
        font=font,
        align="center",
        spacing=spacing,
        stroke_width=stroke_width,
    )


def hitung_posisi_teks_terpusat(x1, y1, x2, y2, text_bbox):
    """Return a draw origin corrected for font bearings and stroke bounds."""
    bbox_x1, bbox_y1, bbox_x2, bbox_y2 = text_bbox
    text_width = bbox_x2 - bbox_x1
    text_height = bbox_y2 - bbox_y1
    origin_x = x1 + ((x2 - x1) - text_width) / 2 - bbox_x1
    origin_y = y1 + ((y2 - y1) - text_height) / 2 - bbox_y1
    return origin_x, origin_y


def tulis_teks_di_mask(
    draw,
    text,
    roi_box,
    safe_mask,
    target_language=None,
    settings=None,
):
    """Draw text using per-line widths derived from an interior bubble mask."""
    cfg = _settings(settings)
    text = str(text).strip()
    if not text:
        return False

    lang_key = (target_language or "").lower()
    if lang_key in ("jepang", "japanese"):
        return False
    if not _has_non_latin(text):
        text = text.upper()

    mask_box = _mask_bounds(safe_mask)
    if mask_box is None:
        return False

    roi_x1, roi_y1, _, _ = roi_box
    mx1, my1, mx2, my2 = mask_box
    mask_width = max(1, mx2 - mx1)
    mask_height = max(1, my2 - my1)
    setting = pilih_setting_teks(mask_width, mask_height, text)
    min_font = setting["min_font"]
    max_font = min(setting["max_font"], max(8, int(mask_height * 0.42)))

    for font_size in range(max_font, min_font - 1, -1):
        font = _get_font_for_text(
            text,
            font_size,
            target_language,
            settings=cfg,
        )
        stroke_width = _adaptive_stroke_width(font_size, safe_region=True)
        spacing = max(1, int(font_size * setting["spacing_ratio"]))
        line_height = _line_height(draw, font, stroke_width) + spacing
        if line_height <= 0:
            continue

        max_line_width = _max_mask_line_width(safe_mask) * 0.92
        if max_line_width <= 4:
            continue
        candidates = balanced_wrap_candidates(
            draw,
            text,
            font,
            max_line_width,
            stroke_width=stroke_width,
            allow_hyphenation=False,
        )
        candidates += balanced_wrap_candidates(
            draw,
            text,
            font,
            max_line_width,
            stroke_width=stroke_width,
            allow_hyphenation=True,
        )

        for candidate in sorted(candidates, key=lambda item: (item.penalty, len(item.lines))):
            placements = _fit_lines_to_mask(
                draw,
                candidate.lines,
                font,
                stroke_width,
                line_height,
                safe_mask,
                mask_box,
            )
            if placements is None:
                continue

            _draw_line_underlays(draw, placements, font_size, roi_x1, roi_y1)
            for line, origin_x, origin_y, _ in placements:
                draw.text(
                    (roi_x1 + origin_x, roi_y1 + origin_y),
                    line,
                    fill=(0, 0, 0),
                    font=font,
                    stroke_width=stroke_width,
                    stroke_fill=(255, 255, 255),
                )
            return True

    return False


def _mask_bounds(mask):
    import numpy as np

    binary = np.asarray(mask) > 0
    if binary.ndim != 2 or not np.any(binary):
        return None
    ys, xs = np.where(binary)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _max_mask_line_width(mask):
    import numpy as np

    binary = np.asarray(mask) > 0
    if binary.ndim != 2:
        return 0
    return max((_row_segment(row)[2] for row in binary), default=0)


def _fit_lines_to_mask(draw, lines, font, stroke_width, line_height, mask, mask_box):
    import numpy as np

    if not lines:
        return None

    binary = np.asarray(mask) > 0
    mx1, my1, mx2, my2 = mask_box
    total_height = int(line_height * len(lines) - max(0, line_height * 0.12))
    available_height = my2 - my1
    if total_height > available_height:
        return None

    start_y = my1 + (available_height - total_height) / 2.0
    mask_width = max(1, mx2 - mx1)
    compact_text_in_tall_bubble = (
        available_height / float(mask_width) >= 2.0
        and total_height <= available_height * 0.34
    )
    if compact_text_in_tall_bubble:
        start_y -= min(available_height * 0.08, (available_height - total_height) * 0.28)
    placements = []

    for index, line in enumerate(lines):
        line_bbox = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_width)
        line_width = line_bbox[2] - line_bbox[0]
        line_height_px = line_bbox[3] - line_bbox[1]
        center_y = int(round(start_y + (index * line_height) + (line_height_px / 2)))
        left, right, width = _best_segment_near_y(binary, center_y, search_radius=max(2, int(line_height // 2)))
        if width <= 0 or line_width > width * 0.92:
            return None

        origin_x = left + ((width - line_width) / 2.0) - line_bbox[0]
        origin_y = start_y + (index * line_height) - line_bbox[1]
        ink_left = origin_x + line_bbox[0]
        ink_top = origin_y + line_bbox[1]
        ink_right = origin_x + line_bbox[2]
        ink_bottom = origin_y + line_bbox[3]
        if ink_left < left or ink_right > right or ink_top < my1 or ink_bottom > my2:
            return None
        placements.append((line, origin_x, origin_y, line_bbox))

    return placements


def _draw_line_underlays(draw, placements, font_size, offset_x=0, offset_y=0):
    pad_x = max(4, int(font_size * 0.22))
    pad_y = max(3, int(font_size * 0.14))
    radius = max(3, int(font_size * 0.20))

    for _, origin_x, origin_y, bbox in placements:
        left = offset_x + origin_x + bbox[0] - pad_x
        top = offset_y + origin_y + bbox[1] - pad_y
        right = offset_x + origin_x + bbox[2] + pad_x
        bottom = offset_y + origin_y + bbox[3] + pad_y
        try:
            draw.rounded_rectangle(
                [left, top, right, bottom],
                radius=radius,
                fill=(255, 255, 255),
            )
        except Exception:
            draw.rectangle([left, top, right, bottom], fill=(255, 255, 255))


def _best_segment_near_y(binary, center_y, search_radius):
    height = binary.shape[0]
    best = (0, 0, 0)

    for offset in range(search_radius + 1):
        for y in {center_y - offset, center_y + offset}:
            if y < 0 or y >= height:
                continue
            left, right, width = _row_segment(binary[y])
            if width > best[2]:
                best = (left, right, width)
        if best[2] > 0:
            return best

    return best


def _row_segment(row):
    best_left = best_right = best_width = 0
    start = None

    for index, value in enumerate(row):
        if value and start is None:
            start = index
        elif not value and start is not None:
            width = index - start
            if width > best_width:
                best_left, best_right, best_width = start, index, width
            start = None

    if start is not None:
        width = len(row) - start
        if width > best_width:
            best_left, best_right, best_width = start, len(row), width

    return best_left, best_right, best_width


def _line_height(draw, font, stroke_width):
    bbox = draw.textbbox((0, 0), "Ag", font=font, stroke_width=stroke_width)
    return max(1, bbox[3] - bbox[1])


def _adaptive_stroke_width(font_size, safe_region=False):
    base = max(0, font_size // (16 if safe_region else 11))
    return min(base, 2 if safe_region else 4)


def cari_layout_teks_optimal(
    draw,
    text,
    target_language,
    settings,
    layout_settings,
    max_w,
    max_h,
):
    """Find the most readable balanced wrapping that fits the safe region."""
    min_font = layout_settings["min_font"]
    max_font = layout_settings["max_font"]
    normal = _find_best_fit(
        draw,
        text,
        target_language,
        settings,
        layout_settings,
        max_w,
        max_h,
        min_font,
        max_font,
        allow_hyphenation=False,
    )
    hyphenated = _find_best_fit(
        draw,
        text,
        target_language,
        settings,
        layout_settings,
        max_w,
        max_h,
        min_font,
        max_font,
        allow_hyphenation=True,
    )

    if normal is None:
        return hyphenated
    if hyphenated is None or not hyphenated.hyphenated:
        return normal

    readable_floor = max(12, min(24, int(min(max_w, max_h) * 0.11)))
    meaningful_gain = (
        hyphenated.font_size >= normal.font_size + 4
        and hyphenated.font_size >= normal.font_size * 1.20
    )
    crosses_readability_floor = (
        normal.font_size < readable_floor <= hyphenated.font_size
    )
    if meaningful_gain or crosses_readability_floor:
        return hyphenated
    return normal


def _find_best_fit(
    draw,
    text,
    target_language,
    settings,
    layout_settings,
    max_w,
    max_h,
    min_font,
    max_font,
    allow_hyphenation,
):
    for font_size in range(max_font, min_font - 1, -1):
        font = _get_font_for_text(
            text,
            font_size,
            target_language,
            settings=settings,
        )
        spacing = max(1, int(font_size * layout_settings["spacing_ratio"]))
        stroke_width = max(1, font_size // 11)
        candidates = balanced_wrap_candidates(
            draw,
            text,
            font,
            max_w,
            stroke_width=stroke_width,
            allow_hyphenation=allow_hyphenation,
        )
        fitting = []

        for candidate in candidates:
            bbox = hitung_bbox_multiline(
                draw,
                candidate.text,
                font,
                spacing,
                stroke_width=stroke_width,
            )
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            if text_width > max_w or text_height > max_h:
                continue

            vertical_unused = max(0.0, (max_h - text_height) / max(1, max_h))
            aspect_imbalance = abs(
                (text_width / max(1, max_w)) - (text_height / max(1, max_h))
            )
            score = (
                candidate.penalty
                + (vertical_unused * 0.08)
                + (aspect_imbalance * 0.10)
            )
            fitting.append((score, candidate, bbox))

        if fitting:
            _, candidate, bbox = min(fitting, key=lambda item: item[0])
            return TextFitResult(
                font_size=font_size,
                wrapped_text=candidate.text,
                spacing=spacing,
                bbox=bbox,
                hyphenated=candidate.hyphenated,
            )
    return None


def pilih_setting_teks(box_width, box_height, text):
    clean_text = str(text).replace(" ", "").replace("\n", "")
    char_count = len(clean_text)
    area = box_width * box_height

    large_bubble = box_width >= 150 and box_height >= 130 and area >= 30000
    short_text = char_count <= 55
    very_short_text = char_count <= 28

    if large_bubble and very_short_text:
        return {
            "skala_w": 0.85,
            "skala_h": 0.78,
            "font_scale": 0.95,
            "spacing_ratio": 0.055,
            "max_font": 86,
            "min_font": 7,
        }

    if large_bubble and short_text:
        return {
            "skala_w": 0.82,
            "skala_h": 0.78,
            "font_scale": 0.94,
            "spacing_ratio": 0.060,
            "max_font": 82,
            "min_font": 7,
        }

    return {
        "skala_w": 0.76,
        "skala_h": 0.76,
        "font_scale": 0.92,
        "spacing_ratio": 0.075,
        "max_font": 76,
        "min_font": 6,
    }


def tulis_teks_jepang_vertikal(
    draw,
    text,
    font_func,
    x1,
    y1,
    x2,
    y2,
    setting,
    background_patch=False,
    settings=None,
):
    text = str(text).replace(" ", "").replace("\n", "")
    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)
    max_w = box_width * setting["skala_w"]
    max_h = box_height * setting["skala_h"]
    min_font_size = setting["min_font"]
    max_font_size = setting["max_font"]
    best_font_size = min_font_size
    best_columns = []

    for font_size in range(max_font_size, min_font_size - 1, -1):
        chars_per_col = max(1, int(max_h // font_size))
        columns = [text[i:i + chars_per_col] for i in range(0, len(text), chars_per_col)]
        if len(columns) * font_size <= max_w:
            best_font_size = font_size
            best_columns = columns
            break

    if not best_columns:
        chars_per_col = max(1, int(max_h // min_font_size))
        best_columns = [text[i:i + chars_per_col] for i in range(0, len(text), chars_per_col)]

    best_font_size = max(min_font_size, int(best_font_size * setting["font_scale"]))
    font = font_func(text, best_font_size, "japanese", settings=settings)
    actual_w = len(best_columns) * best_font_size
    actual_h = max(len(col) for col in best_columns) * best_font_size if best_columns else 0
    start_x = x1 + (box_width + actual_w) / 2 - best_font_size
    start_y = y1 + (box_height - actual_h) / 2
    stroke_w = max(1, best_font_size // 11)

    if background_patch:
        pad = max(6, best_font_size // 2)
        patch_box = [
            int(start_x - actual_w + best_font_size - pad),
            int(start_y - pad),
            int(start_x + best_font_size + pad),
            int(start_y + actual_h + pad),
        ]
        draw.rectangle(patch_box, fill=(255, 255, 255, 255))

    for column in best_columns:
        curr_y = start_y
        for char in column:
            offset_x, offset_y = 0, 0
            if char in ["。", "、", "."]:
                offset_x, offset_y = best_font_size * 0.6, -best_font_size * 0.6
            elif char == "ー":
                char = "︱"

            draw.text(
                (start_x + offset_x, curr_y + offset_y),
                char,
                font=font,
                fill=(255, 255, 255, 255),
                stroke_width=stroke_w,
                stroke_fill=(255, 255, 255, 255),
            )
            draw.text((start_x + offset_x, curr_y + offset_y), char, font=font, fill=(0, 0, 0, 255))
            curr_y += best_font_size
        start_x -= best_font_size


def tulis_teks_di_balon(
    draw,
    text,
    x1,
    y1,
    x2,
    y2,
    background_patch=False,
    target_language=None,
    settings=None,
    safe_region=False,
):
    cfg = _settings(settings)
    text = str(text).strip()
    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)
    setting = pilih_setting_teks(box_width, box_height, text)
    if safe_region:
        setting = {
            **setting,
            "skala_w": 0.96,
            "skala_h": 0.92,
            "font_scale": 0.98,
        }
    lang_key = (target_language or "").lower()
    if lang_key == "jepang":
        lang_key = "japanese"

    if lang_key == "japanese":
        tulis_teks_jepang_vertikal(
            draw,
            text,
            _get_font_for_text,
            x1,
            y1,
            x2,
            y2,
            setting,
            background_patch,
            settings=cfg,
        )
        return

    if not _has_non_latin(text):
        text = text.upper()

    max_w = box_width * setting["skala_w"]
    max_h = box_height * setting["skala_h"]
    min_font_size = setting["min_font"]
    fitted = cari_layout_teks_optimal(
        draw,
        text,
        target_language,
        cfg,
        setting,
        max_w,
        max_h,
    )
    if fitted is None:
        best_font_size = min_font_size
        font = _get_font_for_text(
            text,
            best_font_size,
            target_language,
            settings=cfg,
        )
        best_spacing = max(1, int(best_font_size * setting["spacing_ratio"]))
        best_wrap = bungkus_teks_per_kata(draw, text, font, max_w)
        stroke_w = max(1, best_font_size // 11)
        bbox = hitung_bbox_multiline(
            draw,
            best_wrap,
            font,
            best_spacing,
            stroke_width=stroke_w,
        )
    else:
        best_font_size = fitted.font_size
        best_spacing = fitted.spacing
        best_wrap = fitted.wrapped_text
        bbox = fitted.bbox

    font = _get_font_for_text(text, best_font_size, target_language, settings=cfg)
    stroke_w = max(1, best_font_size // 11)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    center_x, center_y = hitung_posisi_teks_terpusat(
        x1,
        y1,
        x2,
        y2,
        bbox,
    )

    if background_patch:
        pad = max(6, best_font_size // 2)
        ink_left = center_x + bbox[0]
        ink_top = center_y + bbox[1]
        patch_box = [
            int(ink_left - pad),
            int(ink_top - pad),
            int(ink_left + text_width + pad),
            int(ink_top + text_height + pad),
        ]
        try:
            draw.rounded_rectangle(patch_box, radius=max(4, best_font_size // 2), fill=(255, 255, 255))
        except Exception:
            draw.rectangle(patch_box, fill=(255, 255, 255))

    draw.multiline_text(
        (center_x, center_y),
        best_wrap,
        fill=(0, 0, 0),
        font=font,
        align="center",
        spacing=best_spacing,
        stroke_width=stroke_w,
        stroke_fill=(255, 255, 255),
    )
