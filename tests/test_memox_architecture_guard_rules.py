"""Integration-style tests for MemoX architecture guard regex rules."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

REGISTRY_PATH = (
    Path(__file__).parents[1]
    / "registries"
    / "projects"
    / "memox"
    / "rules"
    / "memox-architecture-rules.yaml"
)


def _rule_config(rule_id: str) -> dict:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    for rule_config in registry.get("rules", []):
        if rule_config["id"] == rule_id:
            return deepcopy(rule_config)

    raise AssertionError(f"Rule not found: {rule_id}")


def _violations(rule_id: str, tmp_path: Path, source: str) -> list:
    source_path = tmp_path / "lib" / "app" / "di" / "sample.dart"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = ["lib/**/*.dart"]
    rule_config["exclude"] = []
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


def test_core_di_ui_import_rule_only_blocks_presentation_imports(
    tmp_path: Path,
) -> None:
    bad = """
    import 'package:memox_v6/presentation/features/dashboard/widgets/dashboard_header.dart';

    @Riverpod(keepAlive: true)
    class AuthSessionController extends _$AuthSessionController {
      @override
      Future<void> build() async {}
    }
    """
    good = """
    @Riverpod(keepAlive: true)
    class AuthSessionController extends _$AuthSessionController {
      @override
      Future<void> build() async {}
    }
    """

    assert _violations("memox.architecture.core_di_no_ui_imports", tmp_path, bad)
    assert not _violations("memox.architecture.core_di_no_ui_imports", tmp_path, good)


def test_core_di_state_notifier_rule_is_a_warning_and_flags_notifiers_in_app_di(
    tmp_path: Path,
) -> None:
    bad = """
    @Riverpod(keepAlive: true)
    class FlashcardListViewModel extends _$FlashcardListViewModel {
      @override
      Future<void> build() async {}
    }
    """
    good = """
    @riverpod
    FlashcardRepository flashcardRepository(Ref ref) => FlashcardRepositoryImpl();
    """
    rule = _rule_config("memox.architecture.core_di_no_state_notifiers")

    assert rule["severity"] == "warning"
    assert _violations("memox.architecture.core_di_no_state_notifiers", tmp_path, bad)
    assert not _violations("memox.architecture.core_di_no_state_notifiers", tmp_path, good)


def test_persist_time_as_utc_rule_flags_bare_now_but_allows_to_utc(
    tmp_path: Path,
) -> None:
    bad = """
    int touch() {
      final DateTime now = DateTime.now();
      return now.millisecondsSinceEpoch;
    }
    """
    good = """
    int touch() => DateTime.now().toUtc().millisecondsSinceEpoch;
    """
    rule = _rule_config("memox.architecture.persist_time_as_utc")

    assert rule["severity"] == "warning"
    assert _violations("memox.architecture.persist_time_as_utc", tmp_path, bad)
    assert not _violations("memox.architecture.persist_time_as_utc", tmp_path, good)


def test_no_secret_in_shared_preferences_flags_token_keys_only(tmp_path: Path) -> None:
    bad = """
    Future<void> save(String token, String refresh) async {
      await _prefs.setString(_accessTokenKey, token);
      await _prefs.setString('refresh_token', refresh);
    }
    """
    good = """
    Future<void> save(CloudAccountLink link) async {
      await _prefs.setString(_cloudAccountLinkKey, jsonEncode(link.toJson()));
      await _prefs.setInt(_dailyNewLimitKey, 20);
    }
    """
    rule = _rule_config("memox.architecture.no_secret_in_shared_preferences")

    assert rule["severity"] == "error"
    assert _violations("memox.architecture.no_secret_in_shared_preferences", tmp_path, bad)
    assert not _violations(
        "memox.architecture.no_secret_in_shared_preferences", tmp_path, good
    )
