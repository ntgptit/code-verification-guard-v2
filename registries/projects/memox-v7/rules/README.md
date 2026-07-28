# memox-v7 ruleset

The main guard for the memox-v7 repository. It owns every check
`flutter analyze` cannot express.

```bash
python code-verification-guard-v2/guard/run.py check --project . --ruleset memox-v7
```

## Why this ruleset exists separately from `memox`, `memox-v4`, `memox-v5`

Those are for different repositories and different layouts, and none of them fit
here:

| Ruleset | Why it does not apply |
|---|---|
| `memox`, `memox-v4` | Flutter, but a layer-first tree (`lib/presentation/features/**`, `lib/data/datasources/**`). memox-v7 is **feature-first**: `lib/features/<feature>/{domain,data,presentation}`. Every scope path differs, so the rules would silently match nothing. |
| `memox-v5` | Expo + React Native. Different language entirely. |
| `memox-design-jsx` | JSX design-kit rules. |

They are deliberately **not vendored** into this repo — carrying them would make
it easy to run the wrong one, and a ruleset that matches nothing reports a clean
pass.

## What it replaces

`custom_lint` and `riverpod_lint` are descoped (see `Deferred and descoped` in
`docs/wbs.md`): no published `custom_lint` supports `analyzer >=10`, which
`json_serializable`, `freezed` and `drift_dev` all require. Installing them
would mean downgrading `freezed_annotation` to `^2.2.0` and `uuid` to `^3.0.6`,
contradicting AD-03.

`memox-state-management-rules.yaml` is the replacement. The rule that matters
most is `memox.state_management.no_ref_read_in_build`: `ref.read` inside
`build()` reads without subscribing, so the widget silently stops updating. It
surfaces as "the data is stale" and is very hard to trace back to that line.

## Files

| File | Covers |
|---|---|
| `memox-architecture-rules.yaml` | Layer boundaries, AD-01 backend-readiness, AD-08 single connection site, deferred dependencies |
| `memox-state-management-rules.yaml` | Riverpod 3 usage — the riverpod_lint replacement |
| `memox-error-handling-rules.yaml` | Swallowed exceptions, `print`, Failure mapping |
| `memox-design-token-rules.yaml` | No raw colour / text style / spacing in product UI |
| `memox-i18n-rules.yaml` | No user-visible string outside ARB |
| `memox-data-model-rules.yaml` | BR-57 `COALESCE`, AD-06 clock injection, AD-11 stored state |
| `memox-privacy-rules.yaml` | Card content never logged, no secrets, app-private storage |
| `memox-naming-rules.yaml` | snake_case and role suffixes |
| `memox-testing-rules.yaml` | No skipped or focused tests |

## Scope discipline

Design-token and i18n rules run on `ui_surfaces` — `lib/features/*/presentation`
plus `lib/shared` — and deliberately **not** on:

- `lib/core/theme/**`, where raw values are legitimately *defined*; linting it
  would flag the definition as the crime
- `lib/app/**`, the dev-channel shell. `MobileFrameWidget`'s backdrop colour is
  a raw `Color(0xFF1E1E1E)` on purpose because it is not product UI, and says so
  in a comment.

## The `rule_without_targets` warnings are correct — do not silence them

Most of `lib/` does not exist yet: `lib/features/**` arrives at M3.1,
`lib/core/database` at M4.2, `lib/l10n` at M2.4. The engine reports every rule
pointing at those paths as `guard.config.rule_without_targets`, because a rule
matching no files silently checks nothing.

That diagnostic is the whole point — it is the same failure mode as the
`check_docs.sh` bug fixed in M2.1b, where a green tick covered 27 unchecked
tasks. So the profile gates on `error` only for now and leaves those warnings
visible as an accurate backlog. **M3.1 flips both profiles back to
`fail_on: [error, warning]`** once the tree exists.

## Adding a rule

1. Put it in the file whose domain it belongs to; keep the
   `memox.<domain>.<name>` id convention.
2. Prefer an existing scope over a per-rule `include:`.
3. Write the message so it says *why*, not just *what* — the message is the only
   thing the person who trips it will read.
4. **Fault-inject it.** Write a file that violates it, confirm the guard exits 1
   and names your rule, delete the file, confirm exit 0. A rule that has never
   fired is not known to work.
