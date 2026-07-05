from cypy.core.providers.base import LLMProvider

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None


class GeminiProvider(LLMProvider):
    """
    Google Gemini provider using the google-genai SDK.
    Extracted from the original utils.py implementation~ ♪
    """

    @property
    def provider_name(self):
        return "Google Gemini"

    def translate_image(self, image, prompt):
        if genai is None:
            raise ImportError(
                "google-genai package is not installed. "
                "Install it with: pip install google-genai"
            )

        client = genai.Client(api_key=self.api_key)
        config = (
            types.GenerateContentConfig(
                temperature=0,
                top_p=0.1,
                top_k=1,
                response_mime_type="application/json",
            )
            if types is not None
            else {
                "temperature": 0,
                "top_p": 0.1,
                "top_k": 1,
                "response_mime_type": "application/json",
            }
        )
        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=[image, prompt],
                config=config,
            )
            return response.text
        except Exception as exc:
            self._check_api_key_error(exc)
            raise

    @staticmethod
    def _check_api_key_error(err):
        """Check if an error is related to API key issues and raise ValueError if so."""
        err_str = str(err).lower()
        if any(keyword in err_str for keyword in [
            "api key expired", "api_key_invalid", "api key", "api_key"
        ]):
            raise ValueError("API_KEY_ERROR")
