class LlmNotConfiguredError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "Answer generation needs an OpenAI API key. Set OPENAI_API_KEY and restart the API. "
            "Search works without it."
        )


class AnswerGenerationError(Exception):
    pass
