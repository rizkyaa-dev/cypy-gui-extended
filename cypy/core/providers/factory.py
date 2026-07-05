from cypy.core.providers.custom import CustomProvider
from cypy.core.providers.gemini import GeminiProvider
from cypy.core.providers.openai_provider import OpenAIProvider
from cypy.core.providers.openrouter import OpenRouterProvider
from cypy.core.providers.zen import ZenProvider


PROVIDER_MAP = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "zen": ZenProvider,
    "openrouter": OpenRouterProvider,
    "custom": CustomProvider,
}


def create_provider(provider_name, api_key, model_name, **kwargs):
    provider_key = (provider_name or "").lower()
    cls = PROVIDER_MAP.get(provider_key)
    if cls is None:
        raise ValueError(f"Unknown provider: {provider_name}")
    return cls(api_key=api_key, model_name=model_name, **kwargs)
