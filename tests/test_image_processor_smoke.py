import os

import cv2
import numpy as np

from cypy.core.documents.image_processor import ImageProcessor
from cypy.core.reporting import NullReporter
from tests.helpers import make_settings


class FakeDetector:
    def detect(self, image):
        return [[10, 10, 70, 45]]


class FakeTranslationService:
    def __init__(self):
        self.calls = []

    def translate(self, image, provider, target_language="Indonesian"):
        self.calls.append((image.size, provider.provider_name, target_language))
        return {"1": "hello"}


class FakeProvider:
    provider_name = "fake"
    model_name = "fake-model"

    def validate_api_key(self):
        return True


def test_image_processor_smoke_with_fake_detector_and_translator(tmp_path):
    settings = make_settings(
        tmp_path,
        filter_sfx_aktif=False,
        mask_area_luar_box=False,
        manual_translation_override={},
    )
    image_path = tmp_path / "page.png"
    image = np.full((96, 80, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (10, 10), (70, 45), (245, 245, 245), thickness=-1)
    cv2.imwrite(str(image_path), image)

    translation_service = FakeTranslationService()
    processor = ImageProcessor(
        yolo_model=None,
        provider=FakeProvider(),
        settings=settings,
        reporter=NullReporter(),
        detector=FakeDetector(),
        translation_service=translation_service,
    )

    output_path = processor.process(str(image_path))

    assert output_path.endswith("_cypytr_id.png")
    assert os.path.exists(output_path)
    assert translation_service.calls
    assert cv2.imread(output_path) is not None
