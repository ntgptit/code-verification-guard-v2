"""Regression tests for false-positive fixes that live only in this vendored copy.

Two rule fixes were made here in response to real MemoX false positives, and
because this guard is now owned as a vendored copy of MemoX (see AGENTS.md), they
have to be pinned by tests so a future edit — or a careless re-vendor — cannot
silently bring the false positives back:

  1. ``common.no_commented_out_code`` used to flag any prose comment that began
     with a keyword like ``for`` or ``return``. It now requires the *syntax* that
     follows the keyword in real code, so a wrapped explanatory comment is left
     alone while genuine commented-out code is still caught.

  2. ``memox.testing.no_real_clock_in_test`` used to match ``DateTime.now()``
     wherever it appeared, including inside a comment that merely named it. It is
     now anchored so it only fires on a call reached without passing a ``//``.

Each test asserts both directions: the benign case produces no violation, and the
real defect still does. Loading the rule from the registry YAML — rather than
re-declaring the pattern — is what makes this a regression test for the fix
itself, not for a copy of it.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

_ROOT = Path(__file__).parents[1]
_COMMON_RULES = _ROOT / "registries" / "common" / "common-convention-rules.yaml"
_MEMOX_TESTING_RULES = (
    _ROOT
    / "registries"
    / "projects"
    / "memox-v8"
    / "rules"
    / "memox-testing-rules.yaml"
)


def _rule_config(registry_path: Path, rule_id: str) -> dict:
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    for rule_config in registry.get("rules", []):
        if rule_config["id"] == rule_id:
            return deepcopy(rule_config)
    raise AssertionError(f"Rule not found: {rule_id} in {registry_path}")


def _violations(registry_path: Path, rule_id: str, tmp_path: Path, source: str) -> list:
    source_path = tmp_path / "lib" / "sample.dart"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(registry_path, rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = ["**/*.dart"]
    rule_config["exclude"] = []
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


# --------------------------------------------------------------------------
# 1. common.no_commented_out_code — prose is not commented-out code.
# --------------------------------------------------------------------------


def test_no_commented_out_code_ignores_prose_comments(tmp_path: Path) -> None:
    # The exact shape that used to trip it: a wrapped sentence beginning with a
    # keyword. None of these is code, and none may be reported.
    prose = "\n".join(
        [
            "// for this assertion we keep the raw value.",
            "// return the trimmed name to the caller once BR-01 has run.",
            "// if the boundary has already passed we refresh immediately.",
            "// while the screen sits still nothing changes.",
        ]
    )
    assert _violations(_COMMON_RULES, "common.no_commented_out_code", tmp_path, prose) == []


def test_no_commented_out_code_still_flags_real_code(tmp_path: Path) -> None:
    # The fix must not have blunted the rule: genuinely commented-out statements
    # still have to be caught.
    code = "\n".join(
        [
            "// final name = deck.name;",
            "// if (ready) { run(); }",
            "// return value;",
        ]
    )
    violations = _violations(
        _COMMON_RULES, "common.no_commented_out_code", tmp_path, code
    )
    assert len(violations) >= 3


# --------------------------------------------------------------------------
# 2. memox.testing.no_real_clock_in_test — naming the call is not calling it.
# --------------------------------------------------------------------------


def test_no_real_clock_ignores_the_call_named_in_a_comment(tmp_path: Path) -> None:
    # A doc comment explaining *why* the clock is injected names the call. That
    # is prose about the code, and the rule must measure the code, not the prose.
    commented = "\n".join(
        [
            "// Tests never read DateTime.now(); the clock is injected instead.",
            "/// Pass a fixed instant rather than DateTime.now().",
            "final t = clock();  // not DateTime.now()",
        ]
    )
    assert (
        _violations(
            _MEMOX_TESTING_RULES,
            "memox.testing.no_real_clock_in_test",
            tmp_path,
            commented,
        )
        == []
    )


def test_no_real_clock_still_flags_the_real_call(tmp_path: Path) -> None:
    # And the actual defect the rule exists for is still caught.
    code = "final now = DateTime.now();\n"
    violations = _violations(
        _MEMOX_TESTING_RULES,
        "memox.testing.no_real_clock_in_test",
        tmp_path,
        code,
    )
    assert len(violations) == 1
