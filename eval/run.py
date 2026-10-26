"""Explicit evaluation entry point; no questions or gold answers are generated."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from app.settings import Settings
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from eval.models import EvaluationOptions
from eval.report import write_report
from eval.runtime import run_evaluation
from eval.schema import GoldenDataError, load_golden


def main(argv: Sequence[str] | None = None) -> int:
    """Evaluate one strategy and persist even partial results with explicit failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", choices=("vector", "keyword", "hybrid"), default="hybrid")
    parser.add_argument("--k", type=int, default=EvaluationOptions().k)
    parser.add_argument("--seed", type=int, default=EvaluationOptions().seed)
    parser.add_argument(
        "--retrieval-only", action="store_true", help="Measure ranking only; never call the LLM"
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0,
        help="Pause between questions; excluded from latency",
    )
    parser.add_argument("--golden", type=Path, default=Path("eval/golden.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("eval/results"))
    parser.add_argument(
        "--fake", action="store_true", help="Explicit mechanics-only fake providers"
    )
    args = parser.parse_args(argv)
    try:
        settings = Settings()
        if args.fake:
            settings = settings.model_copy(
                update={
                    "embedding_provider": "fake",
                    "llm_provider": "fake",
                    "enable_real_providers": False,
                }
            )
        questions, digest = load_golden(args.golden, settings.max_query_characters)
        options = EvaluationOptions(
            strategy=args.strategy,
            k=args.k,
            seed=args.seed,
            question_delay_seconds=args.delay_seconds,
            retrieval_only=args.retrieval_only,
        )
        result = run_evaluation(settings, questions, digest, options)
        path = write_report(result, args.output)
    except (GoldenDataError, ValidationError):
        print(
            "Invalid golden data/settings, k, or index. Run python -m eval.validate first.",
            file=sys.stderr,
        )
        return 2
    except SQLAlchemyError:
        print("Database unavailable; no model-quality result was produced.", file=sys.stderr)
        return 1
    except OSError:
        print("Cannot write evaluation output.", file=sys.stderr)
        return 1
    print(f"Report: {path}; questions={result.summary.questions}; errors={result.summary.errors}")
    return 1 if result.summary.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
