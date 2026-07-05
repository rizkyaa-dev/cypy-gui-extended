from cypy.core.providers.base import LLMProvider
from cypy.core.providers.http import request_chat_completion

try:
    import requests
except ImportError:
    requests = None


class OpenAIProvider(LLMProvider):
    """
    OpenAI provider using the REST API directly.
    Supports GPT-5.4, GPT-5.4-mini, and other vision-capable models.
    Uses only `requests` — no extra SDK needed~ ♪

    Get your API key at: https://platform.openai.com/api-keys
    """

    BASE_URL = "https://api.openai.com/v1/chat/completions"

    @property
    def provider_name(self):
        return "OpenAI"

    def translate_image(self, image, prompt):
        if requests is None:
            raise ImportError(
                "requests package is not installed. "
                "Install it with: pip install requests"
            )
        return request_chat_completion(
            http_client=requests,
            provider_name=self.provider_name,
            endpoint=self.BASE_URL,
            api_key=self.api_key,
            model_name=self.model_name,
            image=image,
            prompt=prompt,
            response_format={"type": "json_object"},
        )
