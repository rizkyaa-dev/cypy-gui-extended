from cypy.core.imaging.fonts import FONT_CACHE_DIR, FONT_JAPANESE, FontResolver
from cypy.core.reporting import MemoryReporter
from tests.helpers import make_settings


def test_font_resolver_falls_back_without_network_for_non_latin_text(tmp_path):
    settings = make_settings(tmp_path)
    reporter = MemoryReporter()
    resolver = FontResolver(settings, reporter=reporter, http_client=None)

    font = resolver.resolve("日本語", 12, "korean")

    assert hasattr(font, "getbbox")
    assert reporter.messages == [
        (
            "warning",
            "  [!] 'requests' library is not installed. Custom fonts cannot be downloaded automatically.",
        )
    ]


def test_legacy_font_paths_are_lazy_path_like():
    assert FONT_CACHE_DIR.endswith("fonts")
    assert FONT_JAPANESE.endswith("KosugiMaru.ttf")
