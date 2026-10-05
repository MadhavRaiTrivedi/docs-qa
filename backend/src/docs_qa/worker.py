import asyncio
import signal

import httpx

from docs_qa.database import create_engine, create_session_factory
from docs_qa.embedding_model_check import ensure_embedding_model_matches
from docs_qa.ingestion.chunking import Chunker
from docs_qa.ingestion.embedding import OllamaEmbedder
from docs_qa.ingestion.ingestion_worker import IngestionWorker
from docs_qa.logging_setup import configure_logging
from docs_qa.settings import get_settings


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database.url)
    session_factory = create_session_factory(engine)
    await ensure_embedding_model_matches(session_factory, settings.embedding.model)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for stop_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(stop_signal, stop.set)

    async with httpx.AsyncClient() as http_client:
        worker = IngestionWorker(
            session_factory,
            OllamaEmbedder(http_client, settings.embedding),
            Chunker(settings.chunking.max_words, settings.chunking.overlap_words),
            settings.ingestion,
        )
        await worker.run(stop)
    await engine.dispose()


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
