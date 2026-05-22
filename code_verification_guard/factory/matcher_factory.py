"""Matcher factory implementation."""

from __future__ import annotations

from code_verification_guard.matchers.base_matcher import BaseMatcher
from code_verification_guard.registry.matcher_registry import MatcherRegistry


class MatcherFactory:
    """Creates matcher instances from rule types."""
    def __init__(self, registry: MatcherRegistry | None = None):
        """Create a matcher factory."""
        self.registry = registry or MatcherRegistry()

    def create(self, matcher_type: str) -> BaseMatcher:
        """Create a matcher for a rule type."""
        matcher_class = self.registry.get(matcher_type)

        # Unsupported types should explain the accepted values.
        if matcher_class is None:
            supported_types = ", ".join(self.registry.keys())
            raise ValueError(
                f"Unsupported rule type: {matcher_type}. "
                f"Supported types: {supported_types}"
            )

        return matcher_class()
