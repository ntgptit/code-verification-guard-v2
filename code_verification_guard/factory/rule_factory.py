"""Rule factory implementation."""

from __future__ import annotations

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.factory.matcher_factory import MatcherFactory
from code_verification_guard.rules.base_rule import BaseRule
from code_verification_guard.rules.generic_rule import GenericRule


class RuleFactory:
    """Creates rule instances from rule configuration."""
    def __init__(self, matcher_factory: MatcherFactory | None = None):
        """Create a rule factory."""
        self.matcher_factory = matcher_factory or MatcherFactory()

    def create(self, rule_config: dict) -> BaseRule:
        """Create a rule instance from a rule config."""
        rule_type = rule_config.get(ConfigKeys.TYPE)

        # Rule configs must declare their implementation type.
        if not rule_type:
            raise ValueError(f"Missing rule type: {rule_config}")

        matcher = self.matcher_factory.create(rule_type)
        return GenericRule(rule_config, matcher)

    def register(self, rule_type: str, matcher_class: type[BaseMatcher]) -> None:
        """Register a matcher class for a rule type."""
        self.matcher_factory.registry.register(rule_type, matcher_class)
