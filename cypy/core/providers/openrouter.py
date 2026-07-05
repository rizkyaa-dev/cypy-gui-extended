from cypy.core.providers.base import LLMProvider
from cypy.core.providers.http import request_chat_completion

try:
    import requests
except ImportError:
    requests = None


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter provider using the OpenAI-compatible REST API.
    Supports hundreds of models including Claude, Llama, Mistral, Gemini, etc.
    Uses only `requests` — no extra SDK needed~ ♪

    Get your API key at: https://openrouter.ai/keys
    Browse models at: https://openrouter.ai/models
    """

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    @property
    def provider_name(self):
        return "OpenRouter"

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
            extra_headers={
                "HTTP-Referer": "https://github.com/rizkyaa-dev/cypy-extended",
                "X-Title": "cypy-extended Manga Translator",
            },
        )
