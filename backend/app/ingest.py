"""Run `python -m app.ingest --path corpus/` after applying database migrations."""

import argparse
import json
import sys
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path

import yaml
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.db.repository import PostgresIngestionRepository, create_db_engine
from app.errors import ProviderError
from app.ingestion.manifest import load_manifest
from app.ingestion.service import IngestionResult, IngestionService
from app.providers.factory import create_embedding_provider
from app.settings import Settings


def main(argv: Sequence[str] | None = None) -> int:
    """Ingest a file/directory and print progress plus a machine-readable summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument(
        "--fake", action="store_true", help="Explicit offline smoke-test embeddings"
    )
    args = parser.parse_args(argv)
    if not args.path.exists():
        print("Input path does not exist.", file=sys.stderr)
        return 2
    files = (
        [args.path]
        if args.path.is_file()
        else sorted(
            path
            for path in args.path.rglob("*")
            if path.is_file() and path.suffix.lower() == ".pdf"
        )
    )
    if any(path.suffix.lower() != ".pdf" for path in files):
        print("Input file must be a PDF.", file=sys.stderr)
        return 2
    try:
        settings = Settings()
        manifest_path = (args.path if args.path.is_dir() else args.path.parent) / "manifest.yaml"
        metadata = (
            {item.filename: item for item in load_manifest(manifest_path).documents}
            if manifest_path.exists()
            else {}
        )
    except (ValidationError, OSError, yaml.YAMLError):
        print("Invalid settings or corpus manifest.", file=sys.stderr)
        return 2
    if not files:
        print(json.dumps({"docs": 0, "pages": 0, "chunks": 0, "files": []}))
        return 0
    results: list[IngestionResult] = []
    engine = create_db_engine(settings)
    try:
        with ExitStack() as stack:
            provider_settings = (
                settings.model_copy(update={"embedding_provider": "fake"})
                if args.fake
                else settings
            )
            provider = create_embedding_provider(provider_settings, stack)
            service = IngestionService(settings, provider, PostgresIngestionRepository(engine))
            print(f"Index profile: {service.profile}", file=sys.stderr)
            for index, path in enumerate(files, start=1):
                result = service.ingest(path, metadata.get(path.name))
                results.append(result)
                print(
                    f"[{index}/{len(files)}] {path.name}: {result.status} ({result.reason})",
                    file=sys.stderr,
                )
    except ProviderError:
        print(
            "Provider unavailable: enable real providers and configure its API key, "
            "or use --fake for an offline smoke test.",
            file=sys.stderr,
        )
        return 2
    except SQLAlchemyError:
        print(
            "Database unavailable or write failed; check configuration and migrations.",
            file=sys.stderr,
        )
        return 1
    finally:
        engine.dispose()
    print(
        json.dumps(
            {
                "docs": sum(result.status == "indexed" for result in results),
                "pages": sum(result.pages for result in results),
                "chunks": sum(result.chunks for result in results),
                "skipped": sum(result.status == "skipped" for result in results),
                "failed": sum(result.status == "failed" for result in results),
                "files": [asdict(result) for result in results],
            }
        )
    )
    return int(any(result.status == "failed" for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
