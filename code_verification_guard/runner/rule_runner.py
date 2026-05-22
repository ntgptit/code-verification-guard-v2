"""Rule execution orchestration."""

from __future__ import annotations

from pathlib import Path

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.constants.defaults import Defaults
from code_verification_guard.factory.rule_factory import RuleFactory
from code_verification_guard.models.violation import Violation
from code_verification_guard.registry.rule_registry import RuleRegistry


class RuleRunner:
    """Runs enabled rules and aggregates violations."""
    def __init__(
        self,
        rule_factory: RuleFactory | None = None,
        rule_registry: RuleRegistry | None = None,
    ):
        """Create a rule runner."""
        self.rule_factory = rule_factory or RuleFactory()
        self.rule_registry = rule_registry or RuleRegistry()

    def run(self, project_root: Path) -> list[Violation]:
        """Run all enabled rules against the project."""
        violations: list[Violation] = []

        for rule_config in self.rule_registry.all():
            # Disabled rules are skipped before construction.
            if not rule_config.get(ConfigKeys.ENABLED, Defaults.DEFAULT_RULE_ENABLED):
                continue

            rule = self.rule_factory.create(rule_config)
            violations.extend(rule.check(project_root))

        return violations
