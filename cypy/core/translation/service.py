import json
import time
from dataclasses import dataclass

from cypy.core.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    TranslationResponseError,
)
from cypy.core.translation.prompt import MangaPromptBuilder
from cypy.core.translation.response_parser import bersihkan_json_dari_gemini


@dataclass(frozen=True)
class RetryPolicy:
    max_retry: int = 3
    rate_limit_base_delay: float = 5
    generic_retry_delay: float = 10

    def __post_init__(self):
        object.__setattr__(self, "max_retry", max(1, int(self.max_retry)))

    def can_retry(self, attempt):
        return attempt < self.max_retry - 1

    def rate_limit_delay(self, attempt):
        return self.rate_limit_base_delay * (2 ** attempt)

    def generic_delay(self, attempt):
        return self.generic_retry_delay


class ProviderCallGuard:
    def __init__(self, lock=None):
        self.lock = lock

    def call(self, provider, image, prompt):
        if self.lock is None:
            return provider.translate_image(image, prompt)

        with self.lock:
            return provider.translate_image(image, prompt)


class MosaicTranslationService:
    """Coordinates provider calls, retries, and response validation."""

    def __init__(
        self,
        prompt_builder=None,
        max_retry=3,
        retry_policy=None,
        sleeper=None,
        provider_guard=None,
    ):
        self.prompt_builder = prompt_builder or MangaPromptBuilder()
        self.retry_policy = retry_policy or RetryPolicy(max_retry=max_retry)
        self.max_retry = self.retry_policy.max_retry
        self.sleeper = sleeper or time.sleep
        self.provider_guard = provider_guard or ProviderCallGuard()

    def translate(self, image, provider, target_language="Indonesian"):
        if not provider.validate_api_key():
            raise ProviderAuthError(
                f"API key for {provider.provider_name} is missing or empty."
            )

        prompt = self.prompt_builder.build(target_language)

        for attempt in range(self.retry_policy.max_retry):
            try:
                raw_response = self.provider_guard.call(provider, image, prompt)
                return self._parse_response(raw_response)
            except ProviderAuthError:
                raise
            except ProviderRateLimitError as exc:
                if self.retry_policy.can_retry(attempt):
                    delay = (
                        exc.retry_after
                        if exc.retry_after is not None
                        else self.retry_policy.rate_limit_delay(attempt)
                    )
                    self.sleeper(delay)
                    continue
                raise
            except ValueError as exc:
                if str(exc) == "API_KEY_ERROR":
                    raise ProviderAuthError(
                        f"API key for {provider.provider_name} is expired or invalid."
                    )
                raise
            except Exception as exc:
                if self._is_auth_error(exc):
                    raise ProviderAuthError(
                        f"API key for {provider.provider_name} is expired or invalid."
                    )

                if self._is_rate_limit(exc):
                    if self.retry_policy.can_retry(attempt):
                        self.sleeper(self.retry_policy.rate_limit_delay(attempt))
                        continue
                    raise ProviderRateLimitError(str(exc))

                if self.retry_policy.can_retry(attempt):
                    self.sleeper(self.retry_policy.generic_delay(attempt))
                    continue

                raise

        return {}

    @staticmethod
    def _is_auth_error(exc):
        err = str(exc).lower()
        return any(
            token in err
            for token in ("api key expired", "api_key_invalid", "api key", "api_key")
        )

    @staticmethod
    def _is_rate_limit(exc):
        err = str(exc).lower()
        return any(
            token in err for token in ("429", "too many requests", "rate limit")
        )

    @staticmethod
    def _parse_response(raw_response):
        if not isinstance(raw_response, str) or not raw_response.strip():
            raise TranslationResponseError("Provider returned an empty response.")

        cleaned = bersihkan_json_dari_gemini(raw_response)

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise TranslationResponseError(f"Invalid JSON response: {exc}") from exc

        if not isinstance(payload, dict):
            raise TranslationResponseError("Translation response must be a JSON object.")

        return MosaicTranslationService._normalize_payload(payload)

    @staticmethod
    def _normalize_payload(payload):
        normalized = {}

        for raw_key, raw_value in payload.items():
            key = str(raw_key).strip()
            if not key or raw_value is None:
                continue

            if isinstance(raw_value, str):
                value = raw_value.strip()
            elif isinstance(raw_value, (int, float, bool)):
                value = str(raw_value)
            else:
                value = json.dumps(raw_value, ensure_ascii=False).strip()

            if value:
                normalized[key] = value

        return normalized
