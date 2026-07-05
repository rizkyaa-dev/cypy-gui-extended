import concurrent.futures
import os
import threading

from cypy.core.documents.common import language_suffix, natural_sort_key
from cypy.core.documents.image_pipeline import OutputNamer
from cypy.core.documents.image_processor import proses_satu_gambar
from cypy.core.reporting import ensure_reporter
from cypy.core.settings import ProcessingSettings


def proses_folder(
    folder_path,
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
    files = sorted(
        [
            filename
            for filename in os.listdir(folder_path)
            if filename.lower().endswith(settings.supported_image_extensions)
            and not OutputNamer.is_translated_path(filename)
        ],
        key=natural_sort_key,
    )

    if not files:
        reporter.warning(f"  [!] No supported image files found in: {folder_path}")
        return

    total = len(files)
    reporter.info(f"\n[Batch] Found {total} images in folder.")
    success = 0
    failed = 0
    suffix = language_suffix(target_language, settings=settings)
    stem_counts = {}
    for filename in files:
        stem = os.path.splitext(filename)[0].casefold()
        stem_counts[stem] = stem_counts.get(stem, 0) + 1

    def process_file(filename, index):
        file_path = os.path.join(folder_path, filename)
        stem, extension = os.path.splitext(file_path)
        if stem_counts[os.path.basename(stem).casefold()] > 1:
            expected_output = f"{stem}.{extension.lstrip('.')}{suffix}.png"
        else:
            expected_output = f"{stem}{suffix}.png"
        output_namer = OutputNamer(
            settings,
            target_language,
            source_path=file_path,
            output_path=expected_output,
        )

        if os.path.exists(expected_output):
            reporter.info(f"\n[{index}/{total}] Skipping {filename} (Already translated).")
            return True

        reporter.info(f"\n[{index}/{total}] Processing {filename}...")
        result = proses_satu_gambar(
            file_path,
            yolo_model,
            provider=provider,
            target_language=target_language,
            settings=settings,
            reporter=reporter,
            provider_lock=provider_lock,
            output_namer=output_namer,
        )
        return bool(result)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(process_file, filename, index): filename
            for index, filename in enumerate(files, start=1)
        }

        for future in concurrent.futures.as_completed(futures):
            try:
                ok = future.result()
            except Exception as exc:
                reporter.error(f"  [!] Failed processing {futures[future]}: {exc}")
                ok = False

            if ok:
                success += 1
            else:
                failed += 1

    reporter.info(f"\n[Batch] Completed! Success: {success}, Failed: {failed}, Total: {total}")
