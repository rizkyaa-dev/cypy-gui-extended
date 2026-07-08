from PIL import Image

from cypy.core.imaging.translation_reflow import (
    RegionLayout,
    reflow_translations_for_layout,
)
from tests.helpers import make_settings


def test_reflow_keeps_accessory_label_short_and_dedupes_parent(tmp_path, monkeypatch):
    settings = make_settings(tmp_path)
    image = Image.new("RGB", (900, 900), "white")
    coordinates = {
        "1": (100, 100, 174, 196),
        "2": (20, 90, 150, 230),
    }
    layouts = {
        "1": RegionLayout("1", coordinates["1"], (118, 120, 176, 168), 7104, True),
        "2": RegionLayout("2", coordinates["2"], (28, 100, 145, 220), 18200, False),
    }
    monkeypatch.setattr(
        "cypy.core.imaging.translation_reflow._build_region_layouts",
        lambda image, coordinates: layouts,
    )

    result = reflow_translations_for_layout(
        image,
        {
            "1": "Pemimpin meminta perintah untuk pertemuan di level",
            "2": "Meminta perintah untuk pertemuan di level",
        },
        coordinates,
        "Indonesian",
        settings=settings,
    )

    assert result["1"] == "Pemimpin"
    assert result["2"] == "Meminta perintah untuk pertemuan di level"


def test_reflow_moves_accessory_overflow_to_nearest_parent(tmp_path, monkeypatch):
    settings = make_settings(tmp_path)
    image = Image.new("RGB", (900, 900), "white")
    coordinates = {
        "1": (100, 100, 174, 196),
        "2": (20, 90, 150, 230),
        "3": (600, 600, 750, 760),
    }
    layouts = {
        "1": RegionLayout("1", coordinates["1"], (118, 120, 176, 168), 7104, True),
        "2": RegionLayout("2", coordinates["2"], (28, 100, 145, 220), 18200, False),
        "3": RegionLayout("3", coordinates["3"], (610, 610, 740, 750), 24000, False),
    }
    monkeypatch.setattr(
        "cypy.core.imaging.translation_reflow._build_region_layouts",
        lambda image, coordinates: layouts,
    )

    result = reflow_translations_for_layout(
        image,
        {
            "1": "Pemimpin meminta perintah untuk pertemuan di level",
            "2": "Ya.",
            "3": "Jauh.",
        },
        coordinates,
        "Indonesian",
        settings=settings,
    )

    assert result["1"] == "Pemimpin"
    assert "meminta perintah" in result["2"].lower()
    assert result["3"] == "Jauh."
