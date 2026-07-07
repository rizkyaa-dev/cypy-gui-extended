import numpy as np
from PIL import Image, ImageDraw

from cypy.core.imaging.bubble_geometry import (
    _build_layout_mask,
    analyze_bubble_geometry,
    largest_inner_rectangle,
)
from cypy.core.imaging.text_layout import hitung_posisi_teks_terpusat, tulis_teks_di_mask
from tests.helpers import make_settings


def test_largest_inner_rectangle_stays_inside_mask():
    mask = np.zeros((8, 10), dtype=np.uint8)
    mask[2:7, 3:9] = 255

    assert largest_inner_rectangle(mask) == (3, 2, 9, 7)


def test_geometry_finds_centered_safe_region_inside_bubble():
    image = Image.new("RGB", (220, 220), (150, 150, 150))
    draw = ImageDraw.Draw(image)
    draw.ellipse((20, 15, 200, 205), fill="white", outline="black", width=5)
    draw.rectangle((96, 55, 103, 165), fill="black")
    draw.rectangle((70, 105, 135, 112), fill="black")

    geometry = analyze_bubble_geometry(image, (15, 10, 205, 210))

    assert geometry is not None
    x1, y1, x2, y2 = geometry.text_box
    assert 30 <= x1 < x2 <= 190
    assert 25 <= y1 < y2 <= 195
    assert abs(((x1 + x2) / 2) - 110) < 12
    assert abs(((y1 + y2) / 2) - 110) < 12
    assert geometry.interior_mask.shape == (200, 190)
    assert geometry.safe_mask.shape == (200, 190)
    assert geometry.layout_mask.shape == (200, 190)
    assert geometry.layout_box is not None
    assert geometry.text_erase_mask is not None


def test_geometry_rejects_unbounded_white_region():
    image = Image.new("RGB", (100, 100), "white")

    assert analyze_bubble_geometry(image, (0, 0, 100, 100)) is None


def test_layout_mask_is_constrained_to_inner_safe_rectangle():
    safe_mask = np.full((100, 180), 255, dtype=np.uint8)

    layout_mask = _build_layout_mask(safe_mask, (115, 25, 155, 80))

    ys, xs = np.where(layout_mask > 0)
    assert xs.min() >= 111
    assert xs.max() <= 159
    assert ys.min() >= 21
    assert ys.max() <= 84
    assert np.mean(layout_mask > 0) < 0.20


def test_layout_mask_can_shift_toward_strong_text_anchor():
    safe_mask = np.full((100, 220), 255, dtype=np.uint8)

    layout_mask = _build_layout_mask(
        safe_mask,
        (50, 20, 100, 80),
        anchor_box=(130, 25, 160, 75),
    )

    ys, xs = np.where(layout_mask > 0)
    assert xs.min() >= 70
    assert xs.max() <= 156
    assert ys.min() <= 16
    assert ys.max() >= 84


def test_center_position_accounts_for_negative_font_bearing():
    origin = hitung_posisi_teks_terpusat(
        10,
        20,
        110,
        80,
        (-5, 3, 45, 23),
    )

    assert origin == (40.0, 37.0)


def test_mask_aware_text_layout_draws_inside_bubble_shape(tmp_path):
    settings = make_settings(tmp_path)
    image = Image.new("RGB", (140, 120), "white")
    draw = ImageDraw.Draw(image)
    mask = np.zeros((100, 120), dtype=np.uint8)
    yy, xx = np.ogrid[:100, :120]
    mask[((xx - 60) ** 2 / 54 ** 2) + ((yy - 50) ** 2 / 42 ** 2) <= 1] = 255

    ok = tulis_teks_di_mask(
        draw,
        "halo dunia ini test",
        (10, 10, 130, 110),
        mask,
        target_language="Indonesian",
        settings=settings,
    )

    assert ok is True
