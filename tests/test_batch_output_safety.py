import os
import threading

from cypy.core.documents.folder_processor import proses_folder
from cypy.core.reporting import NullReporter
from tests.helpers import make_settings


def test_folder_skips_translated_outputs_and_avoids_stem_collisions(
    tmp_path,
    monkeypatch,
):
    for name in ("page.jpg", "page.png", "page_cypytr_id.png"):
        (tmp_path / name).write_bytes(b"input")

    outputs = []

    def fake_process(image_path, *args, output_namer=None, **kwargs):
        output = output_namer.translated_image_path(image_path)
        outputs.append((os.path.basename(image_path), os.path.basename(output)))
        return output

    monkeypatch.setattr(
        "cypy.core.documents.folder_processor.proses_satu_gambar",
        fake_process,
    )

    proses_folder(
        str(tmp_path),
        yolo_model=None,
        provider=None,
        settings=make_settings(tmp_path),
        reporter=NullReporter(),
        provider_lock=threading.Lock(),
    )

    assert sorted(outputs) == [
        ("page.jpg", "page.jpg_cypytr_id.png"),
        ("page.png", "page.png_cypytr_id.png"),
    ]
