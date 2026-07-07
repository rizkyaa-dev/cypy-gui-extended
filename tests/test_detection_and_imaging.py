from PIL import Image, ImageDraw
import numpy as np

from cypy.core.detection.box_filters import (
    _area_box,
    _irisan_box,
    buang_kotak_sfx_dan_gambar,
    buang_kotak_raksasa_palsu,
    gabung_kotak_tumpang_tindih,
)
from cypy.core.detection.text_assist import TextAssistedBoxRefiner
from cypy.core.detection.text_onnx import TextBox
from cypy.core.documents.image_pipeline import BubbleExtractionPipeline
from cypy.core.imaging.cropper import buat_crop_lega_tapi_tidak_nyamber, crop_bubble
from cypy.core.imaging.bubble_geometry import BubbleGeometry
from cypy.core.imaging.mosaic import build_numbered_mosaic
from cypy.core.imaging.renderer import render_translation
from tests.helpers import make_settings


def test_box_area_intersection_and_merge():
    assert _area_box([0, 0, 10, 10]) == 100
    assert _irisan_box([0, 0, 10, 10], [5, 5, 15, 15]) == 25

    merged = gabung_kotak_tumpang_tindih([[0, 0, 10, 10], [2, 2, 11, 11]])

    assert merged == [[0, 0, 11, 11]]


def test_large_false_positive_box_is_removed():
    boxes = [[0, 0, 100, 100], [10, 10, 30, 30], [70, 70, 90, 90]]

    assert buang_kotak_raksasa_palsu(boxes) == [[10, 10, 30, 30], [70, 70, 90, 90]]


def test_crop_bounds_and_masking_use_custom_settings(tmp_path):
    settings = make_settings(
        tmp_path,
        min_pad=8,
        pad_x_ratio=1,
        pad_y_ratio=1,
        mask_area_luar_box=True,
        mask_margin=0,
        skala_potongan_mosaik=1,
    )
    image = np.zeros((30, 30, 3), dtype=np.uint8)
    box = [2, 2, 12, 12]

    bounds = buat_crop_lega_tapi_tidak_nyamber(
        box,
        [box],
        lebar_img=30,
        tinggi_img=30,
        pad_x=20,
        pad_y=20,
        settings=settings,
    )
    crop = crop_bubble(image, box, [box], settings=settings)

    assert bounds == (0, 0, 30, 30)
    assert crop.size == (22, 22)


def test_mosaic_uses_custom_settings(tmp_path):
    settings = make_settings(
        tmp_path,
        margin_kiri_nomor=20,
        margin_kanan=7,
        jarak_antar_potongan=3,
        lebar_mosaik_min=10,
        max_tinggi_mosaik=1000,
    )

    mosaic = build_numbered_mosaic(
        [("1", Image.new("RGB", (30, 10))), ("2", Image.new("RGB", (40, 20)))],
        settings=settings,
    )

    assert mosaic.size == (67, 56)


def test_sfx_filter_respects_disabled_custom_settings(tmp_path):
    settings = make_settings(tmp_path, filter_sfx_aktif=False)
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    boxes = [[0, 0, 20, 20]]

    assert buang_kotak_sfx_dan_gambar(image, boxes, settings=settings) is boxes


def test_text_assist_expands_box_to_include_nearby_text(tmp_path):
    class FakeTextDetector:
        def detect(self, image):
            return (TextBox(28, 12, 48, 30, 0.9),)

    settings = make_settings(
        tmp_path,
        text_assist_expand_margin=4,
        text_assist_orphan_recovery=False,
    )
    image = np.full((80, 80, 3), 255, dtype=np.uint8)
    refiner = TextAssistedBoxRefiner(FakeTextDetector(), settings)

    boxes = refiner.refine(image, [[10, 10, 32, 34]])

    assert boxes == [[10, 8, 52, 34]]


def test_text_assist_recovers_orphan_text_from_white_region(tmp_path):
    class FakeTextDetector:
        def detect(self, image):
            return (TextBox(42, 42, 56, 56, 0.9),)

    settings = make_settings(
        tmp_path,
        text_assist_expand_margin=8,
        text_assist_orphan_recovery=True,
    )
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[30:70, 30:70] = 255
    refiner = TextAssistedBoxRefiner(FakeTextDetector(), settings)

    boxes = refiner.refine(image, [])

    assert boxes == [[30, 30, 70, 70]]


