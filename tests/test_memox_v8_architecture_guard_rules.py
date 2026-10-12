"""Fault-injection probes for the memox-v8 architecture rules that name V8's code."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from code_verification_guard.factory.rule_factory import RuleFactory

REGISTRY_PATH = (
    Path(__file__).parents[1]
    / "registries"
    / "projects"
    / "memox-v8"
    / "rules"
    / "memox-architecture-rules.yaml"
)
DB_ACCESS = "memox.architecture.widget_no_database_access"


def _rule_config(rule_id: str) -> dict:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    for rule_config in registry.get("rules", []):
        if rule_config["id"] == rule_id:
            return deepcopy(rule_config)

    raise AssertionError(f"Rule not found: {rule_id}")


def _violations(rule_id: str, tmp_path: Path, source: str) -> list:
    source_path = (
        tmp_path / "lib" / "features" / "deck" / "presentation" / "widgets" / "sections"
        / "sample_section_widget.dart"
    )
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = ["lib/**/*.dart"]
    rule_config["exclude"] = []
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


def test_widget_database_access_goes_red_on_v8s_database(tmp_path: Path) -> None:
    for bad in (
        "    final database = ref.watch(databaseProvider);\n",
        "    final rows = await ref.read(databaseProvider).select(table).get();\n",
        "    final rows = await database.select(database.card).get();\n",
        "    final decks = await deckDao.rootDecks();\n",
    ):
        assert _violations(DB_ACCESS, tmp_path, bad), bad


def test_widget_database_access_leaves_use_cases_and_prose_alone(tmp_path: Path) -> None:
    good = """
    // A widget reads through a use case, never databaseProvider.
    final decks = ref.watch(deckListProvider);
    final result = await ref.read(renameDeckUseCaseProvider).call(id, name);
    """
    assert not _violations(DB_ACCESS, tmp_path, good)


REMINDER_PLUGINS = "memox_v8.architecture.reminder_plugins_have_one_door"
PLUGINS_DOOR = (
    "lib/features/reminders/data/datasources/plugin_reminder_plugins_data_source.dart"
)


def _violations_at(rule_id: str, tmp_path: Path, files: dict[str, str]) -> list:
    for relative, source in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = ["lib/**/*.dart"]
    rule_config["enabled"] = True
    return RuleFactory().create(rule_config).check(tmp_path)


def test_reminder_plugins_are_imported_by_their_data_source_only(tmp_path: Path) -> None:
    for plugin in ("android_alarm_manager_plus", "flutter_local_notifications"):
        line = f"import 'package:{plugin}/{plugin}.dart';\n"
        assert _violations_at(
            REMINDER_PLUGINS, tmp_path / plugin,
            {"lib/app/app.dart": line},
        ), plugin
        assert not _violations_at(
            REMINDER_PLUGINS, tmp_path / f"{plugin}-door",
            {PLUGINS_DOOR: line},
        ), plugin


TTS_PLUGIN = "memox_v8.architecture.tts_plugin_has_one_door"
SPEECH_DOOR = "lib/core/speech/plugin_speech_synthesizer.dart"


def test_tts_plugin_is_imported_by_its_door_only(tmp_path: Path) -> None:
    line = "import 'package:flutter_tts/flutter_tts.dart';\n"
    assert _violations_at(
        TTS_PLUGIN, tmp_path / "leak",
        {"lib/features/study/presentation/screens/study_session_screen.dart": line},
    )
    assert not _violations_at(TTS_PLUGIN, tmp_path / "door", {SPEECH_DOOR: line})
