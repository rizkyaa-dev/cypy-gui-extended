import concurrent.futures
import os
import shutil
import threading
import uuid

import fitz

from cypy.core.documents.common import language_suffix, save_images_as_pdf
from cypy.core.documents.image_processor import proses_satu_gambar
from cypy.core.reporting import ensure_reporter
from cypy.core.settings import ProcessingSettings


def mulai_ritual_pdf(
    pdf_path,
    yolo_model,
    provider,
    target_language="Indonesian",
    settings=None,
    reporter=None,
    provider_lock=None,
):
    settings = settings or ProcessingSettings.from_config()
    reporter = ensure_reporter(reporter)
    provider_lock = provider_lock or threading.Lock()
    reporter.info(f"\nProcessing PDF: {os.path.basename(pdf_path)}")

    suffix = language_suffix(target_language, settings=settings)
    doc = fitz.open(pdf_path)
    temp_dir = os.path.join(
        settings.root_dir,
        "cypy_cache",
        f"pdf_temp_{uuid.uuid4().hex[:8]}",
    )
    os.makedirs(temp_dir, exist_ok=True)

    translated_paths = [None] * len(doc)
    total_pages = len(doc)
    failed_pages = 0

    try:
        reporter.info("Extracting PDF pages...")
        page_paths = []
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            img_path = os.path.join(temp_dir, f"page_{page_num:04d}.png")
            pix.save(img_path)
            page_paths.append((page_num, img_path))

        def process_pdf_page(page_num, img_path):
            expected_output = img_path.rsplit(".", 1)[0] + f"{suffix}.png"
            if os.path.exists(expected_output):
                reporter.info(f"\n[PDF {page_num + 1}/{total_pages}] Skipping (Already translated).")
                return page_num, expected_output, True

            reporter.info(f"\n[PDF {page_num + 1}/{total_pages}] Translating...")
            result_path = proses_satu_gambar(
                img_path,
                yolo_model,
                provider=provider,
                target_language=target_language,
                settings=settings,
                reporter=reporter,
                provider_lock=provider_lock,
            )
            return page_num, result_path or img_path, result_path is not None

        reporter.info("Translating pages...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(process_pdf_page, page_num, img_path): page_num
                for page_num, img_path in page_paths
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    page_num, result_path, succeeded = future.result()
                except Exception as exc:
                    page_num = futures[future]
                    reporter.error(f"  [!] Failed processing PDF page {page_num + 1}: {exc}")
                    result_path = page_paths[page_num][1]
                    succeeded = False

                translated_paths[page_num] = result_path
                if not succeeded:
                    failed_pages += 1

        if translated_paths:
            if failed_pages:
                reporter.warning(
                    f"[!] {failed_pages} page(s) could not be translated; "
                    "the original pages were preserved in the output PDF."
                )
            reporter.info("Saving final PDF...")
            output_pdf_path = pdf_path.rsplit(".", 1)[0] + f"{suffix}.pdf"
            if save_images_as_pdf(translated_paths, output_pdf_path):
                reporter.info(f"Done! Saved at: {output_pdf_path}")
                return output_pdf_path
        return None
    finally:
        doc.close()
        shutil.rmtree(temp_dir, ignore_errors=True)
