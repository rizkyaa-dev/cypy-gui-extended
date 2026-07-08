import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from cypy.core.imaging.bubble_geometry import analyze_bubble_geometry
from cypy.core.imaging.text_layout import tulis_teks_di_balon, tulis_teks_di_mask
from cypy.core.settings import ProcessingSettings


def _settings(settings=None):
    return settings or ProcessingSettings.from_config()


def render_translation(image, draw, box, text, target_language, settings=None):
    cfg = _settings(settings)
    x1, y1, x2, y2 = box
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    ratio = width / float(height)
    area_ratio = (width * height) / float(max(1, image.width * image.height))

    if ratio >= 3.2 and width >= image.width * 0.35:
        return

    if area_ratio >= 0.035 and ratio >= 2.8:
        return

    suspicious_flat_box = (
        ratio >= cfg.rasio_box_gepeng
        and width >= image.width * cfg.lebar_box_gepeng_ratio
        and height <= image.height * cfg.tinggi_box_gepeng_ratio
    )

    if cfg.pakai_patch_untuk_box_gepeng and suspicious_flat_box:
        tulis_teks_di_balon(
            draw,
            text,
            x1,
            y1,
            x2,
            y2,
            background_patch=True,
            target_language=target_language,
            settings=cfg,
        )
        return

    geometry = analyze_bubble_geometry(image, box)
    if _should_use_caption_patch(image, box, geometry):
        _draw_caption_patch(image, box)
        tulis_teks_di_balon(
            draw,
            text,
            x1,
            y1,
            x2,
            y2,
            background_patch=False,
            target_language=target_language,
            settings=cfg,
        )
        return

    if _should_use_small_label_patch(image, box, geometry):
        label_box = _draw_small_label_patch(image, box, geometry)
        tulis_teks_di_balon(
            draw,
            text,
            label_box[0],
            label_box[1],
            label_box[2],
            label_box[3],
            background_patch=False,
            target_language=target_language,
            settings=cfg,
            safe_region=True,
        )
        return

    if geometry is not None:
        _erase_existing_text(image, geometry)
        layout_mask = geometry.layout_mask if geometry.layout_mask is not None else geometry.safe_mask
        if layout_mask is not None and tulis_teks_di_mask(
            draw,
            text,
            geometry.roi_box,
            layout_mask,
            target_language=target_language,
            settings=cfg,
        ):
            return

        _erase_detected_interior(image, geometry)
        text_x1, text_y1, text_x2, text_y2 = geometry.text_box
        tulis_teks_di_balon(
            draw,
            text,
            text_x1,
            text_y1,
            text_x2,
            text_y2,
            background_patch=False,
            target_language=target_language,
            settings=cfg,
            safe_region=True,
        )
        return

    margin_x = int(width * cfg.mask_margin_ratio)
    margin_y = int(height * cfg.mask_margin_ratio)
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    overlay_draw.ellipse(
        [x1 + margin_x, y1 + margin_y, x2 - margin_x, y2 - margin_y],
        fill=(255, 255, 255, 255),
    )

    blurred = overlay.filter(ImageFilter.GaussianBlur(radius=8))
    image.paste(blurred, (0, 0), blurred)

    tulis_teks_di_balon(
        draw,
        text,
        x1,
        y1,
        x2,
        y2,
        background_patch=False,
        target_language=target_language,
        settings=cfg,
    )


def _should_use_caption_patch(image, box, geometry):
    x1, y1, x2, y2 = box
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    area_ratio = (width * height) / float(max(1, image.width * image.height))
    small_text_region = area_ratio <= 0.018 and width <= image.width * 0.24
    return small_text_region and (geometry is None or geometry.text_erase_mask is None)


def _should_use_small_label_patch(image, box, geometry):
    if geometry is None or geometry.safe_mask is None:
        return False

    x1, y1, x2, y2 = box
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    area_ratio = (width * height) / float(max(1, image.width * image.height))
    if area_ratio > 0.012 or width > image.width * 0.14 or height > image.height * 0.13:
        return False

    safe_mask = np.asarray(geometry.safe_mask) > 0
    if safe_mask.ndim != 2 or not np.any(safe_mask):
        return False
    ys, xs = np.where(safe_mask)
    safe_width = int(xs.max() - xs.min() + 1)
    return safe_width <= width * 0.72


