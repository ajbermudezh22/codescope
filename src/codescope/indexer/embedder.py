"""bge-small embeddings via fastembed. CPU-only, ~80MB model, 384 dims."""

from __future__ import annotations

from fastembed import TextEmbedding

_MODEL = "BAAI/bge-small-en-v1.5"
_DIM = 384


class Embedder:
    def __init__(self) -> None:
        self._model = TextEmbedding(model_name=_MODEL)

    @property
    def dim(self) -> int:
        return _DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [vec.tolist() for vec in self._model.embed(texts)]
