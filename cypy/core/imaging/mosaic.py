from PIL import Image, ImageDraw, ImageFont

from cypy.core.settings import ProcessingSettings


def _settings(settings=None):
    return settings or ProcessingSettings.from_config()


def shrink_crops_to_fit(
    crops,
    max_height=6000,
    spacing=10,
    vertical_padding=20,
):
    if not crops:
        return crops

    total_crop_height = sum(crop.height for _, crop in crops)
    total_spacing = len(crops) * spacing + vertical_padding
    initial_height = total_crop_height + total_spacing

    if initial_height <= max_height:
        return crops

    target_crop_height = max(1, max_height - total_spacing)
    ratio = target_crop_height / float(total_crop_height)

    resized = []
    for number, crop in crops:
        new_size = (
            max(1, int(crop.width * ratio)),
            max(1, int(crop.height * ratio)),
        )
        resized.append((number, crop.resize(new_size, Image.Resampling.LANCZOS)))

    return resized


def build_numbered_mosaic(crops, settings=None):
    cfg = _settings(settings)
    margin_left = cfg.margin_kiri_nomor
    margin_right = cfg.margin_kanan
    spacing = cfg.jarak_antar_potongan

    crops = shrink_crops_to_fit(
        crops,
        max_height=cfg.max_tinggi_mosaik,
        spacing=spacing,
        vertical_padding=20,
    )

    mosaic_width = max(
        cfg.lebar_mosaik_min,
        max(crop.width for _, crop in crops) + margin_left + margin_right,
    )
    mosaic_height = sum(crop.height for _, crop in crops) + (len(crops) * spacing) + 20
    mosaic = Image.new("RGB", (mosaic_width, mosaic_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(mosaic)
    font_number = ImageFont.load_default()

    try:
        font_number = ImageFont.truetype(cfg.font_manga, 40)
    except Exception:
        pass

    y_offset = 10
    for number, crop in crops:
        draw.text(
            (5, y_offset + (crop.height // 2) - 20),
            number,
            fill=(255, 0, 0),
            font=font_number,
        )
        mosaic.paste(crop, (margin_left, y_offset))
        y_offset += crop.height + spacing

    return mosaic
