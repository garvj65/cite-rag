"""Pure metric functions with explicit denominators and no model judge."""

import math
from collections.abc import Sequence

from eval.schema import GoldPage


def recall_at_k(gold: Sequence[GoldPage], retrieved: Sequence[GoldPage], k: int) -> float:
    """Measure the fraction of distinct gold pages found among the first k chunks."""
    if k < 1 or not gold:
        raise ValueError("recall requires positive k and nonempty gold pages")
    expected = set(gold)
    return len(expected.intersection(retrieved[:k])) / len(expected)


def reciprocal_rank(gold: Sequence[GoldPage], retrieved: Sequence[GoldPage], k: int) -> float:
    """Return the reciprocal rank of the first chunk on any gold page, or zero."""
    if k < 1 or not gold:
        raise ValueError("MRR requires positive k and nonempty gold pages")
    expected = set(gold)
    return next((1 / rank for rank, page in enumerate(retrieved[:k], 1) if page in expected), 0.0)


def citation_validity(valid: int, proposed: int) -> float | None:
    """Divide raw verified citations by raw proposed citations; zero proposals is undefined."""
    if not 0 <= valid <= proposed:
        raise ValueError("invalid citation counts")
    return valid / proposed if proposed else None


def refusal_accuracy(refused: int, unanswerable: int) -> float | None:
    """Measure correct refusals on negatives; provider errors are not correct refusals."""
    if not 0 <= refused <= unanswerable:
        raise ValueError("invalid refusal counts")
    return refused / unanswerable if unanswerable else None


def percentile(values: Sequence[float], quantile: float) -> float | None:
    """Compute a linearly interpolated percentile, returning None for no samples."""
    if not 0 <= quantile <= 1 or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("invalid latency values or quantile")
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
