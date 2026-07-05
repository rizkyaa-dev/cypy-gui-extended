import requests

from cypy.core.providers.base import LLMProvider
from cypy.core.providers.http import (
    build_chat_completion_endpoint,
    request_chat_completion,
)


class CustomProvider(LLMProvider):
    """
    Custom OpenAI-compatible provider with configurable base URL.
    Uses the same /v1/chat/completions format as OpenAI.
    """

    def __init__(self, api_key, model_name, base_url=""):
        super().__init__(api_key, model_name)
        self._base_url = (base_url or "").rstrip("/")

    @property
    def provider_name(self):
        return "Custom"

    def validate_api_key(self):
        """Key is optional — some local providers don't need one."""
        return True

    @property
    def base_url(self):
        return self._base_url or "Not set"

    def translate_image(self, image, prompt):
        if not self._base_url:
            raise RuntimeError("Custom provider base URL is not configured.")

        return request_chat_completion(
            http_client=requests,
            provider_name=self.provider_name,
            endpoint=build_chat_completion_endpoint(self._base_url),
            api_key=self.api_key,
            model_name=self.model_name,
            image=image,
            prompt=prompt,
        )
