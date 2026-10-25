"""Serialize retrieved passages as bounded data, separate from system instructions."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import files

from app.retrieval.models import SearchHit


@dataclass(frozen=True)
class PromptContext:
    """Retain the exact subset shown to the model for subsequent quote validation."""

    user_prompt: str
    passages: list[SearchHit]


def system_prompt() -> str:
    """Load the versioned evidence/injection policy shipped with the application."""
    return files("app.answering").joinpath("prompts/system.txt").read_text(encoding="utf-8")


def build_context(query: str, hits: Sequence[SearchHit], budget: int) -> PromptContext:
    """Include whole ranked passages while bounding the serialized user-message length."""
    included: list[SearchHit] = []
    records: list[dict[str, object]] = []

    def serialize(passages: list[dict[str, object]]) -> str:
        return json.dumps({"question": query, "passages": passages}, ensure_ascii=False)

    for hit in hits:
        record: dict[str, object] = {
            "number": len(records) + 1,
            "doc_id": hit.doc_id,
            "page": hit.page,
            "text": hit.text,
        }
        if len(serialize([*records, record])) <= budget:
            records.append(record)
            included.append(hit)
    return PromptContext(serialize(records), included)
