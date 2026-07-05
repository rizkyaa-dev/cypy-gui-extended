import os
import re

import fitz

from cypy.core.filesystem import atomic_replace
from cypy.core.reporting import ensure_reporter
from cypy.core.settings import ProcessingSettings


def _settings(settings=None):
    return settings or ProcessingSettings.from_config()


def language_suffix(target_language, settings=None):
    cfg = _settings(settings)
    lang_code = cfg.lang_codes.get(
        (target_language or "").lower(),
        target_language[:2].lower() if target_language else "tr",
    )
    return f"_cypytr_{lang_code}"


def natural_sort_key(path):
    return [
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", os.fspath(path))
    ]


def safe_remove(path, reporter=None):
    if not path:
        return

    reporter = ensure_reporter(reporter)

    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError as exc:
        reporter.warning(f"  [!] Failed to remove temp file {path}: {exc}")


def save_images_as_pdf(image_paths, output_pdf_path):
    paths = list(image_paths)
    if not paths:
        return False

    output = fitz.open()
    try:
        for path in paths:
            with fitz.open(path) as image_document:
                pdf_bytes = image_document.convert_to_pdf()
            with fitz.open("pdf", pdf_bytes) as page_document:
                output.insert_pdf(page_document)

        atomic_replace(
            output_pdf_path,
            lambda temp_path: output.save(temp_path, garbage=4, deflate=True),
        )
        return True
    finally:
        output.close()
