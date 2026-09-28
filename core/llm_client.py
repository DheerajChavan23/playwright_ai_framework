"""Resilient Google Gemini LLM Client with fast fallback across models."""

import time
from typing import List, Optional
from google import genai
from google.genai import errors, types
from config.settings import settings

FALLBACK_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
]


class LLMClient:
    """Manages robust communication with Google Gemini API with automated fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.default_model = default_model or settings.gemini_model or "gemini-3.7-flash"
        self._client: Optional[genai.Client] = None


    @property
    def client(self) -> genai.Client:
        """Lazy initialization of GenAI Client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your .env file or environment variables."
                )
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generate content from Gemini with fallback model succession on demand spikes.

        Args:
            prompt: Text prompt for Gemini.
            model: Specific model name to try first.
            temperature: Sampling temperature.

        Returns:
            Generated text content.
        """
        primary_model = model or self.default_model
        candidate_models: List[str] = [primary_model]
        for m in FALLBACK_MODELS:
            if m not in candidate_models:
                candidate_models.append(m)

        config = types.GenerateContentConfig(
            temperature=temperature,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        last_error: Optional[Exception] = None

        for candidate in candidate_models:
            try:
                response = self.client.models.generate_content(
                    model=candidate,
                    contents=prompt,
                    config=config,
                )
                if response and response.text:
                    return response.text
            except (errors.ServerError, errors.APIError) as e:
                last_error = e
                # Try next fallback model immediately if server is unavailable or model not found
                continue
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise last_error
        raise RuntimeError("Failed to generate response from Gemini across all candidate models.")
