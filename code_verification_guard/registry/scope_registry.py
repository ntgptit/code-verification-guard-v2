"""Scope registry implementation."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock

from code_verification_guard.constants.config_keys import ConfigKeys


class ScopeRegistry:
    """Stores named file scopes for future rule grouping."""
    _instance = None
    _instance_lock = Lock()

    def __new__(cls, *args, **kwargs):
        """Return the shared scope registry instance."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._scopes = {}
                cls._instance._registry_lock = Lock()

        return cls._instance

    def __init__(self):
        """Create an empty scope registry."""
        return

    def register(
        self,
        name: str,
        include_patterns: list[str],
        exclude_patterns: list[str],
    ) -> None:
        """Register include and exclude patterns for a named scope."""
        with self._registry_lock:
            self._scopes[name] = {
                ConfigKeys.INCLUDE: list(include_patterns),
                ConfigKeys.EXCLUDE: list(exclude_patterns),
            }

    def get(self, name: str) -> dict:
        """Return scope configuration by name."""
        with self._registry_lock:
            return deepcopy(self._scopes.get(name, {}))

    def contains(self, name: str) -> bool:
        """Return whether a scope is registered."""
        with self._registry_lock:
            return name in self._scopes

    def clear(self) -> None:
        """Remove all registered scopes."""
        with self._registry_lock:
            self._scopes.clear()

    def reset(self) -> None:
        """Reset registry state between loads or tests."""
        self.clear()
