class CypyError(Exception):
    """Base exception for expected cypy domain failures."""


class ProviderAuthError(CypyError):
    """Raised when a provider rejects or is missing credentials."""


class ProviderRateLimitError(CypyError):
    """Raised when a provider reports rate limiting."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class ProviderRequestError(CypyError):
    """Raised when a provider request or response fails."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class TranslationResponseError(CypyError):
    """Raised when a provider response cannot be parsed safely."""


class ArchiveSafetyError(CypyError):
    """Raised when an archive contains unsafe paths."""
