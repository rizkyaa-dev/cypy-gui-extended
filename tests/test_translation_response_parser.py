import pytest

from cypy.core.errors import TranslationResponseError
from cypy.core.translation.service import MosaicTranslationService


def test_parse_response_valid_json():
    assert MosaicTranslationService._parse_response('{"1": "Hello"}') == {"1": "Hello"}


def test_parse_response_fenced_json():
    raw = '```json\n{"1": "Hello", "2": "SKIP"}\n```'
    assert MosaicTranslationService._parse_response(raw) == {"1": "Hello", "2": "SKIP"}


def test_parse_response_normalizes_non_string_values():
    assert MosaicTranslationService._parse_response('{"1": 10, "2": true}') == {
        "1": "10",
        "2": "True",
    }


def test_parse_response_rejects_invalid_json():
    with pytest.raises(TranslationResponseError):
        MosaicTranslationService._parse_response("{not-json}")


def test_parse_response_rejects_non_object_json():
    with pytest.raises(TranslationResponseError):
        MosaicTranslationService._parse_response('["not", "object"]')
