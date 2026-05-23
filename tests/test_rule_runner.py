from pathlib import Path

from code_verification_guard.constants.config_keys import ConfigKeys
from code_verification_guard.registry.rule_registry import RuleRegistry
from code_verification_guard.runner.rule_runner import RuleRunner
from code_verification_guard.scanner.file_scanner import FileScanner
from code_verification_guard.scanner.rule_file_reader import RuleFileReader


class CountingFileScanner(FileScanner):
    """Scanner test double that counts full project walks."""

    def __init__(self):
        super().__init__()
        self.collect_project_files_count = 0

    def _collect_project_files(self, project_root: Path):
        self.collect_project_files_count += 1
        return super()._collect_project_files(project_root)


class CountingRuleFileReader(RuleFileReader):
    """Reader test double that counts disk reads."""

    def __init__(self, scanner: FileScanner):
        super().__init__(scanner=scanner)
        self.read_text_count = 0

    def read_text(self, file_path: Path) -> str:
        self.read_text_count += 1
        return super().read_text(file_path)


def test_rule_runner_reads_rules_from_rule_registry(tmp_path: Path):
    source = tmp_path / "main.py"
    source.write_text("print('hello')\n", encoding="utf-8")
    registry = RuleRegistry()
    registry.clear()
    registry.register(
        {
            ConfigKeys.ID: "python.no_print",
            ConfigKeys.TYPE: "regex",
            ConfigKeys.MODE: "line",
            ConfigKeys.SEVERITY: "warning",
            ConfigKeys.ENABLED: True,
            ConfigKeys.MESSAGE: "No print.",
            ConfigKeys.INCLUDE: ["**/*.py"],
            ConfigKeys.PATTERNS: ["\\bprint\\s*\\("],
        }
    )

    violations = RuleRunner(rule_registry=registry).run(tmp_path)

    assert len(violations) == 1
    assert violations[0].rule_id == "python.no_print"
    registry.clear()


def test_rule_runner_reports_progress_for_enabled_rules(tmp_path: Path):
    source = tmp_path / "main.py"
    source.write_text("print('hello')\n", encoding="utf-8")
    registry = RuleRegistry()
    registry.clear()
    registry.register(
        {
            ConfigKeys.ID: "python.no_print",
            ConfigKeys.TYPE: "regex",
            ConfigKeys.MODE: "line",
            ConfigKeys.SEVERITY: "warning",
            ConfigKeys.ENABLED: True,
            ConfigKeys.MESSAGE: "No print.",
            ConfigKeys.INCLUDE: ["**/*.py"],
            ConfigKeys.PATTERNS: ["\\bprint\\s*\\("],
        }
    )
    registry.register(
        {
            ConfigKeys.ID: "python.disabled",
            ConfigKeys.TYPE: "regex",
            ConfigKeys.MODE: "line",
            ConfigKeys.SEVERITY: "warning",
            ConfigKeys.ENABLED: False,
            ConfigKeys.MESSAGE: "Disabled.",
            ConfigKeys.INCLUDE: ["**/*.py"],
            ConfigKeys.PATTERNS: ["disabled"],
        }
    )
    progress_events = []

    def record_progress(completed_rules: int, total_rules: int, rule_id: str) -> None:
        progress_events.append((completed_rules, total_rules, rule_id))

    RuleRunner(rule_registry=registry).run(tmp_path, progress_callback=record_progress)

    assert progress_events == [(1, 1, "python.no_print")]
    registry.clear()


def test_rule_runner_reuses_file_scan_and_file_reads_across_rules(tmp_path: Path):
    source = tmp_path / "main.py"
    source.write_text("print('hello')\n", encoding="utf-8")
    registry = RuleRegistry()
    registry.clear()

    for rule_id, pattern in [
        ("python.no_print", "\\bprint\\s*\\("),
        ("python.no_hello", "hello"),
    ]:
        registry.register(
            {
                ConfigKeys.ID: rule_id,
                ConfigKeys.TYPE: "regex",
                ConfigKeys.MODE: "line",
                ConfigKeys.SEVERITY: "warning",
                ConfigKeys.ENABLED: True,
                ConfigKeys.MESSAGE: "Matched.",
                ConfigKeys.INCLUDE: ["**/*.py"],
                ConfigKeys.PATTERNS: [pattern],
            }
        )

    scanner = CountingFileScanner()
    reader = CountingRuleFileReader(scanner=scanner)

    violations = RuleRunner(rule_registry=registry, file_reader=reader).run(tmp_path)

    assert len(violations) == 2
    assert scanner.collect_project_files_count == 1
    assert reader.read_text_count == 1
    registry.clear()
