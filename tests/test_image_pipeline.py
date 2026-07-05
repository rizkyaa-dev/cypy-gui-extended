import os

import cv2
import numpy as np

from cypy.core.documents.image_pipeline import OutputNamer
from cypy.core.documents.image_processor import ImageProcessor
from cypy.core.reporting import NullReporter
from tests.helpers import make_settings


class EmptyDetector:
    def detect(self, image):
        return []


class UnusedProvider:
    provider_name = "unused"
    model_name = "unused"

    def validate_api_key(self):
        return True

    def translate_image(self, image, prompt):
        raise AssertionError("provider should not be called when no bubbles are detected")


def test_output_namer_uses_settings_suffix(tmp_path):
    settings = make_settings(tmp_path, lang_codes={"klingon": "tlh"})
    namer = OutputNamer(settings, "Klingon")

    assert namer.translated_image_path(str(tmp_path / "page.jpg")).endswith("_cypytr_tlh.png")
    assert namer.split_part_path(str(tmp_path / "page.jpg"), 2).endswith("_split2.png")
    assert namer.mosaic_preview_path(str(tmp_path / "page.jpg")).endswith(
        os.path.join("cypy_cache", "mosaic_preview_page.jpg")
    )


def test_image_processor_no_bubbles_writes_translated_copy(tmp_path):
    settings = make_settings(tmp_path)
    image_path = tmp_path / "page.png"
    cv2.imwrite(str(image_path), np.full((32, 24, 3), 255, dtype=np.uint8))

    processor = ImageProcessor(
        yolo_model=None,
        provider=UnusedProvider(),
        settings=settings,
        reporter=NullReporter(),
        detector=EmptyDetector(),
    )

    output_path = processor.process(str(image_path))

    assert output_path.endswith("_cypytr_id.png")
    assert os.path.exists(output_path)
