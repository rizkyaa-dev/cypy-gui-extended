import numpy as np
from PIL import Image, ImageDraw

from cypy.core.imaging.bubble_geometry import (
    analyze_bubble_geometry,
    largest_inner_rectangle,
)
from cypy.core.imaging.text_layout import hitung_posisi_teks_terpusat


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


def test_geometry_rejects_unbounded_white_region():
    image = Image.new("RGB", (100, 100), "white")

    assert analyze_bubble_geometry(image, (0, 0, 100, 100)) is None


def test_center_position_accounts_for_negative_font_bearing():
    origin = hitung_posisi_teks_terpusat(
        10,
        20,
        110,
        80,
        (-5, 3, 45, 23),
    )

    assert origin == (40.0, 37.0)
