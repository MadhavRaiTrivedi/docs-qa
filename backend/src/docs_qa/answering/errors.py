class OpenAINotConfiguredError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "Search and answers need an OpenAI API key. Set OPENAI_API_KEY and restart. "
            "Uploads are kept and ingested once the key is set."
        )


class AnswerGenerationError(Exception):
    pass
