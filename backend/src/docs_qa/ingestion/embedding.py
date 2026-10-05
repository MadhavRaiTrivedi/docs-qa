from collections.abc import Sequence
from typing import Protocol

from openai import AsyncOpenAI

from docs_qa.settings import EmbeddingSettings


class Embedder(Protocol):
    @property
    def model(self) -> str: ...

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class OpenAIEmbedder:
    def __init__(self, client: AsyncOpenAI, settings: EmbeddingSettings) -> None:
        self._client = client
        self._settings = settings

    @property
    def model(self) -> str:
        return self._settings.model

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        batch_size = self._settings.batch_size
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            embeddings.extend(await self._embed(texts[start : start + batch_size]))
        return embeddings

    async def embed_query(self, text: str) -> list[float]:
        [embedding] = await self._embed([text])
        return embedding

    async def _embed(self, inputs: Sequence[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._settings.model, input=list(inputs)
        )
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
