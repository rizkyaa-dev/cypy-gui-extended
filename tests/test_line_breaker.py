from PIL import Image, ImageDraw

from cypy.core.imaging.text_layout import cari_layout_teks_optimal
from cypy.core.settings import ProcessingSettings
from cypy.core.translation.prompt import MangaPromptBuilder


LAYOUT_SETTINGS = {
    "min_font": 6,
    "max_font": 50,
    "spacing_ratio": 0.06,
}


def _fit(text):
    draw = ImageDraw.Draw(Image.new("RGB", (500, 500), "white"))
    return cari_layout_teks_optimal(
        draw,
        text,
        "Indonesian",
        ProcessingSettings.from_config(),
        LAYOUT_SETTINGS,
        max_w=75,
        max_h=180,
    )


def test_long_indonesian_word_uses_readable_syllable_break():
    result = _fit("AKU MENINGGALKANKU SENDIRIAN")

    assert result.font_size >= 10
    assert result.hyphenated is True
    assert "MENING-\nGALKANKU" in result.wrapped_text


def test_short_word_is_never_force_split():
    result = _fit("BOLEH")

    assert result.hyphenated is False
    assert result.wrapped_text == "BOLEH"


def test_translation_prompt_requests_compact_bubble_wording():
    prompt = MangaPromptBuilder().build("Indonesian")

    assert "shortest natural wording" in prompt
    assert "fits the original bubble" in prompt
