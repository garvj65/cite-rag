"""Validate user-authored golden JSONL; optionally check pages against the active index."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from app.db.repository import create_db_engine
from app.ingestion.service import indexing_profile
from app.settings import Settings
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from eval.runtime import inspect_index
from eval.schema import GoldenDataError, GoldenQuestion, load_golden


def main(argv: Sequence[str] | None = None) -> int:
    """Check schema/labels locally without model calls, or export the JSON schema."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path("eval/golden.jsonl"))
    parser.add_argument("--check-index", action="store_true")
    parser.add_argument("--schema", action="store_true", help="Print the JSON schema and exit")
    args = parser.parse_args(argv)
    if args.schema:
        print(json.dumps(GoldenQuestion.model_json_schema(), indent=2))
        return 0
    try:
        settings = Settings()
        questions, digest = load_golden(args.path, settings.max_query_characters)
        if args.check_index:
            engine = create_db_engine(settings)
            try:
                inspect_index(engine, indexing_profile(settings), questions)
            finally:
                engine.dispose()
    except (GoldenDataError, ValidationError):
        print(
            "Invalid or empty golden data/settings. Check the schema, page labels, unique IDs, "
            "query length, and matching index when requested.",
            file=sys.stderr,
        )
        return 2
    except SQLAlchemyError:
        print("Database unavailable; check configuration and migrations.", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "questions": len(questions),
                "answerable": sum(q.answerable for q in questions),
                "unanswerable": sum(not q.answerable for q in questions),
                "golden_sha256": digest,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
