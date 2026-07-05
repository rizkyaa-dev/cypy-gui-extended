import threading

from cypy.core.documents.folder_processor import proses_folder
from cypy.core.reporting import NullReporter
from tests.helpers import make_settings


def test_folder_processor_reuses_one_provider_lock(tmp_path, monkeypatch):
    settings = make_settings(tmp_path, supported_image_extensions=(".png",))
    for index in range(3):
        (tmp_path / f"page_{index}.png").write_bytes(b"not-a-real-image")

    seen_locks = []

    def fake_process(*args, **kwargs):
        seen_locks.append(kwargs["provider_lock"])
        return str(tmp_path / "out.png")

    monkeypatch.setattr("cypy.core.documents.folder_processor.proses_satu_gambar", fake_process)

    proses_folder(
        str(tmp_path),
        yolo_model=None,
        provider=object(),
        settings=settings,
        reporter=NullReporter(),
    )

    assert len(seen_locks) == 3
    assert all(isinstance(lock, threading.Lock().__class__) for lock in seen_locks)
    assert len({id(lock) for lock in seen_locks}) == 1
