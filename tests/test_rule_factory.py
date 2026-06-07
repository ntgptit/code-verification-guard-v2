import pytest

from code_verification_guard.factory.rule_factory import RuleFactory
from code_verification_guard.rules.generic_rule import GenericRule


def test_create_regex_rule():
    rule = RuleFactory().create(
        {
            "id": "test.regex",
            "type": "regex",
            "severity": "warning",
            "message": "Test regex.",
            "patterns": ["test"],
        }
    )

    assert isinstance(rule, GenericRule)


def test_create_dart_shared_widget_doc_rule():
    rule = RuleFactory().create(
        {
            "id": "flutter.shared_widget.dart_doc.required",
            "type": "dart_shared_widget_doc",
            "severity": "error",
            "enabled": True,
            "message": "Docs required.",
            "check": "required",
        }
    )

    assert isinstance(rule, GenericRule)


def test_unsupported_rule_type():
    with pytest.raises(ValueError):
        RuleFactory().create(
            {
                "id": "test.unknown",
                "type": "unknown",
            }
        )
