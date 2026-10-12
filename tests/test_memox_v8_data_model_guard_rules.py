"""Fault-injection probes for the memox-v8 data-model rules.

Each rule looks for V8's names, and each is pinned in both directions: it
reports the defect written the way V8's code would write it, and it stays
silent on V8's correct shape, including a comment that quotes the defect.
"""

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
    / "memox-data-model-rules.yaml"
)


def _rule_config(rule_id: str) -> dict:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    for rule_config in registry.get("rules", []):
        if rule_config["id"] == rule_id:
            return deepcopy(rule_config)

    raise AssertionError(f"Rule not found: {rule_id}")


def _violations(rule_id: str, tmp_path: Path, relative_path: str, source: str) -> list:
    source_path = tmp_path / relative_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source, encoding="utf-8")

    rule_config = _rule_config(rule_id)
    rule_config.pop("scopes", None)
    rule_config["include"] = [relative_path]
    rule_config["exclude"] = []
    rule_config["enabled"] = True

    return RuleFactory().create(rule_config).check(tmp_path)


DAO = "lib/features/srs/data/datasources/sample_dao.dart"
QUERIES = "lib/core/database/tables/sample.drift"
CARD_TABLE = "lib/core/database/tables/card.drift"
SCREEN = "lib/features/study/presentation/widgets/sections/sample_widget.dart"
MODEL = "lib/features/srs/domain/models/sample_model.dart"

COALESCE = "memox.data_model.no_coalesce_parent_id"
CARD_COLUMNS = "memox.data_model.no_schedule_columns_on_card_table"
ACTIONS = "memox.data_model.review_actions_from_supported_actions"
KIND = "memox.data_model.review_kind_not_inferred"


def test_no_coalesce_parent_id_goes_red_on_every_spelling(tmp_path: Path) -> None:
    for relative_path, bad in (
        (QUERIES, "SELECT COALESCE(d.parent_id, d.id) AS root_id FROM deck d;\n"),
        (QUERIES, "SELECT coalesce(parent_id, id) FROM deck;\n"),
        (DAO, "        'SELECT COALESCE(parent_id, id) FROM deck'\n"),
        (DAO, "    final root = coalesce([deck.parentId, deck.id]);\n"),
    ):
        assert _violations(COALESCE, tmp_path, relative_path, bad), bad


def test_no_coalesce_parent_id_leaves_the_root_column_and_prose_alone(tmp_path: Path) -> None:
    dao = """
  /// The root of [cardId]'s tree, reached through `card.deck_id` and then
  /// `deck.root_id` — never `COALESCE(parent_id, id)` (BR-DECK-003); null
  /// when the card or its deck is in the Trash (BE-C3).
          ' JOIN deck root ON root.id = d.root_id'
"""
    queries = "-- never COALESCE(parent_id, id): the root is root_id\nSELECT root_id FROM deck;\n"
    assert not _violations(COALESCE, tmp_path, DAO, dao)
    assert not _violations(COALESCE, tmp_path, QUERIES, queries)


_TABLES = """CREATE TABLE card (
  id TEXT NOT NULL PRIMARY KEY,
  deck_id TEXT NOT NULL REFERENCES deck (id) ON DELETE CASCADE,
  front TEXT NOT NULL,
  back TEXT NOT NULL,
  -- NULL = active; otherwise a tombstone of that batch. Its schedule, due_at
  -- and all, lives in card_schedule.
  delete_batch_id TEXT REFERENCES delete_batches (id) ON DELETE CASCADE,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
) AS CardRow;

CREATE TABLE card_schedule (
  card_id TEXT NOT NULL PRIMARY KEY REFERENCES card (id) ON DELETE CASCADE,
  generation INTEGER NOT NULL,
  due_at DATETIME,
  current_box INTEGER,
  ease_factor REAL,
  interval_days INTEGER
) AS CardSchedule;
"""


