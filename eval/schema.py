"""Validate user-authored JSONL without supplying questions or reference answers."""

import hashlib
import json
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class GoldenDataError(ValueError):
    """Describe invalid evaluation input without reflecting its contents."""


class GoldPage(BaseModel):
    """Identify one physical PDF page by its original document SHA-256."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    doc_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    page: int = Field(gt=0)


class GoldenQuestion(BaseModel):
    """Describe answerability and all gold pages, with an optional human reference answer."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    answerable: bool
    gold_pages: list[GoldPage]
    reference_answer: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_labels(self) -> Self:
        """Require pages for answerable rows and no gold pages/answer for negatives."""
        if self.answerable != bool(self.gold_pages):
            raise ValueError("answerability and gold pages disagree")
        if len(set(self.gold_pages)) != len(self.gold_pages):
            raise ValueError("duplicate gold pages")
        if not self.answerable and self.reference_answer is not None:
            raise ValueError("unanswerable rows cannot have reference answers")
        return self


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def load_golden(path: Path, max_query_characters: int) -> tuple[list[GoldenQuestion], str]:
    """Reject empty/malformed/duplicate data and return a digest of the exact input bytes."""
    try:
        raw = path.read_bytes()
        lines = raw.decode("utf-8").splitlines()
    except (OSError, UnicodeError):
        raise GoldenDataError("Cannot read UTF-8 golden data.") from None
    questions: list[GoldenQuestion] = []
    ids: set[str] = set()
    texts: set[str] = set()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            item = GoldenQuestion.model_validate(json.loads(line, object_pairs_hook=_unique_object))
            item.question.encode("utf-8")
            item.id.encode("utf-8")
            if len(item.question) > max_query_characters:
                raise ValueError("oversized query")
            if item.id in ids or item.question in texts:
                raise ValueError("duplicate question or id")
        except (ValueError, ValidationError, RecursionError):
            raise GoldenDataError(f"Invalid golden row at line {number}.") from None
        ids.add(item.id)
        texts.add(item.question)
        questions.append(item)
    if not questions:
        raise GoldenDataError("Golden data is empty. Add your own questions and page labels first.")
    return questions, hashlib.sha256(raw).hexdigest()
