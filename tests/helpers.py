from dataclasses import replace

from cypy.core.settings import ProcessingSettings


def make_settings(tmp_path, **overrides):
    base = ProcessingSettings.from_config()
    defaults = {
        "root_dir": str(tmp_path),
        "assets_dir": str(tmp_path),
        "cache_dir": str(tmp_path / "cache"),
        "font_manga": str(tmp_path / "missing-font.ttf"),
        "font_japanese": str(tmp_path / "missing-japanese.ttf"),
        "manual_translation_override": {},
        "lang_codes": dict(base.lang_codes),
    }
    defaults.update(overrides)
    return replace(base, **defaults)
