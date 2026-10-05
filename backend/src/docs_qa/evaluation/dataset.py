from pathlib import Path

from pydantic import BaseModel


class EvaluationCase(BaseModel):
    question: str
    expected_document: str
    expected_passage: str


def load_cases(path: Path) -> list[EvaluationCase]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [EvaluationCase.model_validate_json(line) for line in lines if line.strip()]