def _draw_caption_patch(image, box):
    x1, y1, x2, y2 = map(int, box)
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    pad_x = max(4, int(round(width * 0.08)))
    pad_y = max(3, int(round(height * 0.08)))
    patch_box = [
        max(0, x1 - pad_x),
        max(0, y1 - pad_y),
        min(image.width, x2 + pad_x),
        min(image.height, y2 + pad_y),
    ]
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    radius = max(4, min(14, int(round(min(width, height) * 0.18))))
    overlay_draw.rounded_rectangle(
        patch_box,
        radius=radius,
        fill=(255, 255, 255, 255),
    )
    image.paste(overlay, (0, 0), overlay)


def _draw_small_label_patch(image, box, geometry):
    label_box = _small_label_box(image, box, geometry)
    if _erase_small_label_text(image, geometry):
        return label_box

    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    radius = max(4, min(12, int(round(min(label_box[2] - label_box[0], label_box[3] - label_box[1]) * 0.18))))
    overlay_draw.rounded_rectangle(
        label_box,
        radius=radius,
        fill=(255, 255, 255, 255),
    )
    image.paste(overlay, (0, 0), overlay)
    return label_box


def _erase_small_label_text(image, geometry):
    if geometry.text_erase_mask is None:
        return False

    mask = np.asarray(geometry.text_erase_mask, dtype=np.uint8)
    if not np.any(mask):
        return False

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.dilate(mask, kernel, iterations=1)
    mask = Image.fromarray(mask).filter(ImageFilter.GaussianBlur(radius=0.8))
    image.paste((255, 255, 255), geometry.roi_box, mask)
    return True


def _small_label_box(image, box, geometry):
    text_box = _small_label_box_from_existing_text(image, box, geometry)
    if text_box is not None:
        return text_box

    if geometry.layout_box is not None:
        x1, y1, x2, y2 = map(int, geometry.layout_box)
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        pad_x = max(4, int(round(width * 0.12)))
        pad_y = max(4, int(round(height * 0.08)))
        return [
            max(0, x1 - pad_x),
            max(0, y1 - pad_y),
            min(image.width, x2 + pad_x),
            min(image.height, y2 + pad_y),
        ]

    safe_mask = np.asarray(geometry.safe_mask) > 0
    ys, xs = np.where(safe_mask)
    if xs.size == 0 or ys.size == 0:
        return list(map(int, box))

    roi_x1, roi_y1, _, _ = geometry.roi_box
    safe_x1 = roi_x1 + int(xs.min())
    safe_y1 = roi_y1 + int(ys.min())
    safe_x2 = roi_x1 + int(xs.max()) + 1
    safe_y2 = roi_y1 + int(ys.max()) + 1
    safe_width = max(1, safe_x2 - safe_x1)
    safe_height = max(1, safe_y2 - safe_y1)
    pad_x = max(4, int(round(safe_width * 0.10)))
    pad_y = max(4, int(round(safe_height * 0.06)))
    return [
        max(0, safe_x1 - pad_x),
        max(0, safe_y1 - pad_y),
        min(image.width, safe_x2 + max(pad_x, 7)),
        min(image.height, safe_y2 + pad_y),
    ]


def _small_label_box_from_existing_text(image, box, geometry):
    if geometry.text_erase_mask is None:
        return None

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
    return [
        max(0, left),
        max(0, top),
        min(image.width, left + target_width),
        min(image.height, top + target_height),
    ]


def _erase_detected_interior(image, geometry):
    mask = Image.fromarray(np.asarray(geometry.interior_mask, dtype=np.uint8))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.2))
    image.paste((255, 255, 255), geometry.roi_box, mask)


def _erase_existing_text(image, geometry):
    if geometry.text_erase_mask is None:
        return False

    erase_mask = np.asarray(geometry.text_erase_mask, dtype=np.uint8)
    if geometry.layout_mask is not None:
        layout_mask = _expanded_layout_mask(geometry.layout_mask)
        constrained = np.where(layout_mask > 0, erase_mask, 0).astype(np.uint8)
        if not np.any(constrained):
            return False
        erase_mask = constrained

    mask = Image.fromarray(erase_mask)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.1))
    image.paste((255, 255, 255), geometry.roi_box, mask)
    return True


def _expanded_layout_mask(layout_mask):
    mask = np.asarray(layout_mask, dtype=np.uint8)
    ys, xs = np.where(mask > 0)
    if xs.size == 0 or ys.size == 0:
        return mask

    width = int(xs.max() - xs.min() + 1)
    height = int(ys.max() - ys.min() + 1)
    expand_x = min(48, max(8, int(round(width * 0.25))))
    expand_y = min(96, max(12, int(round(height * 0.55))))
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (expand_x * 2 + 1, expand_y * 2 + 1),
    )
    return cv2.dilate(mask, kernel, iterations=1)
