"""Summarization helpers."""
from __future__ import annotations

from abc import ABC, abstractmethod
import time
from typing import List



class Summarizer(ABC):
    """Abstract base class for text summarizers."""

    @abstractmethod
    def summarize(self, text: str) -> str:
        """Return a summary of ``text``."""
        raise NotImplementedError


def _chunk_text(text: str, max_chars: int) -> List[str]:
    """Split ``text`` into chunks without breaking words."""
    if len(text) <= max_chars:
        return [text]
    import textwrap

    return textwrap.wrap(
        text,
        max_chars,
        break_long_words=False,
        break_on_hyphens=False,
    )


class OpenAISummarizer(Summarizer):
    """Summarizer that uses OpenAI's Chat Completions API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        *,
        max_chars: int = 4000,
        max_retries: int = 3,
    ) -> None:

        import openai

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.max_chars = max_chars
        self.max_retries = max_retries

    def summarize(self, text: str) -> str:
        chunks = _chunk_text(text, self.max_chars)
        summaries: List[str] = []
        for chunk in chunks:
            for attempt in range(self.max_retries):
                try:
                    completion = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "user",
                                "content": f"Summarize the following text:\n{chunk}",
                            }
                        ],
                    )
                    summaries.append(completion.choices[0].message.content.strip())
                    break
                except Exception:  # pragma: no cover - network errors
                    if attempt == self.max_retries - 1:
                        raise
                    time.sleep(2 ** attempt)
        return "\n\n".join(summaries)


class GeminiSummarizer(Summarizer):
    """Summarizer that uses Google's Gemini API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-pro",
        *,
        max_chars: int = 4000,
        max_retries: int = 3,
    ) -> None:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.max_chars = max_chars
        self.max_retries = max_retries

    def summarize(self, text: str) -> str:
        chunks = _chunk_text(text, self.max_chars)
        summaries: List[str] = []
        for chunk in chunks:
            for attempt in range(self.max_retries):
                try:
                    response = self.model.generate_content(
                        f"Summarize the following text:\n{chunk}"
                    )
                    summaries.append(response.text.strip())
                    break
                except Exception:  # pragma: no cover - network errors
                    if attempt == self.max_retries - 1:
                        raise
                    time.sleep(2 ** attempt)
        return "\n\n".join(summaries)


class DummySummarizer(Summarizer):
    """Fallback summarizer used for testing."""

    def summarize(self, text: str) -> str:  # pragma: no cover - trivial
        return text.splitlines()[0] if text else ""
