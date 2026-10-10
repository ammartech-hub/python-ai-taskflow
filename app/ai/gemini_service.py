"""Gemini AI Service integration for automated task description generation.

Utilizes the official Google Gen AI Python SDK with robust error handling,
resilience against missing API configurations, rate limit translation, and
timeout protection without leaking credentials.
"""

import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class AIServiceException(Exception):
    """Base exception for all AI service operations."""
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AIServiceNotConfiguredError(AIServiceException):
    """Raised when GEMINI_API_KEY is not configured in the environment."""
    def __init__(self, message: str = "AI service is not configured. Please set GEMINI_API_KEY in the environment."):
        super().__init__(message=message, status_code=503)


class AIRateLimitError(AIServiceException):
    """Raised when Gemini API rate limit or quota is exhausted."""
    def __init__(self, message: str = "AI provider rate limit reached. Please retry after a brief pause."):
        super().__init__(message=message, status_code=429)


class AIServiceUnavailableError(AIServiceException):
    """Raised when the AI provider is unreachable, times out, or returns 503."""
    def __init__(self, message: str = "AI provider is temporarily unavailable. Please retry later."):
        super().__init__(message=message, status_code=503)


class AIProviderError(AIServiceException):
    """Raised when the AI provider returns an unexpected error."""
    def __init__(self, message: str = "Failed to generate description from AI provider."):
        super().__init__(message=message, status_code=502)


class GeminiService:
    """Service class for coordinating Gemini AI operations."""

    SYSTEM_INSTRUCTION = (
        "You are an expert technical project manager and task assistant. "
        "Given a task title, write a concise, actionable, and professional task description. "
        "The description should detail clear objectives, necessary steps, and expected deliverables. "
        "Keep it within 2 to 4 sentences or a compact structured paragraph without fluff or preamble."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-2.5-flash"

    def is_configured(self) -> bool:
        """Check whether a non-empty API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    def generate_task_description(self, title: str) -> str:
        """Generate a professional task description based on a given title.

        Args:
            title: Validated task title string.

        Returns:
            String containing the AI-generated task description.

        Raises:
            AIServiceNotConfiguredError: If GEMINI_API_KEY is missing.
            AIRateLimitError: If provider quota is exceeded.
            AIServiceUnavailableError: If provider is unreachable or times out.
            AIProviderError: On other provider or response errors.
        """
        if not self.is_configured():
            logger.warning("Attempted AI generation without configured GEMINI_API_KEY")
            raise AIServiceNotConfiguredError()

        clean_title = title.strip()
        prompt = (
            f"Generate a clear, professional task description for this task title:\n\n"
            f"\"{clean_title}\"\n\n"
            f"Description:"
        )

        # Attempt invocation using official google-genai SDK first
        try:
            return self._call_google_genai(clean_title, prompt)
        except AIServiceException:
            raise
        except Exception as exc:
            # Check if google-genai is not available and try google.generativeai fallback
            exc_str = str(exc).lower()
            if "no module named 'google.genai'" in exc_str or "cannot import name" in exc_str:
                try:
                    return self._call_legacy_generativeai(prompt)
                except AIServiceException:
                    raise
                except Exception as legacy_exc:
                    self._handle_api_error(legacy_exc)

            self._handle_api_error(exc)

    def _call_google_genai(self, title: str, prompt: str) -> str:
        """Execute request using modern google-genai SDK."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=self.SYSTEM_INSTRUCTION,
                temperature=0.7,
                max_output_tokens=400,
            ),
        )

        text = getattr(response, "text", None)
        if not text and hasattr(response, "candidates") and response.candidates:
            cand = response.candidates[0]
            if hasattr(cand, "content") and cand.content.parts:
                text = cand.content.parts[0].text

        if not text or not text.strip():
            raise AIProviderError("AI provider returned an empty or filtered response.")

        return text.strip()

    def _call_legacy_generativeai(self, prompt: str) -> str:
        """Fallback execution using google.generativeai SDK."""
        import google.generativeai as genai_legacy

        genai_legacy.configure(api_key=self.api_key)
        model = genai_legacy.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.SYSTEM_INSTRUCTION,
        )
        response = model.generate_content(prompt)
        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise AIProviderError("AI provider returned an empty response.")
        return text.strip()

    def _handle_api_error(self, exc: Exception) -> None:
        """Classify exceptions without leaking API keys or internal stack traces."""
        msg = str(exc)
        msg_lower = msg.lower()
        logger.error("Gemini AI API failure: %s", type(exc).__name__)

        if any(term in msg_lower for term in ["429", "resource_exhausted", "quota", "rate limit"]):
            raise AIRateLimitError()
        elif any(term in msg_lower for term in ["timeout", "timed out", "503", "unavailable", "deadline"]):
            raise AIServiceUnavailableError()
        elif any(term in msg_lower for term in ["not found", "model", "unsupported"]):
            raise AIProviderError(f"Requested AI model '{self.model_name}' is unavailable or unsupported.")
        elif any(term in msg_lower for term in ["401", "api_key", "unauthenticated", "invalid api key"]):
            raise AIProviderError("Authentication with AI provider failed. Please verify GEMINI_API_KEY.")
        else:
            raise AIProviderError()


# Singleton instance for route injection
gemini_service = GeminiService()