def test_text_assist_keeps_original_boxes_when_detector_fails(tmp_path):
    class FailingTextDetector:
        def detect(self, image):
            raise RuntimeError("detector unavailable")

    settings = make_settings(tmp_path)
    image = np.zeros((30, 30, 3), dtype=np.uint8)
    refiner = TextAssistedBoxRefiner(FailingTextDetector(), settings)

    assert refiner.refine(image, [[1, 2, 10, 12]]) == [[1, 2, 10, 12]]


def test_bubble_pipeline_uses_injected_text_refiner(tmp_path):
    class FakeBubbleDetector:
        def detect(self, image):
            return [[10, 10, 20, 20]]

    class FakeTextRefiner:
        def refine(self, image, boxes):
            assert boxes == [[10, 10, 20, 20]]
            return [[8, 8, 24, 24]]

    settings = make_settings(
        tmp_path,
        text_assist_enabled=True,
        filter_sfx_aktif=False,
    )
    pipeline = BubbleExtractionPipeline(
        FakeBubbleDetector(),
        settings,
        text_refiner=FakeTextRefiner(),
    )
    image = np.full((40, 40, 3), 255, dtype=np.uint8)

    assert pipeline.detect_boxes(image, "page.png") == [[8, 8, 24, 24]]


def test_renderer_receives_custom_settings_for_flat_patch(tmp_path, monkeypatch):
    settings = make_settings(
        tmp_path,
        pakai_patch_untuk_box_gepeng=True,
        rasio_box_gepeng=2,
        lebar_box_gepeng_ratio=0.2,
        tinggi_box_gepeng_ratio=0.5,
    )
    captured = {}

    def fake_write(*args, **kwargs):
        captured["background_patch"] = kwargs["background_patch"]
        captured["settings"] = kwargs["settings"]

    monkeypatch.setattr("cypy.core.imaging.renderer.tulis_teks_di_balon", fake_write)

    image = Image.new("RGB", (200, 100), "white")
    render_translation(
        image,
        ImageDraw.Draw(image),
        [10, 10, 110, 50],
        "hello",
        "Indonesian",
        settings=settings,
    )

    assert captured == {"background_patch": True, "settings": settings}


def test_renderer_uses_analyzed_safe_text_region(tmp_path, monkeypatch):
    settings = make_settings(tmp_path, pakai_patch_untuk_box_gepeng=False)
    geometry = BubbleGeometry(
        roi_box=(10, 10, 50, 50),
        text_box=(18, 16, 43, 45),
        interior_mask=np.full((40, 40), 255, dtype=np.uint8),
    )
    captured = {}

    monkeypatch.setattr(
        "cypy.core.imaging.renderer.analyze_bubble_geometry",
        lambda image, box: geometry,
    )

    def fake_write(draw, text, x1, y1, x2, y2, **kwargs):
        captured["box"] = (x1, y1, x2, y2)
        captured["safe_region"] = kwargs["safe_region"]

    monkeypatch.setattr("cypy.core.imaging.renderer.tulis_teks_di_balon", fake_write)
    image = Image.new("RGB", (100, 100), "white")

    render_translation(
        image,
        ImageDraw.Draw(image),
        [10, 10, 50, 50],
        "hello",
        "Indonesian",
        settings=settings,
    )

    assert captured == {
        "box": geometry.text_box,
        "safe_region": True,
    }


def test_renderer_prefers_conservative_layout_mask(tmp_path, monkeypatch):
    settings = make_settings(tmp_path, pakai_patch_untuk_box_gepeng=False)
    safe_mask = np.full((40, 40), 255, dtype=np.uint8)
    layout_mask = np.zeros((40, 40), dtype=np.uint8)
    layout_mask[12:30, 18:34] = 255
    geometry = BubbleGeometry(
        roi_box=(10, 10, 50, 50),
        text_box=(18, 16, 43, 45),
        interior_mask=safe_mask,
        safe_mask=safe_mask,
        layout_mask=layout_mask,
    )
    captured = {}

    monkeypatch.setattr(
        "cypy.core.imaging.renderer.analyze_bubble_geometry",
        lambda image, box: geometry,
    )

    def fake_mask_write(draw, text, roi_box, mask, **kwargs):
        captured["roi_box"] = roi_box
        captured["mask"] = mask
        captured["settings"] = kwargs["settings"]
        return True

    monkeypatch.setattr("cypy.core.imaging.renderer.tulis_teks_di_mask", fake_mask_write)
    image = Image.new("RGB", (100, 100), "white")

    render_translation(
        image,
        ImageDraw.Draw(image),
        [10, 10, 50, 50],
        "hello",
        "Indonesian",
        settings=settings,
    )

    assert captured["roi_box"] == geometry.roi_box
    assert captured["mask"] is layout_mask
    assert captured["settings"] is settings
