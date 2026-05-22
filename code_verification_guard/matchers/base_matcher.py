"""Base matcher implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from code_verification_guard.models.scan_context import ScanContext
from code_verification_guard.models.violation import Violation

# Runtime imports should avoid circular dependencies.
if TYPE_CHECKING:
    from code_verification_guard.rules.base_rule import BaseRule


class BaseMatcher(ABC):
    """Base class for matcher implementations."""
    @abstractmethod
    def match(self, rule: "BaseRule", context: ScanContext) -> list[Violation]:
        """Return violations for one rule."""
        raise NotImplementedError
