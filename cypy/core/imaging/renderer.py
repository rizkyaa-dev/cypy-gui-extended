import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from cypy.core.imaging.bubble_geometry import analyze_bubble_geometry
from cypy.core.imaging.text_layout import tulis_teks_di_balon
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
    if geometry is not None:
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


def _erase_detected_interior(image, geometry):
    mask = Image.fromarray(np.asarray(geometry.interior_mask, dtype=np.uint8))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.2))
    image.paste((255, 255, 255), geometry.roi_box, mask)
