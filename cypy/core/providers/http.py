import base64
import io
from urllib.parse import urlsplit

from cypy.core.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderRequestError,
)


def build_chat_completion_endpoint(base_url):
    value = str(base_url or "").strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Provider base URL must be an absolute HTTP(S) URL.")

    if value.endswith("/chat/completions"):
        return value
    if value.endswith("/v1"):
        return value + "/chat/completions"
    return value + "/v1/chat/completions"


def request_chat_completion(
    *,
    http_client,
    provider_name,
    endpoint,
    api_key,
    model_name,
    image,
    prompt,
    extra_headers=None,
    response_format=None,
    timeout=120,
):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    headers.update(extra_headers or {})

    payload = {
        "model": model_name,
        "temperature": 0,
        "top_p": 0.1,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": _png_data_uri(image)}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    if response_format is not None:
        payload["response_format"] = response_format

    response = http_client.post(
        endpoint,
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    _raise_for_status(provider_name, response)

    try:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderRequestError(
            f"Unexpected {provider_name} response format: {exc}"
        ) from exc

    if not isinstance(content, str):
        raise ProviderRequestError(
            f"Unexpected {provider_name} response content type: {type(content).__name__}"
        )
    return content


def _png_data_uri(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    encoded = base64.b64encode(buffered.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _raise_for_status(provider_name, response):
    status = int(response.status_code)
    if status == 200:
        return

    detail = _error_detail(response)
    message = f"{provider_name} API error {status}: {detail}".rstrip()
    if status in {401, 403}:
        raise ProviderAuthError(message)
    if status == 429:
        raise ProviderRateLimitError(
            message,
            retry_after=_retry_after_seconds(response),
        )
    raise ProviderRequestError(message, status_code=status)


def _error_detail(response):
    try:
        payload = response.json()
        detail = payload.get("error", {}).get("message", "")
        if detail:
            return str(detail)[:500]
    except (AttributeError, TypeError, ValueError):
        pass
    return str(getattr(response, "text", ""))[:500]


def _retry_after_seconds(response):
    try:
        value = response.headers.get("Retry-After")
        return max(0.0, float(value)) if value is not None else None
    except (AttributeError, TypeError, ValueError):
        return None
