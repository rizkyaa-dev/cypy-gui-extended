import concurrent.futures
import threading
import time

import pytest

from cypy.core.errors import ProviderRateLimitError
from cypy.core.translation.service import MosaicTranslationService, ProviderCallGuard, RetryPolicy


class FakeProvider:
    provider_name = "fake"
    model_name = "fake-model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    def validate_api_key(self):
        return True

    def translate_image(self, image, prompt):
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)

        time.sleep(0.01)

        with self.lock:
            self.active -= 1
            self.calls += 1

        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_retry_policy_uses_injected_sleeper_for_generic_retry():
    provider = FakeProvider([RuntimeError("temporary"), '{"1": "ok"}'])
    delays = []
    service = MosaicTranslationService(
        retry_policy=RetryPolicy(max_retry=2, generic_retry_delay=0.25),
        sleeper=delays.append,
    )

    assert service.translate(None, provider) == {"1": "ok"}
    assert delays == [0.25]


def test_rate_limit_raises_domain_error_after_retries():
    provider = FakeProvider([RuntimeError("429"), RuntimeError("429")])
    service = MosaicTranslationService(
        retry_policy=RetryPolicy(max_retry=2, rate_limit_base_delay=0.5),
        sleeper=lambda delay: None,
    )

    with pytest.raises(ProviderRateLimitError):
        service.translate(None, provider)


def test_rate_limit_honors_provider_retry_after():
    provider = FakeProvider(
        [ProviderRateLimitError("429", retry_after=1.75), '{"1": "ok"}']
    )
    delays = []
    service = MosaicTranslationService(
        retry_policy=RetryPolicy(max_retry=2),
        sleeper=delays.append,
    )

    assert service.translate(None, provider) == {"1": "ok"}
    assert delays == [1.75]


def test_provider_call_guard_serializes_shared_provider_calls():
    provider = FakeProvider(['{"1": "ok"}', '{"1": "ok"}', '{"1": "ok"}'])
    service = MosaicTranslationService(
        provider_guard=ProviderCallGuard(threading.Lock()),
        sleeper=lambda delay: None,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(lambda _: service.translate(None, provider), range(3)))

    assert results == [{"1": "ok"}, {"1": "ok"}, {"1": "ok"}]
    assert provider.max_active == 1
