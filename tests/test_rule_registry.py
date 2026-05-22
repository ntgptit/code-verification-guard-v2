import pytest

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.registry.matcher_registry import MatcherRegistry
from code_verification_guard.registry.rule_registry import RuleRegistry
from code_verification_guard.registry.scope_registry import ScopeRegistry


def rule_config(rule_id: str) -> dict:
    return {
        ConfigKeys.ID: rule_id,
        ConfigKeys.TYPE: "regex",
        ConfigKeys.SEVERITY: "warning",
        ConfigKeys.ENABLED: True,
        ConfigKeys.MESSAGE: "Sample rule.",
        ConfigKeys.INCLUDE: ["**/*.py"],
        ConfigKeys.PATTERNS: ["sample"],
    }


def test_registries_are_singletons():
    assert RuleRegistry() is RuleRegistry()
    assert MatcherRegistry() is MatcherRegistry()
    assert ScopeRegistry() is ScopeRegistry()


def test_rule_registry_reset_clears_shared_state():
    registry = RuleRegistry()
    shared_registry = RuleRegistry()

    registry.clear()
    registry.register(rule_config("sample.one"))
    assert len(shared_registry.all()) == 1

    shared_registry.reset()
    assert registry.all() == []


def test_rule_registry_register_all_rejects_duplicate_rule_ids():
    registry = RuleRegistry()
    registry.clear()

    with pytest.raises(ValueError, match="Duplicate rule id"):
        registry.register_all(
            [
                rule_config("sample.duplicate"),
                rule_config("sample.duplicate"),
            ]
        )

    registry.clear()
