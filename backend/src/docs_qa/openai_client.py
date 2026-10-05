from openai import AsyncOpenAI

from docs_qa.settings import OpenAISettings


def create_openai_client(settings: OpenAISettings) -> AsyncOpenAI | None:
    if settings.api_key is None:
        return None
    return AsyncOpenAI(
        api_key=settings.api_key.get_secret_value(), timeout=settings.timeout_seconds
    )
