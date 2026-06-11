"""Rule execution orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.constants.defaults import Defaults
from code_verification_guard.constants.severity import Severity
from code_verification_guard.factory.rule_factory import RuleFactory
from code_verification_guard.models.violation import Violation
from code_verification_guard.registry.rule_registry import RuleRegistry
from code_verification_guard.rules.base_rule import BaseRule
from code_verification_guard.scanner.file_scanner import FileScanner
from code_verification_guard.scanner.rule_file_reader import RuleFileReader

ProgressCallback = Callable[[int, int, str], None]

# Meta rule ids for guard configuration diagnostics. A declared rule is always
# intentional, so a rule whose paths no longer select anything is reported as
# a warning instead of silently checking nothing.
RULE_WITHOUT_TARGETS_ID = "guard.config.rule_without_targets"
MISSING_TARGET_PATH_ID = "guard.config.missing_target_path"

_GLOB_CHARS = ("*", "?", "[")
_MAX_SAMPLE_RULE_IDS = 3


class RuleRunner:
    """Runs enabled rules and aggregates violations."""
    def __init__(
        self,
        rule_factory: RuleFactory | None = None,
        rule_registry: RuleRegistry | None = None,
        file_reader: RuleFileReader | None = None,
    ):
        """Create a rule runner."""
        self.rule_factory = rule_factory or RuleFactory()
        self.rule_registry = rule_registry or RuleRegistry()
        self.file_reader = file_reader

    def run(
        self,
        project_root: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> list[Violation]:
        """Run all enabled rules against the project."""
        violations: list[Violation] = []
        config_diagnostics: list[Violation] = []
        enabled_rule_configs = [
            rule_config
            for rule_config in self.rule_registry.all()
            if rule_config.get(ConfigKeys.ENABLED, Defaults.DEFAULT_RULE_ENABLED)
        ]
        total_rules = len(enabled_rule_configs)
        shared_file_reader = self.file_reader or RuleFileReader(scanner=FileScanner())

        for index, rule_config in enumerate(enabled_rule_configs, start=1):
            rule = self.rule_factory.create(rule_config)
            rule.file_reader = shared_file_reader
            violations.extend(rule.check(project_root))

            # A rule with an empty target set silently checks nothing.
            if not rule.target_files(project_root):
                config_diagnostics.append(
                    self._rule_without_targets_violation(rule, project_root)
                )

            if progress_callback:
                progress_callback(index, total_rules, rule.rule_id)

        config_diagnostics.extend(
            self._missing_literal_path_violations(project_root, enabled_rule_configs)
        )
        violations.extend(config_diagnostics)
        return violations

    def _rule_without_targets_violation(
        self,
        rule: BaseRule,
        project_root: Path,
    ) -> Violation:
        """Report a rule whose include/exclude patterns select no files."""
        return Violation(
            rule_id=RULE_WITHOUT_TARGETS_ID,
            severity=Severity.WARNING,
            message=(
                f"Rule `{rule.rule_id}` matched no target files; its include/exclude "
                "patterns no longer select anything, so the rule silently checks "
                "nothing. Update the configured paths, or remove/disable the rule."
            ),
            file_path=project_root,
            fix_hint=(
                "Check the rule's include/exclude patterns (and the scopes they come "
                "from) against the current project layout."
            ),
        )

    def _missing_literal_path_violations(
        self,
        project_root: Path,
        rule_configs: list[dict],
    ) -> list[Violation]:
        """Report literal (non-glob) configured paths that no longer exist."""
        missing_patterns: dict[str, list[str]] = {}

        for rule_config in rule_configs:
            rule_id = rule_config.get(ConfigKeys.ID, "<unknown>")

            for config_key in (ConfigKeys.INCLUDE, ConfigKeys.EXCLUDE):
                for pattern in rule_config.get(config_key) or []:
                    # Glob patterns may legitimately match nothing yet.
                    if any(glob_char in pattern for glob_char in _GLOB_CHARS):
                        continue

                    # Only literal paths into the source tree indicate rename
                    # drift. Root-level literals such as `.env` belong to
                    # file-presence-ban rules where absence is the goal.
                    if "/" not in pattern:
                        continue

                    if (project_root / pattern).exists():
                        continue

                    rule_ids = missing_patterns.setdefault(pattern, [])
                    if rule_id not in rule_ids:
                        rule_ids.append(rule_id)

        return [
            self._missing_target_path_violation(project_root, pattern, rule_ids)
            for pattern, rule_ids in missing_patterns.items()
        ]

    def _missing_target_path_violation(
        self,
        project_root: Path,
        pattern: str,
        rule_ids: list[str],
    ) -> Violation:
        """Report one configured literal path that does not exist."""
        sample_rule_ids = ", ".join(rule_ids[:_MAX_SAMPLE_RULE_IDS])

        if len(rule_ids) > _MAX_SAMPLE_RULE_IDS:
            sample_rule_ids += f", … ({len(rule_ids)} rules total)"

        return Violation(
            rule_id=MISSING_TARGET_PATH_ID,
            severity=Severity.WARNING,
            message=(
                f"Configured target path `{pattern}` does not exist in the project "
                f"(referenced by: {sample_rule_ids}). The file has likely been moved "
                "or renamed; update the rule/scope configuration to match."
            ),
            file_path=project_root / pattern,
            fix_hint=(
                "Find the renamed file in the project and update the rule or scope "
                "pattern, or drop the stale path."
            ),
        )
