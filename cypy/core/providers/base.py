from abc import ABC, abstractmethod
from PIL import Image


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    Each provider must implement translate_image() to handle
    sending a manga mosaic image + prompt and returning the raw JSON text~ ♪
    """

    def __init__(self, api_key, model_name):
        self.api_key = api_key
        self.model_name = model_name

    @property
    @abstractmethod
    def provider_name(self):
        """Human-readable name for display purposes."""
        ...

    @abstractmethod
    def translate_image(self, image, prompt):
        """
        Send a PIL Image + prompt to the LLM and return the raw response text.

        Args:
            image (PIL.Image.Image): The mosaic image with numbered bubbles.
            prompt (str): The translation prompt.

        Returns:
            str: The raw text response from the LLM (should be JSON).

        Raises:
            ValueError("API_KEY_ERROR"): If the API key is invalid or expired.
            Exception: For other API errors.
        """
        ...

    def validate_api_key(self):
        """Check if the API key looks valid (non-empty). Override for deeper checks."""
        return bool(self.api_key and self.api_key.strip())

    def __repr__(self):
        return f"{self.provider_name} (model={self.model_name})"
