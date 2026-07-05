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
