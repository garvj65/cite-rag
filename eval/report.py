"""Write measured results without presenting absent denominators as perfect scores."""

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from eval.models import EvaluationResult


def _number(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def results_table(results: list[EvaluationResult]) -> str:
    """Render comparable strategy/chunk rows with explicit errors and sample counts."""
    lines = [
        "| Strategy | Chunk words | k | Questions | Errors | Recall@k | MRR@k | "
        "Citation validity | Refusal accuracy | p50 ms | p95 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        options, summary = result.options, result.summary
        settings = result.metadata.get("settings")
        chunk = (
            settings.get("chunk_size_words", "unknown") if isinstance(settings, dict) else "unknown"
        )
        metrics = [
            summary.recall_at_k,
            summary.mrr,
            summary.citation_validity,
            summary.refusal_accuracy,
            summary.latency_p50_ms,
            summary.latency_p95_ms,
        ]
        lines.append(
            f"| {options.strategy} | {chunk} | {options.k} | "
            f"{summary.questions} | {summary.errors} | "
            + " | ".join(_number(value) for value in metrics)
            + " |"
        )
    return "\n".join(lines)


def render_report(result: EvaluationResult) -> str:
    """Describe actual counts, exact provenance, and the limits of reproducibility."""
    summary = result.summary
    label = (
        "FAKE/MIXED PROVIDERS: MECHANICS ONLY"
        if result.metadata.get("mechanics_only")
        else "Configured-provider evaluation"
    )
    return (
        f"# CiteRAG evaluation\n\n**{label}**\n\n"
        + results_table([result])
        + f"\n\nAnswerable: {summary.answerable}; unanswerable: {summary.unanswerable}; "
        f"correct refusals: {summary.correct_refusals}.\n"
        "Raw citation counts before refusal filtering/deduplication: "
        f"{summary.citations_valid} valid / "
        f"{summary.citations_proposed} proposed. Zero denominators are N/A.\n\n"
        "Recall and MRR are macro averages over answerable questions. k counts chunks; "
        "recall deduplicates pages, while MRR uses the first matching chunk rank. "
        "Retrieval failures score zero; generation failures retain retrieval measurements. "
        "Errors are never counted as correct refusals. Latency includes retrieval, generation, "
        "validation, and retries for every attempted question, including failures.\n\n"
        "No LLM judge is used. Citation validity measures quote provenance, not answer entailment. "
        "Faithfulness is not measured. A fixed seed controls question order; live providers, "
        "network conditions, database caches, and latencies are not bit-for-bit reproducible. "
        "Fake/mixed provider results are mechanics checks, not semantic-quality evidence.\n\n"
        "## Reproduction metadata\n\n```json\n"
        + json.dumps(
            {"options": result.options.model_dump(), **result.metadata}, indent=2, ensure_ascii=True
        )
        + "\n```\n"
    )


def atomic_write(path: Path, content: str) -> None:
    """Replace a result file atomically without exposing partially written reports."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix=".citerag-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def write_report(result: EvaluationResult, directory: Path) -> Path:
    """Save Markdown, complete JSON, and per-question JSONL with a unique run name."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    mode = "mechanics" if result.metadata.get("mechanics_only") else "configured"
    stem = f"{timestamp}_{mode}_{result.options.strategy}_k{result.options.k}"
    target = directory / f"{stem}.md"
    atomic_write(directory / f"{stem}.json", result.model_dump_json(indent=2) + "\n")
    atomic_write(
        directory / f"{stem}.jsonl", "".join(row.model_dump_json() + "\n" for row in result.rows)
    )
    atomic_write(target, render_report(result))
    return target
