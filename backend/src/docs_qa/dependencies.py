"""Builds request-scoped services from what the app created at startup."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from docs_qa.answering.answer_generator import AnswerGenerator
from docs_qa.answering.errors import LlmNotConfiguredError
from docs_qa.answering.question_answerer import QuestionAnswerer
from docs_qa.answering.question_service import QuestionService
from docs_qa.database import get_session
from docs_qa.ingestion.embedding import Embedder
from docs_qa.library.collection_service import CollectionService
from docs_qa.library.document_service import DocumentService
from docs_qa.search.hybrid_retriever import HybridRetriever
from docs_qa.settings import Settings

Session = Annotated[AsyncSession, Depends(get_session)]


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_embedder(request: Request) -> Embedder:
    embedder: Embedder = request.app.state.embedder
    return embedder


def get_answer_generator(request: Request) -> AnswerGenerator:
    generator: AnswerGenerator | None = request.app.state.answer_generator
    if generator is None:
        raise LlmNotConfiguredError()
    return generator


AppSettings = Annotated[Settings, Depends(get_app_settings)]


def get_collection_service(session: Session) -> CollectionService:
    return CollectionService(session)


def get_document_service(session: Session) -> DocumentService:
    return DocumentService(session)


def get_question_service(session: Session) -> QuestionService:
    return QuestionService(session)


def get_retriever(
    session: Session,
    embedder: Annotated[Embedder, Depends(get_embedder)],
    settings: AppSettings,
) -> HybridRetriever:
    return HybridRetriever(session, embedder, settings.retrieval)


def get_question_answerer(
    session: Session,
    retriever: Annotated[HybridRetriever, Depends(get_retriever)],
    generator: Annotated[AnswerGenerator, Depends(get_answer_generator)],
    settings: AppSettings,
) -> QuestionAnswerer:
    return QuestionAnswerer(session, retriever, generator, settings.retrieval)
