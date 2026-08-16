from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

EMBEDDING_DIMENSIONS = 384


class EmbeddingProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed(self, text: str) -> list[float]: ...


class FeatureHashEmbeddingProvider:
    """Deterministic offline embedder for development and adapter contract tests."""

    @property
    def name(self) -> str:
        return "local-feature-hash-v1"

    @property
    def dimensions(self) -> int:
        return EMBEDDING_DIMENSIONS

    async def embed(self, text: str) -> list[float]:
        normalized = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        tokens = [token for token in normalized.split() if token]
        features = tokens + [
            token[index : index + 3] for token in tokens for index in range(max(0, len(token) - 2))
        ]
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
            number = int.from_bytes(digest)
            vector[number % self.dimensions] += 1.0 if number & 1 else -1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [value / magnitude for value in vector] if magnitude else vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))
