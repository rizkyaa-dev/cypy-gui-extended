import requests

from cypy.core.providers.base import LLMProvider
from cypy.core.providers.http import request_chat_completion


class ZenProvider(LLMProvider):
    """
    Zen provider (opencode.ai) — OpenAI-compatible API, no key required.
    Docs: https://opencode.ai/docs/zen/#endpoints
    """

    BASE_URL = "https://opencode.ai/zen/v1/chat/completions"

    @property
    def provider_name(self):
        return "Zen (opencode.ai)"

    def validate_api_key(self):
        """Zen works without an API key — always pass validation."""
        return True

    def translate_image(self, image, prompt):
        return request_chat_completion(
            http_client=requests,
            provider_name=self.provider_name,
            endpoint=self.BASE_URL,
            api_key=self.api_key,
            model_name=self.model_name,
            image=image,
            prompt=prompt,
        )
