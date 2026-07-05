import json

import cypy.core.config as config
from cypy.core.documents.common import language_suffix
from cypy.core.settings import ProcessingSettings


def test_language_suffix_known_language():
    assert language_suffix("Indonesian") == "_cypytr_id"


def test_language_suffix_custom_language():
    assert language_suffix("Klingon") == "_cypytr_kl"


def test_language_suffix_empty_language():
    assert language_suffix("") == "_cypytr_tr"


def test_processing_settings_from_config_maps_required_fields():
    settings = ProcessingSettings.from_config()

    assert settings.root_dir
    assert settings.assets_dir
    assert settings.font_manga.endswith("Komika Axis.ttf")
    assert ".png" in settings.supported_image_extensions
    assert settings.lang_codes["indonesian"] == "id"


def test_settings_file_never_persists_api_keys(tmp_path, monkeypatch):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(config, "SETTINGS_FILE", str(settings_path))
    monkeypatch.setattr(config, "GEMINI_API_KEY", "super-secret")

    assert config.save_settings()

    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert not any("api_key" in key for key in payload)
