"""Rule registry implementation."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock

from code_verification_guard.constants.config_keys import ConfigKeys


class RuleRegistry:
    """Stores rule configuration dictionaries by rule id."""
    _instance = None
    _instance_lock = Lock()

    def __new__(cls, *args, **kwargs):
        """Return the shared rule registry instance."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._rules = {}
                cls._instance._registry_lock = Lock()

        return cls._instance

    def __init__(self, rule_configs: list[dict] | None = None):
        """Create or refresh a registry from optional rule configs."""
        if rule_configs is None:
            return

        self.clear()
        self.register_all(rule_configs)

    def register(self, rule_config: dict) -> None:
        """Register one rule configuration."""
        rule_id = rule_config[ConfigKeys.ID]

        with self._registry_lock:
            if rule_id in self._rules:
                raise ValueError(f"Duplicate rule id '{rule_id}'")

            self._rules[rule_id] = deepcopy(rule_config)

    def register_all(self, rule_configs: list[dict]) -> None:
        """Register multiple rule configurations."""
        for rule_config in rule_configs:
            self.register(rule_config)

    def all(self) -> list[dict]:
        """Return all registered rule configurations."""
        with self._registry_lock:
            return [
                deepcopy(rule_config)
                for rule_config in self._rules.values()
            ]

    def clear(self) -> None:
        """Remove all registered rules."""
        with self._registry_lock:
            self._rules.clear()

    def reset(self) -> None:
        """Reset registry state between runs or tests."""
        self.clear()