def test_no_schedule_columns_on_card_table_goes_red_on_a_schedule_column(tmp_path: Path) -> None:
    # Before and after the comment whose `;` ends a naive `[^;]*` scan.
    for anchor in ("  back TEXT NOT NULL,\n", "  created_at DATETIME NOT NULL,\n"):
        for column in ("generation INTEGER NOT NULL", "due_at DATETIME", "current_box INTEGER",
                       "ease_factor REAL", "interval_days INTEGER", "scheduler_type TEXT"):
            bad = _TABLES.replace(anchor, f"{anchor}  {column},\n", 1)
            assert _violations(CARD_COLUMNS, tmp_path, CARD_TABLE, bad), (anchor, column)


def test_no_schedule_columns_on_card_table_leaves_v8s_tables_alone(tmp_path: Path) -> None:
    assert not _violations(CARD_COLUMNS, tmp_path, CARD_TABLE, _TABLES)


def test_review_actions_go_red_on_a_hardcoded_set(tmp_path: Path) -> None:
    for bad in (
        "for (final a in [Sm2Action.again, Sm2Action.hard, Sm2Action.good, Sm2Action.easy]) {}\n",
        """const grades = [
  Sm2Action.again,
  Sm2Action.hard,
  Sm2Action.good,
  Sm2Action.easy,
];
""",
        "const actions = [EightBoxAction.forgotten, EightBoxAction.remembered];\n",
    ):
        assert _violations(ACTIONS, tmp_path, SCREEN, bad), bad


def test_review_actions_leave_the_label_switch_and_supported_actions_alone(tmp_path: Path) -> None:
    good = """
  String studyGrade(Sm2Action action) => switch (action) {
    Sm2Action.again => cardActionAgain,
    Sm2Action.hard => cardActionHard,
    Sm2Action.good => cardActionGood,
    Sm2Action.easy => cardActionEasy,
  };
  String cardAction(Object action) => switch (action) {
    EightBoxAction.forgotten => cardActionForgotten,
    EightBoxAction.remembered => cardActionRemembered,
    _ => '',
  };
  final buttons = [for (final action in scheduler.supportedActions) button(action)];
"""
    assert not _violations(ACTIONS, tmp_path, SCREEN, good)


def test_review_actions_leave_a_comment_that_quotes_the_set_alone(tmp_path: Path) -> None:
    good = """
  // Never [Sm2Action.again, Sm2Action.hard, Sm2Action.good, Sm2Action.easy]:
  /// nor EightBoxAction.forgotten, EightBoxAction.remembered by hand.
"""
    assert not _violations(ACTIONS, tmp_path, SCREEN, good)


def test_review_kind_goes_red_when_inferred_from_the_boxes(tmp_path: Path) -> None:
    for bad in (
        "final kind = previousBox == nextBox ? ReviewKind.relearning : ReviewKind.scheduled;\n",
        "    kind: entry.previousBox != entry.nextBox ? ReviewKind.scheduled : ReviewKind.relearning,\n",
        "final turnKind = before.currentBox == after.currentBox ? ReviewKind.relearning : null;\n",
    ):
        assert _violations(KIND, tmp_path, MODEL, bad), bad


def test_review_kind_leaves_the_stored_and_session_kinds_alone(tmp_path: Path) -> None:
    good = """
  if (round > 1 || answersInSession > 0) return ReviewKind.relearning;
        kind: ReviewKind.scheduled,
    kind: round > 1 ? ReviewKind.relearning : ReviewKind.scheduled,
  final kind = turn.kind;
"""
    assert not _violations(KIND, tmp_path, MODEL, good)


def test_review_kind_leaves_a_comment_that_quotes_the_inference_alone(tmp_path: Path) -> None:
    good = """
  // Never `kind = previousBox == nextBox ? …`: a box-8 turn would read as relearning.
  /// The kind: previousBox != nextBox is not how a turn is labelled.
"""
    assert not _violations(KIND, tmp_path, MODEL, good)


