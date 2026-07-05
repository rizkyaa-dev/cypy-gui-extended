import os
import threading

import cv2
from PIL import Image, ImageDraw

from cypy.core.detection.detector import YoloBubbleDetector
from cypy.core.documents.image_pipeline import (
    BubbleExtractionPipeline,
    LandscapeSplitter,
    MosaicPipeline,
    OutputNamer,
)
from cypy.core.errors import ProviderAuthError, ProviderRateLimitError
from cypy.core.filesystem import atomic_replace
from cypy.core.imaging.mosaic import shrink_crops_to_fit
from cypy.core.imaging.renderer import render_translation
from cypy.core.reporting import ensure_reporter
from cypy.core.settings import ProcessingSettings
from cypy.core.translation import MosaicTranslationService, ProviderCallGuard


_YOLO_LOCK = threading.Lock()


class ImageProcessor:
    def __init__(
        self,
        yolo_model,
        provider,
        target_language="Indonesian",
        settings=None,
        reporter=None,
        translation_service=None,
        detector=None,
        provider_lock=None,
        output_namer=None,
        bubble_pipeline=None,
        mosaic_pipeline=None,
        landscape_splitter=None,
    ):
        self.yolo_model = yolo_model
        self.provider = provider
        self.target_language = target_language
        self.settings = settings or ProcessingSettings.from_config()
        self.reporter = ensure_reporter(reporter)
        self.detector = detector or YoloBubbleDetector(yolo_model, lock=_YOLO_LOCK)
        self.provider_lock = provider_lock
        self.translation_service = translation_service or MosaicTranslationService(
            provider_guard=ProviderCallGuard(provider_lock)
        )
        self.output_namer = output_namer or OutputNamer(self.settings, target_language)
        self.bubble_pipeline = bubble_pipeline or BubbleExtractionPipeline(
            self.detector,
            self.settings,
        )
        self.mosaic_pipeline = mosaic_pipeline or MosaicPipeline(
            self.settings,
            self.output_namer,
        )
        self.landscape_splitter = landscape_splitter or LandscapeSplitter(
            self.settings,
            self.output_namer,
            self.reporter,
        )

    def process(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            self.reporter.error("[!] Image file is corrupt or unreadable.")
            return None

        image_height, image_width = img.shape[:2]
        ratio = image_width / image_height

        if ratio > 1.2:
            return self.landscape_splitter.process(
                image_path,
                img,
                ratio,
                self.process_page,
            )

        return self.process_page(image_path)

    def process_page(self, image_path):
        self.reporter.info(f"\nTranslating: {os.path.basename(image_path)}")

        img = cv2.imread(image_path)

        if img is None:
            self.reporter.error("[!] Image file is corrupt or unreadable.")
            return None

        image_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(image_pil)

        crops, coordinates = self.bubble_pipeline.extract(img, image_path)

        if not crops:
            self.reporter.info("  No text bubbles found.")
            output_path = self.output_namer.translated_image_path(image_path)
            atomic_replace(output_path, lambda temp_path: image_pil.save(temp_path, format="PNG"))
            return output_path

        self.reporter.info(f"  Found {len(crops)} speech bubbles...")
        mosaic = self.mosaic_pipeline.build(crops)
        self.mosaic_pipeline.save_preview(image_path, mosaic)

        self.reporter.info(
            f"  Translating with {self.provider.provider_name} ({self.provider.model_name})..."
        )
        translations = self.translate_mosaic(mosaic)

        if not translations:
            self.reporter.warning("  [!] Translation failed.")
            return None

        if self.settings.manual_translation_override:
            translations.update(self.settings.manual_translation_override)

        for bubble_id, text in translations.items():
            if bubble_id not in coordinates:
                continue

            text = str(text).strip()
            if text.upper() == "SKIP" or not text:
                continue

            render_translation(
                image_pil,
                draw,
                coordinates[bubble_id],
                text,
                self.target_language,
                settings=self.settings,
            )

        output_path = self.output_namer.translated_image_path(image_path)
        atomic_replace(output_path, lambda temp_path: image_pil.save(temp_path, format="PNG"))
        return output_path

    def translate_mosaic(self, mosaic):
        try:
            return self.translation_service.translate(
                mosaic,
                provider=self.provider,
                target_language=self.target_language,
            )
        except ProviderAuthError as exc:
            self.reporter.error(f"\n[!] {exc}")
        except ProviderRateLimitError:
            self.reporter.error(f"\n[!] Rate limit hit for {self.provider.provider_name}.")
        except Exception as exc:
            self.reporter.error(f"\n[!] {self.provider.provider_name} error: {exc}")

        return {}


def terjemahkan_mosaik(
    gambar_mosaik_pil,
    provider,
    target_language="Indonesian",
    max_retry=3,
    reporter=None,
    provider_lock=None,
):
    service = MosaicTranslationService(
        max_retry=max_retry,
        provider_guard=ProviderCallGuard(provider_lock),
    )
    reporter = ensure_reporter(reporter)

    try:
        return service.translate(
            gambar_mosaik_pil,
            provider=provider,
            target_language=target_language,
        )
    except ProviderAuthError as exc:
        reporter.error(f"\n[!] {exc}")
    except ProviderRateLimitError:
        reporter.error(f"\n[!] Rate limit hit for {provider.provider_name}.")
    except Exception as exc:
        reporter.error(f"\n[!] {provider.provider_name} error: {exc}")

    return {}


def perkecil_daftar_potongan_jika_mosaik_terlalu_tinggi(
    daftar_potongan,
    max_tinggi_mosaik=6000,
    jarak_antar_potongan=10,
    padding_atas_bawah=20,
):
    return shrink_crops_to_fit(
        daftar_potongan,
        max_height=max_tinggi_mosaik,
        spacing=jarak_antar_potongan,
        vertical_padding=padding_atas_bawah,
    )


def proses_satu_gambar(
    image_path,
    yolo_model,
    provider,
    target_language="Indonesian",
    settings=None,
    reporter=None,
    provider_lock=None,
    detector=None,
    output_namer=None,
):
    processor = ImageProcessor(
        yolo_model,
        provider,
        target_language=target_language,
        settings=settings,
        reporter=reporter,
        provider_lock=provider_lock,
        detector=detector,
        output_namer=output_namer,
    )
    return processor.process(image_path)


def _proses_satu_gambar_core(
    image_path,
    yolo_model,
    provider,
    target_language="Indonesian",
    settings=None,
    reporter=None,
    provider_lock=None,
    detector=None,
):
    processor = ImageProcessor(
        yolo_model,
        provider,
        target_language=target_language,
        settings=settings,
        reporter=reporter,
        provider_lock=provider_lock,
        detector=detector,
    )
    return processor.process_page(image_path)
