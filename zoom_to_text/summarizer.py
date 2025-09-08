"""Summarization helpers."""
from __future__ import annotations

from abc import ABC, abstractmethod


class Summarizer(ABC):
    """Abstract base class for text summarizers."""

    @abstractmethod
    def summarize(self, text: str) -> str:
        """Return a summary of ``text``."""
        raise NotImplementedError


class OpenAISummarizer(Summarizer):
    """Summarizer that uses OpenAI's Chat Completions API."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo") -> None:
        import openai

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def summarize(self, text: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": f"Summarize the following text:\n{text}"}],
        )
        return completion.choices[0].message.content.strip()


class DummySummarizer(Summarizer):
    """Fallback summarizer used for testing."""

    def summarize(self, text: str) -> str:  # pragma: no cover - trivial
        return text.splitlines()[0] if text else ""
