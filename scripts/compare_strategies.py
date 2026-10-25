"""Compare retrieval strategies and chunk sizes on the same user-authored golden data."""

import argparse
import sys
from collections.abc import Sequence
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

import yaml
from app.db.repository import PostgresIngestionRepository, create_db_engine
from app.errors import ProviderError
from app.ingestion.manifest import load_manifest
from app.ingestion.service import IngestionService, indexing_profile
from app.providers.factory import create_embedding_provider
from app.settings import Settings
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from eval.models import EvaluationOptions, EvaluationResult
from eval.report import atomic_write, results_table, write_report
from eval.runtime import inspect_index, run_evaluation
from eval.schema import GoldenDataError, load_golden


def ingest_profile(settings: Settings, corpus: Path) -> None:
    """Index a chunk configuration without downloads or hidden provider failures."""
    files = sorted(p for p in corpus.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
    if not files:
        raise GoldenDataError("No PDFs found for comparison ingestion.")
    manifest = corpus / "manifest.yaml"
    metadata = (
        {doc.filename: doc for doc in load_manifest(manifest).documents}
        if manifest.exists()
        else {}
    )
    engine = create_db_engine(settings)
    try:
        with ExitStack() as stack:
            provider = create_embedding_provider(settings, stack)
            service = IngestionService(settings, provider, PostgresIngestionRepository(engine))
            for path in files:
                result = service.ingest(path, metadata.get(path.name))
                if result.status == "failed":
                    raise ProviderError("comparison_ingestion_failed")
    finally:
        engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    """Validate inputs, optionally ingest, and persist a combined comparison table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strategies",
        choices=("vector", "keyword", "hybrid"),
        nargs="+",
        default=["vector", "keyword", "hybrid"],
    )
    parser.add_argument("--chunk-sizes", type=int, nargs="+", required=True)
    parser.add_argument("--overlap", type=int)
    parser.add_argument("--k", type=int, default=EvaluationOptions().k)
    parser.add_argument("--seed", type=int, default=EvaluationOptions().seed)
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0,
        help="Pause between questions; excluded from latency",
    )
    parser.add_argument("--golden", type=Path, default=Path("eval/golden.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("eval/results"))
    parser.add_argument(
        "--ingest", action="store_true", help="Explicitly embed/index each requested profile"
    )
    parser.add_argument("--corpus", type=Path, default=Path("corpus"))
    parser.add_argument(
        "--fake", action="store_true", help="Mechanics-only providers, never semantic benchmarking"
    )
    args = parser.parse_args(argv)
    try:
        base = Settings()
        if args.fake:
            base = base.model_copy(
                update={
                    "embedding_provider": "fake",
                    "llm_provider": "fake",
                    "enable_real_providers": False,
                }
            )
        questions, digest = load_golden(args.golden, base.max_query_characters)
        configurations = [
            Settings.model_validate(
                {
                    **base.model_dump(),
                    "chunk_size_words": size,
                    "chunk_overlap_words": base.chunk_overlap_words
                    if args.overlap is None
                    else args.overlap,
                }
            )
            for size in dict.fromkeys(args.chunk_sizes)
        ]
        options = [
            EvaluationOptions(
                strategy=strategy,
                k=args.k,
                seed=args.seed,
                question_delay_seconds=args.delay_seconds,
            )
            for strategy in dict.fromkeys(args.strategies)
        ]
        if args.k > base.search_max_k or not configurations:
            raise GoldenDataError("Invalid comparison bounds.")
        if args.ingest:
            for config in configurations:
                ingest_profile(config, args.corpus)
        engine = create_db_engine(base)
        try:
            corpora = [
                inspect_index(engine, indexing_profile(config), questions)
                for config in configurations
            ]
        finally:
            engine.dispose()
        doc_sets = [{doc["doc_id"] for doc in corpus} for corpus in corpora]
        if any(doc_ids != doc_sets[0] for doc_ids in doc_sets):
            raise GoldenDataError("Comparison profiles contain different documents.")
        results: list[EvaluationResult] = []
        for config in configurations:
            for option in options:
                result = run_evaluation(config, questions, digest, option)
                write_report(result, args.output)
                results.append(result)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        label = (
            "MECHANICS ONLY: fake/mixed providers"
            if any(r.metadata.get("mechanics_only") for r in results)
            else "Configured-provider comparison"
        )
        target = args.output / f"{timestamp}_comparison.md"
        atomic_write(
            target,
            f"# {label}\n\n{results_table(results)}\n\n"
            f"Seed: {args.seed}. Golden SHA-256: {digest}.\n\n"
            "Each run has adjacent JSON/JSONL records and full provenance. All profiles use "
            "the same document identities, golden data, overlap, and seeded question order. "
            "Run against a quiescent index. Cache/network effects and live model responses "
            "are not controlled by the seed. No faithfulness judge is used.\n",
        )
    except (GoldenDataError, ValidationError, yaml.YAMLError):
        print(
            "Invalid golden data, comparison settings, corpus manifest, or index profiles.",
            file=sys.stderr,
        )
        return 2
    except (SQLAlchemyError, ProviderError):
        print(
            "Comparison database/provider operation failed; "
            "check configuration and saved partial reports.",
            file=sys.stderr,
        )
        return 1
    except OSError:
        print("Cannot read corpus or write comparison output.", file=sys.stderr)
        return 1
    print(f"Comparison: {target}; runs={len(results)}")
    return int(any(result.summary.errors for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
