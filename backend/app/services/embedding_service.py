import hashlib
import math
import re

from app.core.config import settings


class EmbeddingService:
    """Small deterministic embedding provider for local MVP development.

    This is not a semantic embedding model. It gives the backend a stable vector
    path for ingestion/search until an OpenAI or local model provider is added.
    """

    def __init__(self, dimensions: int | None = None) -> None:
        self.dimensions = dimensions or settings.embedding_dimensions

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = self._tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]

    def has_signal(self, embedding: list[float]) -> bool:
        return any(value != 0.0 for value in embedding)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[A-Za-z0-9_가-힣]+", text.lower())

