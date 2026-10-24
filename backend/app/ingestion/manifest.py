"""Validate corpus metadata shared by the downloader and ingestion CLI."""

import hashlib
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class CorpusDocument(BaseModel):
    """Describe one explicitly selected public PDF source."""

    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    url: HttpUrl
    source: str = Field(min_length=1)

    @property
    def filename(self) -> str:
        """Derive a safe stable filename without trusting URL path components."""
        slug = re.sub(r"[^a-z0-9]+", "-", self.title.casefold()).strip("-")[:70] or "document"
        suffix = hashlib.sha256(str(self.url).encode()).hexdigest()[:12]
        return f"{slug}-{suffix}.pdf"


class CorpusManifest(BaseModel):
    """Validate a corpus manifest before downloading or storing any document."""

    model_config = ConfigDict(extra="forbid")
    documents: list[CorpusDocument]

    @model_validator(mode="after")
    def unique_sources(self) -> "CorpusManifest":
        """Reject duplicate source URLs instead of counting the same PDF twice."""
        urls = [str(document.url) for document in self.documents]
        if len(urls) != len(set(urls)):
            raise ValueError("manifest contains duplicate URLs")
        if any(document.url.scheme != "https" for document in self.documents):
            raise ValueError("corpus sources must use HTTPS")
        return self


def load_manifest(path: Path) -> CorpusManifest:
    """Read a strict YAML manifest without constructing arbitrary Python objects."""
    return CorpusManifest.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
