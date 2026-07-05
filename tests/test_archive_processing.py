import os
import time
from dataclasses import dataclass

import pytest

from cypy.core.documents.archive_processor import _translate_archive_images
from cypy.core.documents.archive_safety import (
    ArchiveExtractionPolicy,
    is_safe_archive_member,
    safe_extract_all,
)
from cypy.core.reporting import NullReporter


@dataclass
class FakeMember:
    filename: str
    file_size: int = 0
    compress_size: int = 0


class FakeArchive:
    def __init__(self, names):
        self.names = names
        self.extracted = []

    def infolist(self):
        return [FakeMember(name) for name in self.names]

    def extract(self, member, destination):
        self.extracted.append((member.filename, destination))


def test_archive_member_normal_path_is_safe(tmp_path):
    assert is_safe_archive_member(str(tmp_path), "chapter/page001.png")


def test_archive_member_parent_traversal_is_rejected(tmp_path):
    assert not is_safe_archive_member(str(tmp_path), "../evil.png")


def test_archive_member_absolute_path_is_rejected(tmp_path):
    absolute_path = os.path.abspath(str(tmp_path / "evil.png"))
    assert not is_safe_archive_member(str(tmp_path), absolute_path)


def test_safe_extract_all_rejects_unsafe_member(tmp_path):
    archive = FakeArchive(["ok/page.png", "../evil.png"])

    with pytest.raises(Exception):
        safe_extract_all(archive, str(tmp_path))

    assert archive.extracted == []


def test_safe_extract_all_rejects_archive_bomb_metadata(tmp_path):
    archive = FakeArchive([])
    archive.infolist = lambda: [
        FakeMember("huge.png", file_size=10_000_000, compress_size=1)
    ]

    with pytest.raises(Exception):
        safe_extract_all(
            archive,
            str(tmp_path),
            policy=ArchiveExtractionPolicy(max_member_size=20_000_000),
        )

    assert archive.extracted == []


def test_archive_translation_results_keep_source_order():
    image_paths = ["page1.png", "page2.png", "page3.png"]

    def process(path, index):
        time.sleep(0.01 * (4 - index))
        return f"translated-{path}"

    result = _translate_archive_images(image_paths, process, NullReporter())

    assert result == [
        "translated-page1.png",
        "translated-page2.png",
        "translated-page3.png",
    ]
