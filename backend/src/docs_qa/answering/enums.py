from enum import StrEnum


class AnswerOutcome(StrEnum):
    ANSWERED = "ANSWERED"
    NOT_IN_DOCUMENTS = "NOT_IN_DOCUMENTS"
    UNSUPPORTED = "UNSUPPORTED"


class Rating(StrEnum):
    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"
