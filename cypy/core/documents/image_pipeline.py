import os
import re

import cv2

from cypy.core.detection.box_filters import (
    buang_kotak_ngawur,
    buang_kotak_raksasa_palsu,
    buang_kotak_sfx_dan_gambar,
    gabung_kotak_tumpang_tindih,
)
from cypy.core.documents.common import language_suffix, safe_remove
from cypy.core.filesystem import atomic_replace
from cypy.core.imaging.cropper import crop_bubble
from cypy.core.imaging.mosaic import build_numbered_mosaic


class OutputNamer:
    TRANSLATED_NAME_PATTERN = re.compile(r"_cypytr_[a-z0-9_-]+\.png$", re.IGNORECASE)

    def __init__(
        self,
        settings,
        target_language,
        source_path=None,
        output_path=None,
    ):
        self.settings = settings
        self.target_language = target_language
        self.source_path = os.path.abspath(source_path) if source_path else None
        self.output_path = os.path.abspath(output_path) if output_path else None

    @property
    def suffix(self):
        return language_suffix(self.target_language, settings=self.settings)

    def translated_image_path(self, image_path):
        if (
            self.source_path
            and self.output_path
            and os.path.abspath(image_path) == self.source_path
        ):
            return self.output_path
        return image_path.rsplit(".", 1)[0] + f"{self.suffix}.png"

    @classmethod
    def is_translated_path(cls, path):
        return bool(cls.TRANSLATED_NAME_PATTERN.search(os.path.basename(path)))

    def split_part_path(self, image_path, index):
        return image_path.rsplit(".", 1)[0] + f"_split{index}.png"

    def mosaic_preview_path(self, image_path):
        temp_mosaic_dir = os.path.join(self.settings.root_dir, "cypy_cache")
        return os.path.join(
            temp_mosaic_dir,
            f"mosaic_preview_{os.path.basename(image_path)}",
        )


class BubbleExtractionPipeline:
    def __init__(self, detector, settings):
        self.detector = detector
        self.settings = settings

    def extract(self, img, image_path):
        boxes = self.detect_boxes(img, image_path)
        crops, coordinates = self._build_crops(img, boxes)
        return crops, coordinates

    def detect_boxes(self, img, image_path):
        """Return the filtered boxes used by crop and translation rendering."""
        image_height, image_width = img.shape[:2]
        raw_boxes = self.detector.detect(img)
        boxes = buang_kotak_raksasa_palsu(raw_boxes, settings=self.settings)
        boxes = gabung_kotak_tumpang_tindih(boxes, settings=self.settings)
        boxes = buang_kotak_ngawur(
            boxes,
            image_width,
            image_height,
            settings=self.settings,
        )
        return buang_kotak_sfx_dan_gambar(
            img=img,
            boxes=boxes,
            image_name=image_path,
            settings=self.settings,
        )

    def _build_crops(self, img, boxes):
        crops = []
        coordinates = {}

        for order, box in enumerate(boxes, start=1):
            crop = crop_bubble(img, box, boxes, settings=self.settings)
            if crop is None:
                continue

            bubble_id = str(order)
            crops.append((bubble_id, crop))
            coordinates[bubble_id] = tuple(box)

        return crops, coordinates


class MosaicPipeline:
    def __init__(self, settings, output_namer):
        self.settings = settings
        self.output_namer = output_namer

    def build(self, crops):
        return build_numbered_mosaic(crops, settings=self.settings)

    def save_preview(self, image_path, mosaic):
        mosaic_path = self.output_namer.mosaic_preview_path(image_path)
        os.makedirs(os.path.dirname(mosaic_path), exist_ok=True)
        atomic_replace(mosaic_path, lambda temp_path: mosaic.save(temp_path))
        return mosaic_path


class LandscapeSplitter:
    def __init__(self, settings, output_namer, reporter):
        self.settings = settings
        self.output_namer = output_namer
        self.reporter = reporter

    def process(self, image_path, img, ratio, process_page):
        image_height, image_width = img.shape[:2]
        num_splits = max(2, round(ratio / 0.71))
        self.reporter.info(
            f"  [Auto-Split] Wide image detected (ratio {ratio:.2f}). "
            f"Splitting into {num_splits} parts..."
        )

        split_width = image_width // num_splits
        splits = []
        try:
            for index in range(num_splits):
                x_end = image_width - (index * split_width)
                x_start = x_end - split_width
                if index == num_splits - 1:
                    x_start = 0

                img_part = img[:, x_start:x_end]
                part_path = self.output_namer.split_part_path(image_path, index + 1)
                splits.append([None, part_path])
                if not cv2.imwrite(part_path, img_part):
                    raise OSError(f"Failed to write split image: {part_path}")

                self.reporter.info(f"  Translating Part {index + 1} (Right-to-Left)...")
                splits[-1][0] = process_page(part_path)

            valid_results = [result for result, _ in splits if result]
            if len(valid_results) != num_splits:
                return None

            result_images = [cv2.imread(result) for result in valid_results]
            if any(image is None for image in result_images):
                return None

            result_images.reverse()
            target_height = max(image.shape[0] for image in result_images)

            for index, result_image in enumerate(result_images):
                height, width = result_image.shape[:2]
                if height != target_height:
                    result_images[index] = cv2.resize(
                        result_image,
                        (int(width * target_height / height), target_height),
                    )

            combined = cv2.hconcat(result_images)
            output_path = self.output_namer.translated_image_path(image_path)

            def write_combined(temp_path):
                if not cv2.imwrite(temp_path, combined):
                    raise OSError(f"Failed to write translated image: {output_path}")

            atomic_replace(output_path, write_combined)
            return output_path
        finally:
            for result_path, part_path in splits:
                safe_remove(result_path, reporter=self.reporter)
                safe_remove(part_path, reporter=self.reporter)
