"""Application service for running the guard."""

from __future__ import annotations

from pathlib import Path

from code_verification_guard.config.config_manager import ConfigManager
from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.constants.defaults import Defaults
from code_verification_guard.constants.severity import Severity
from code_verification_guard.factory.reporter_factory import ReporterFactory
from code_verification_guard.registry.rule_registry import RuleRegistry
from code_verification_guard.runner.rule_runner import RuleRunner


class GuardApplication:
    """Coordinates config loading, rule running, and reporting."""
    def __init__(
        self,
        config_manager: ConfigManager | None = None,
        rule_runner: RuleRunner | None = None,
        reporter_factory: ReporterFactory | None = None,
        rule_registry: RuleRegistry | None = None,
    ):
        """Create a guard application."""
        self.config_manager = config_manager or ConfigManager()
        self.rule_registry = rule_registry or RuleRegistry()
        self.rule_runner = rule_runner or RuleRunner()
        self.reporter_factory = reporter_factory or ReporterFactory()

    def run(
        self,
        project: str,
        config: str,
        ruleset: str | None = None,
        profile: str | None = None,
    ) -> bool:
        """Run the guard and return whether it should fail."""
        project_root = Path(project).resolve()

        if ruleset:
            runtime_config, rule_configs = self.config_manager.load_ruleset_runtime(
                project_root,
                ruleset,
                profile,
            )
            return self._run_with_config(project_root, runtime_config, rule_configs)

        if profile:
            raise ValueError("--profile requires --ruleset")

        raise ValueError("--ruleset is required. Example: check --project . --ruleset memox")

    def run_legacy(self, project: str, config: str) -> bool:
        """Run the legacy project-config flow."""
        project_root = Path(project).resolve()
        config_path = project_root / config
        project_config = self.config_manager.load_project_config(config_path)
        profile_config = self.config_manager.load_profile_config(project_root, project_config)
        rule_configs = self.config_manager.load_rule_definitions(
            project_root,
            project_config,
            profile_config,
        )
        runtime_config = self.config_manager.merge_runtime_config(
            profile_config,
            project_config,
        )
        return self._run_with_config(project_root, runtime_config, rule_configs)

    def _run_with_config(
        self,
        project_root: Path,
        runtime_config: dict,
        rule_configs: list[dict],
    ) -> bool:
        """Run loaded rules against a project root."""
        report_config = runtime_config.get(ConfigKeys.REPORT, {})
        reporter = self.reporter_factory.create(
            report_config.get(
                ConfigKeys.FORMAT,
                Defaults.DEFAULT_REPORT_FORMAT,
            ),
            report_config.get(ConfigKeys.SHOW_FIX_HINT, False),
        )
        self.rule_registry.clear()
        self.rule_registry.register_all(rule_configs)
        violations = self.rule_runner.run(
            project_root,
            progress_callback=getattr(reporter, "progress", None),
        )
        reporter.print(violations)
        return self._should_fail(runtime_config, violations)

    def _should_fail(self, project_config: dict, violations: list) -> bool:
        """Return whether violations should fail the process."""
        failure_config = project_config.get(ConfigKeys.FAILURE, {})
        fail_on = set(failure_config.get(ConfigKeys.FAIL_ON, Defaults.DEFAULT_FAIL_ON))

        # Promote warnings when the project configuration requires it.
        if failure_config.get(ConfigKeys.WARNING_AS_ERROR, False):
            fail_on.add(Severity.WARNING)

        return any(violation.severity in fail_on for violation in violations)
