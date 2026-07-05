import fitz

from cypy.core.documents.pdf_processor import mulai_ritual_pdf
from cypy.core.reporting import MemoryReporter
from tests.helpers import make_settings


def test_failed_pdf_page_is_preserved_in_output(tmp_path, monkeypatch):
    source_path = tmp_path / "source.pdf"
    document = fitz.open()
    document.new_page(width=100, height=100)
    document.new_page(width=100, height=100)
    document.save(source_path)
    document.close()

    calls = 0

    def fake_process(image_path, *args, **kwargs):
        nonlocal calls
        calls += 1
        return None if calls == 1 else image_path

    monkeypatch.setattr(
        "cypy.core.documents.pdf_processor.proses_satu_gambar",
        fake_process,
    )
    reporter = MemoryReporter()

    output_path = mulai_ritual_pdf(
        str(source_path),
        yolo_model=None,
        provider=None,
        settings=make_settings(tmp_path),
        reporter=reporter,
    )

    with fitz.open(output_path) as output:
        assert output.page_count == 2
    assert any(
        level == "warning" and "original pages were preserved" in message
        for level, message in reporter.messages
    )
