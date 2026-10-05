from functools import lru_cache

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from docs_qa.auth.role import Role


class DatabaseSettings(BaseModel):
    url: str = "postgresql+asyncpg://docs_qa:docs_qa@localhost:5432/docs_qa"


class EmbeddingSettings(BaseModel):
    ollama_url: str = "http://localhost:11434"
    model: str = "nomic-embed-text"
    # nomic-embed-text was trained with these task prefixes; without them retrieval is worse.
    document_prefix: str = "search_document: "
    query_prefix: str = "search_query: "
    batch_size: int = 32
    timeout_seconds: float = 60


class OpenAISettings(BaseModel):
    api_key: SecretStr | None = None
    model: str = "gpt-5.4-mini"
    max_output_tokens: int = 2000
    timeout_seconds: float = 60


class ChunkingSettings(BaseModel):
    max_words: int = 300
    overlap_words: int = 45


class RetrievalSettings(BaseModel):
    candidates_per_search: int = 20
    top_k: int = 6
    rrf_k: int = 60
    min_similarity: float = 0.45


class IngestionSettings(BaseModel):
    poll_interval_seconds: float = 1
    lease_seconds: int = 300
    max_attempts: int = 3


class UploadSettings(BaseModel):
    max_file_size_bytes: int = 20 * 1024 * 1024


class AuthSettings(BaseModel):
    api_keys: dict[str, Role] = {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__", env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    database: DatabaseSettings = DatabaseSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    openai: OpenAISettings = OpenAISettings()
    chunking: ChunkingSettings = ChunkingSettings()
    retrieval: RetrievalSettings = RetrievalSettings()
    ingestion: IngestionSettings = IngestionSettings()
    upload: UploadSettings = UploadSettings()
    auth: AuthSettings = AuthSettings()


@lru_cache
def get_settings() -> Settings:
    return Settings()
