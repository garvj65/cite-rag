"""Deterministic test doubles; never selected automatically in the application."""

import hashlib
import math
import re
from collections import deque
from collections.abc import Sequence

from app.errors import ProviderError
from app.settings import EMBEDDING_DIMENSIONS


class HashEmbeddingProvider:
    """Hash case-folded word counts into a normalized vector for offline tests."""

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions

    @property
    def model_id(self) -> str:
        """Identify this fake so its vectors cannot be mixed with real embeddings."""
        return "fake/hash-word-count-v1"

    @property
    def dimensions(self) -> int:
        """Return the configured vector dimension."""
        return self._dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return repeatable lexical vectors independent of Python's hash seed."""
        result: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            words = re.findall(r"\w+", text.casefold()) or ["<empty>"]
            for word in words:
                index = int.from_bytes(hashlib.sha256(word.encode()).digest()[:8])
                vector[index % self.dimensions] += 1.0
            norm = math.sqrt(sum(value * value for value in vector))
            result.append([value / norm for value in vector])
        return result


class ScriptedLLMProvider:
    """Return responses or exceptions from a finite script without any network."""

    def __init__(self, responses: Sequence[str | ProviderError]) -> None:
        self._responses = deque(responses)
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Consume one scripted response and record the supplied prompts."""
        self.calls.append((system_prompt, user_prompt))
        if not self._responses:
            raise ProviderError("script_exhausted")
        response = self._responses.popleft()
        if isinstance(response, ProviderError):
            raise response
        return response
