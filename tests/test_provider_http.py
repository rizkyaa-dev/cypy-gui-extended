from types import SimpleNamespace

import pytest
from PIL import Image

from cypy.core.errors import ProviderRateLimitError
from cypy.core.providers.http import (
    build_chat_completion_endpoint,
    request_chat_completion,
)


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_custom_endpoint_normalization_does_not_duplicate_v1():
    assert build_chat_completion_endpoint("https://api.example.com/v1") == (
        "https://api.example.com/v1/chat/completions"
    )
    assert build_chat_completion_endpoint(
        "https://api.example.com/v1/chat/completions"
    ) == "https://api.example.com/v1/chat/completions"


def test_custom_endpoint_rejects_non_http_urls():
    with pytest.raises(ValueError):
        build_chat_completion_endpoint("file:///tmp/provider")


def test_http_adapter_exposes_retry_after():
    client = SimpleNamespace(
        post=lambda *args, **kwargs: FakeResponse(
            429,
            {"error": {"message": "slow down"}},
            headers={"Retry-After": "3.5"},
        )
    )

    with pytest.raises(ProviderRateLimitError) as error:
        request_chat_completion(
            http_client=client,
            provider_name="Test",
            endpoint="https://api.example.com/v1/chat/completions",
            api_key="key",
            model_name="model",
            image=Image.new("RGB", (2, 2), "white"),
            prompt="translate",
        )

    assert error.value.retry_after == 3.5
