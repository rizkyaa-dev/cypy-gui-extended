import concurrent.futures
import os
import platform
import shutil
import threading
import uuid
import zipfile

try:
    import rarfile
except ImportError:
    rarfile = None

from cypy.core.documents.archive_safety import safe_extract_all
from cypy.core.documents.common import language_suffix, natural_sort_key, save_images_as_pdf
from cypy.core.documents.image_pipeline import OutputNamer
from cypy.core.documents.image_processor import proses_satu_gambar
from cypy.core.reporting import ensure_reporter
from cypy.core.settings import ProcessingSettings


def setup_rarfile():
    if rarfile is None:
        return False

    if shutil.which("unrar") or shutil.which("unrar.exe"):
        return True

    os_name = platform.system()

    if os_name == "Windows":
        common_paths = [
            r"C:\Program Files\WinRAR\UnRAR.exe",
            r"C:\Program Files\WinRAR\WinRAR.exe",
            r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
            r"C:\Program Files (x86)\WinRAR\WinRAR.exe",
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ]
    elif os_name == "Darwin":
        common_paths = ["/usr/local/bin/unrar", "/opt/homebrew/bin/unrar"]
    else:
        common_paths = ["/usr/bin/unrar", "/usr/local/bin/unrar"]

    for path in common_paths:
        if os.path.exists(path):
            rarfile.UNRAR_TOOL = path
            return True

    return False


def _translate_archive_images(image_paths, process_func, reporter):
    translated_paths = [None] * len(image_paths)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(process_func, path, index): (index - 1, path)
            for index, path in enumerate(image_paths, start=1)
        }

        for future in concurrent.futures.as_completed(futures):
            result_index, original_path = futures[future]
            try:
                translated_paths[result_index] = future.result()
            except Exception as exc:
                reporter.error(
                    "  [!] Failed processing archive image "
                    f"{os.path.basename(original_path)}: {exc}"
                )
                translated_paths[result_index] = original_path

    return translated_paths


def mulai_ritual_archive(
    archive_path,
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
    reporter.info(f"\nProcessing Archive: {os.path.basename(archive_path)}")

    is_rar = archive_path.lower().endswith((".rar", ".cbr"))
    if is_rar and not setup_rarfile():
        reporter.error("\n[!] Error: 'rarfile' module is not installed or 'unrar' is missing.")
        reporter.error("Please ensure you have WinRAR or 7-Zip installed (or add unrar to PATH).")
        reporter.error("If you just ran the update, please RESTART cypy for the module to load.")
        return

    if is_rar:
        reporter.info("[Info] Archive detected. Output will be saved as .pdf")

    temp_dir = os.path.join(
        settings.root_dir,
        "cypy_cache",
        f"archive_temp_{uuid.uuid4().hex[:8]}",
    )
    os.makedirs(temp_dir, exist_ok=True)

    try:
        reporter.info("Extracting archive...")
        if is_rar:
            with rarfile.RarFile(archive_path) as archive:
                safe_extract_all(archive, temp_dir)
        else:
            with zipfile.ZipFile(archive_path, "r") as archive:
                safe_extract_all(archive, temp_dir)

        image_paths = []
        for root, _, files in os.walk(temp_dir):
            for filename in files:
                if filename.lower().endswith(settings.supported_image_extensions):
                    path = os.path.join(root, filename)
                    if not OutputNamer.is_translated_path(path):
                        image_paths.append(path)

        image_paths.sort(key=natural_sort_key)
        total = len(image_paths)

        if total == 0:
            reporter.warning("[!] No images found in archive.")
            return

        reporter.info(f"Found {total} images. Starting translation...")
        suffix = language_suffix(target_language, settings=settings)

        def process_archive_file(img_path, index):
            expected_output = img_path.rsplit(".", 1)[0] + f"{suffix}.png"
            if os.path.exists(expected_output):
                reporter.info(f"\n[{index}/{total}] Skipping (Already translated).")
                return expected_output

            reporter.info(f"\n[{index}/{total}] Translating {os.path.basename(img_path)}...")
            result = proses_satu_gambar(
                img_path,
                yolo_model,
                provider=provider,
                target_language=target_language,
                settings=settings,
                reporter=reporter,
                provider_lock=provider_lock,
            )
            return result if result else img_path

        translated_paths = _translate_archive_images(image_paths, process_archive_file, reporter)
        valid_paths = [path for path in translated_paths if path and os.path.exists(path)]

        if valid_paths:
            output_pdf_path = archive_path.rsplit(".", 1)[0] + f"{suffix}.pdf"
            reporter.info("\nCombining translated images into PDF...")
            if save_images_as_pdf(valid_paths, output_pdf_path):
                reporter.info(f"Done! Saved at: {output_pdf_path}")
    except Exception as exc:
        reporter.error(f"[!] Archive processing failed: {exc}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
