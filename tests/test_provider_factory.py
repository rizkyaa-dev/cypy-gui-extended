import pytest

from cypy.core.providers.factory import create_provider


def test_create_provider_valid_provider():
    provider = create_provider("zen", api_key="", model_name="model")
    assert provider.provider_name == "Zen (opencode.ai)"


def test_create_provider_invalid_provider():
    with pytest.raises(ValueError):
        create_provider("missing", api_key="", model_name="model")
