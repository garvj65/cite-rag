"""Download explicitly selected public PDFs from corpus/manifest.yaml."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx
import yaml
from app.ingestion.manifest import CorpusDocument, load_manifest
from app.settings import Settings
from pydantic import ValidationError


def download_document(
    document: CorpusDocument,
    destination: Path,
    client: httpx.Client,
    max_bytes: int,
) -> str:
    """Download one bounded PDF atomically; reuse an existing nonempty PDF."""
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / document.filename
    if target.exists() and target.stat().st_size <= max_bytes:
        with target.open("rb") as existing:
            if existing.read(5) == b"%PDF-":
                return "already_downloaded"
    temporary = target.with_suffix(".part")
    try:
        with client.stream("GET", str(document.url), follow_redirects=True) as response:
            response.raise_for_status()
            size = 0
            prefix = bytearray()
            with temporary.open("wb") as stream:
                for block in response.iter_bytes():
                    size += len(block)
                    if size > max_bytes:
                        raise ValueError("pdf_too_large")
                    if len(prefix) < 5:
                        prefix.extend(block[: 5 - len(prefix)])
                    stream.write(block)
            if prefix != b"%PDF-":
                raise ValueError("response_is_not_pdf")
        temporary.replace(target)
        return "downloaded"
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    """Download a strict manifest, reporting failures without provider or URL secrets."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("corpus/manifest.yaml"))
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        settings = Settings()
    except (OSError, ValidationError, yaml.YAMLError):
        print("Invalid settings or corpus manifest.", file=sys.stderr)
        return 2
    failures = 0
    with httpx.Client(timeout=settings.provider_timeout_seconds) as client:
        for document in manifest.documents:
            try:
                status = download_document(
                    document, args.manifest.parent, client, settings.max_pdf_bytes
                )
                print(f"{document.title}: {status}")
            except (httpx.HTTPError, OSError, ValueError):
                failures += 1
                print(f"{document.title}: download_failed", file=sys.stderr)
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
