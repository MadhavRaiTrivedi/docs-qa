from collections.abc import Sequence
from typing import Protocol

import httpx

from docs_qa.settings import EmbeddingSettings


class Embedder(Protocol):
    @property
    def model(self) -> str: ...

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class OllamaEmbedder:
    def __init__(self, client: httpx.AsyncClient, settings: EmbeddingSettings) -> None:
        self._client = client
        self._settings = settings

    @property
    def model(self) -> str:
        return self._settings.model

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        prefixed = [self._settings.document_prefix + text for text in texts]
        batch_size = self._settings.batch_size
        embeddings: list[list[float]] = []
        for start in range(0, len(prefixed), batch_size):
            embeddings.extend(await self._embed(prefixed[start : start + batch_size]))
        return embeddings

    async def embed_query(self, text: str) -> list[float]:
        [embedding] = await self._embed([self._settings.query_prefix + text])
        return embedding

    async def _embed(self, inputs: list[str]) -> list[list[float]]:
        response = await self._client.post(
            f"{self._settings.ollama_url}/api/embed",
            json={"model": self._settings.model, "input": inputs},
            timeout=self._settings.timeout_seconds,
        )
        response.raise_for_status()
        embeddings: list[list[float]] = response.json()["embeddings"]
        return embeddings
