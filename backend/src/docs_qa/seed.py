"""Uploads every file in a folder to a collection, creating the collection if needed."""

import argparse
import asyncio
from pathlib import Path

from docs_qa.database import create_engine, create_session_factory
from docs_qa.library.collection_service import CollectionService
from docs_qa.library.document_service import DocumentService
from docs_qa.settings import get_settings


async def seed(files: list[Path], collection_name: str) -> None:
    engine = create_engine(get_settings().database.url)
    async with create_session_factory(engine)() as session:
        collections = CollectionService(session)
        collection = await collections.find_by_name(collection_name)
        if collection is None:
            collection = await collections.create(collection_name)

        documents = DocumentService(session)
        for path in files:
            outcome = await documents.upload(collection.id, path.name, path.read_bytes())
            state = "already present" if outcome.is_duplicate else "queued for ingestion"
            print(f"{path.name}: {state}")
    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--collection", required=True)
    arguments = parser.parse_args()
    files = sorted(path for path in arguments.folder.iterdir() if path.is_file())
    asyncio.run(seed(files, arguments.collection))


if __name__ == "__main__":
    main()
