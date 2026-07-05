import cv2
import numpy as np
from PIL import Image

from cypy.core.settings import ProcessingSettings


def _settings(settings=None):
    return settings or ProcessingSettings.from_config()


def _overlap_1d(a1, a2, b1, b2):
    return max(0, min(a2, b2) - max(a1, b1))


def buat_crop_lega_tapi_tidak_nyamber(
    box,
    semua_box,
    lebar_img,
    tinggi_img,
    pad_x,
    pad_y,
    settings=None,
):
    cfg = _settings(settings)
    x1, y1, x2, y2 = box

    crop_x1 = max(0, x1 - pad_x)
    crop_y1 = max(0, y1 - pad_y)
    crop_x2 = min(lebar_img, x2 + pad_x)
    crop_y2 = min(tinggi_img, y2 + pad_y)

    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)

    for other in semua_box:
        if other == box:
            continue

        ox1, oy1, ox2, oy2 = other
        other_width = max(1, ox2 - ox1)
        other_height = max(1, oy2 - oy1)

        overlap_x = _overlap_1d(x1, x2, ox1, ox2) / float(min(box_width, other_width))
        overlap_y = _overlap_1d(y1, y2, oy1, oy2) / float(min(box_height, other_height))

        if overlap_x >= cfg.overlap_batas_crop:
            if oy1 >= y2:
                batas = (y2 + oy1) // 2
                crop_y2 = min(crop_y2, max(y2, batas))
            elif oy2 <= y1:
                batas = (oy2 + y1) // 2
                crop_y1 = max(crop_y1, min(y1, batas))

        if overlap_y >= cfg.overlap_batas_crop:
            if ox1 >= x2:
                batas = (x2 + ox1) // 2
                crop_x2 = min(crop_x2, max(x2, batas))
            elif ox2 <= x1:
                batas = (ox2 + x1) // 2
                crop_x1 = max(crop_x1, min(x1, batas))

    return int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)


def mask_luar_box_utama(potongan, crop_x1, crop_y1, x1, y1, x2, y2, settings=None):
    cfg = _settings(settings)
    if not cfg.mask_area_luar_box:
        return potongan

    local_x1 = x1 - crop_x1
    local_y1 = y1 - crop_y1
    local_x2 = x2 - crop_x1
    local_y2 = y2 - crop_y1

    mask_x1 = max(0, local_x1 - cfg.mask_margin)
    mask_y1 = max(0, local_y1 - cfg.mask_margin)
    mask_x2 = min(potongan.shape[1], local_x2 + cfg.mask_margin)
    mask_y2 = min(potongan.shape[0], local_y2 + cfg.mask_margin)

    masked = 255 * np.ones_like(potongan)
    masked[mask_y1:mask_y2, mask_x1:mask_x2] = potongan[mask_y1:mask_y2, mask_x1:mask_x2]
    return masked


def crop_bubble(image, box, all_boxes, settings=None):
    cfg = _settings(settings)
    x1, y1, x2, y2 = box
    image_height, image_width = image.shape[:2]
    box_width = max(1, x2 - x1)
    box_height = max(1, y2 - y1)

    pad_x = max(cfg.min_pad, int(box_width * cfg.pad_x_ratio))
    pad_y = max(cfg.min_pad, int(box_height * cfg.pad_y_ratio))

    crop_x1, crop_y1, crop_x2, crop_y2 = buat_crop_lega_tapi_tidak_nyamber(
        [x1, y1, x2, y2],
        all_boxes,
        image_width,
        image_height,
        pad_x,
        pad_y,
        settings=cfg,
    )

    crop = image[crop_y1:crop_y2, crop_x1:crop_x2].copy()
    if crop.size == 0:
        return None

    crop = mask_luar_box_utama(crop, crop_x1, crop_y1, x1, y1, x2, y2, settings=cfg)
    crop_pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))

    if cfg.skala_potongan_mosaik != 1:
        new_size = (
            max(1, int(crop_pil.width * cfg.skala_potongan_mosaik)),
            max(1, int(crop_pil.height * cfg.skala_potongan_mosaik)),
        )
        crop_pil = crop_pil.resize(new_size, Image.Resampling.LANCZOS)

    return crop_pil
