"""Sanitized domain failures that are safe to display to a caller."""


class IngestionError(Exception):
    """Represent a rejected PDF using a stable, non-sensitive reason code."""


class ProviderError(Exception):
    """Represent a provider failure without including its response or request text."""


class ProviderTimeoutError(ProviderError):
    """Represent an exhausted provider timeout."""