QUERIES_IN_DRIFT = "memox.data_model.queries_in_drift"

SCOPES_PATH = (
    Path(__file__).parents[1]
    / "registries"
    / "projects"
    / "memox-v8"
    / "config"
    / "scopes.yaml"
)

# The exceptions ADR-020 grants for good (D7): the scope's only excludes.
PERMANENT_EXCLUDES = (
    "**/*.g.dart",
    "lib/core/database/schema_versions.dart",
    "lib/core/database/migrations/**",
    "lib/core/database/app_database.dart",
    "lib/core/database/local_data_reset.dart",
)


def test_queries_in_drift_goes_red_on_sql_strings_and_builder_chains(tmp_path: Path) -> None:
    for bad in (
        "    final row = await _db.customSelect('SELECT 1').getSingle();\n",
        "        .customSelect(\n",
        "    await _db.customUpdate(\n",
        "    await customInsert('INSERT INTO t VALUES (1)');\n",
        "    await _db.customStatement('DELETE FROM sync_outbox');\n",
        "      (_db.select(_db.card)..where((c) => c.id.equals(id))).getSingle();\n",
        "    final byId = await (_db.select(\n",
        "      .into(_db.card)\n",
        "      (_db.update(_db.appSettings)\n",
        "    await (select(logEntries)..limit(1)).get();\n",
        "    final query = selectOnly(logEntries)\n",
        "    (delete(logEntries)..where((t) => t.id.isIn(ids))).go();\n",
        "        _db.select(_card).join([\n",
        "    await _db.batch((b) => b.insertAll(_db.card, rows));\n",
        # `dart format` splits these, and the guard reads one line at a time.
        "  }) => _db.batch(\n",
        "    await _db.batch(\n",
        "  Future<void> write(List<LogEntry> rows) => batch(\n",
        # Inside an accessor, a table the mixin does not expose.
        "    final row = await (select(attachedDatabase.card)..limit(1)).get();\n",
        "    await (delete(this.deleteBatches)..where((b) => b.id.equals(id))).go();\n",
        "    final rows = await (_db.select(_db.card)).get();\n",
    ):
        assert _violations(QUERIES_IN_DRIFT, tmp_path, DAO, bad), bad


def test_queries_in_drift_leaves_generated_queries_pragmas_and_predicates_alone(
    tmp_path: Path,
) -> None:
    good = """
  /// Reads through `customSelect` were the old shape; ADR-020 moved them.
  // await _db.customSelect('SELECT 1');
  Future<List<TrashDeckEntryRow>> deckEntryRows() => trashDeckEntries().get();
  Future<void> purge(String batchId) => purgeDeleteBatch(batchId);
  Stream<void> entryChanges() =>
      tableChanges(attachedDatabase, [attachedDatabase.deleteBatches]);
  Future<void> defer() => _db.customStatement('PRAGMA defer_foreign_keys = ON');
  Expression<bool> _predicate(Card c) => c.deckId.equals(deckId) & c.deleteBatchId.isNull();
  Future<void> delete(String key) => _storage.delete(key: key);
  final names = parts.join(', ');
"""
    assert not _violations(QUERIES_IN_DRIFT, tmp_path, DAO, good)


def _scope(name: str) -> dict:
    return yaml.safe_load(SCOPES_PATH.read_text(encoding="utf-8"))["scopes"][name]


def test_drift_query_sites_excludes_only_adr_020_exceptions() -> None:
    # P8 deleted the temporary exclude: no file of lib/ outside D7 may write a
    # query in Dart, and none may be added back.
    scope = _scope("drift_query_sites")

    assert set(scope["exclude"]) == set(PERMANENT_EXCLUDES)


def test_drift_query_sites_covers_all_of_lib() -> None:
    # ADR-020 says "every query": lib/app, lib/shared and a feature's di/ are
    # as much app code as a DAO.
    assert _scope("drift_query_sites")["include"] == ["lib/**/*.dart"]
