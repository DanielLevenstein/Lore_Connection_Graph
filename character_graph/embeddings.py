from __future__ import annotations

import hashlib
import math
import re

from .schema import EmbeddingRecord


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9']+")


class HashingEmbedder:
    """Small deterministic embedding fallback for offline MVP retrieval."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            return vector
        return [value / norm for value in vector]


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def build_embedding_record(node_id: str, embedding_text: str, embedder: HashingEmbedder | None = None) -> EmbeddingRecord:
    embedder = embedder or HashingEmbedder()
    return EmbeddingRecord(
        node_id=node_id,
        embedding_text=embedding_text,
        embedding_ref=f"local_hash:{node_id}",
        vector=embedder.embed(embedding_text),
    )
