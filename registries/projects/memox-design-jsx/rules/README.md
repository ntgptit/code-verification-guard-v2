# MemoX Design System (JSX) Guard Rule Registry

Rules of `code-verification-guard` for the **MemoX Design System** — the JSX / CSS
design kit under `docs/design/MemoX Design System`. Structured the same way as the
sibling `memox` ruleset: one file per domain, one stable id per rule.

This ruleset is the guard-engine counterpart of the design system's own oxlint
adherence config, `docs/design/MemoX Design System/_adherence.oxlintrc.json`. Where
the engine can express a check with regex / import / file-name matching, the rule
is reproduced here; AST-level checks that oxlint does (see "Known engine limits")
are documented but not reproduced.

## Invocation

```bash
python code-verification-guard/guard/run.py check --project . --ruleset memox-design-jsx
python code-verification-guard/guard/run.py check --project . --ruleset memox-design-jsx --debug   # print resolved load paths
python code-verification-guard/guard/run.py check --project . --ruleset memox-design-jsx --profile ci
```

`--project` is the repo root; all scope globs are repo-root-relative and target
`docs/design/MemoX Design System/**`.

## ID convention

```
mxds.<domain>.<rule_name>
```

- `mxds` is the namespace for this ruleset. The ruleset *name* is `memox-design-jsx`,
  but rule ids may not contain hyphens, so the short `mxds` (MemoX Design System,
  mirroring the `Mx*` component prefix) is used.
- `<domain>` matches the slug of the file holding the rule (`mxds-<domain>-rules.yaml`,
  `-` → `_`). Rules in `mxds-design-token-rules.yaml` are `mxds.design_token.*`.
- `<rule_name>` is snake_case and describes the behaviour: `no_raw_hex_color`,
  `component_file_mx_prefix`.

## Files by domain

| File | Domain | Enforces |
| --- | --- | --- |
| `mxds-design-token-rules.yaml` | `design_token` | Layer-1: no raw hex / px above the token layer — use `var(--memox-*)` |
| `mxds-component-contract-rules.yaml` | `component_contract` | Layer-2: import the Mx* family from the package index, not internal paths |
| `mxds-naming-rules.yaml` | `naming` | Frozen identifiers: `Mx*` PascalCase component files, PascalCase screen files |

## The three-layer model this guards

`Token → Component → Screen` (see the design system `readme.md`). Screens use only
components; components use only tokens; **no raw visual values above the token
layer**. The golden rule: *changing a value is free; changing a name or id breaks
the system* — which is why the naming rules are `error` and the token rules are
`warning` (values are tunable debt, names are contracts).

## Scopes

- The ruleset loads its scopes from `config/scopes.yaml`.
- That file **redefines the generic `common` scope names** (`project_files`,
  `source_files`, `text_source_files`, `all_text_files`, `source_and_config_files`)
  so the shared `common` hygiene rules selected in `guard-manifest.yaml` only scan
  `docs/design/MemoX Design System/**` — not the whole repo. The ruleset-local
  scope document is registered after the shared `common-scopes.yaml`, so the
  redefinitions win.
- Generated bundles (`_ds_bundle.js`, `_ds_manifest.json`) and runtime template
  helpers (`support.js`, `ds-base.js`) plus binary assets (`fonts/`, `screenshots/`,
  `uploads/`) are excluded at the scope level.
- Local `ds_*` scopes target the layers: `ds_components` (Mx* family),
  `ds_screens` (app screens, minus `kit-helpers.jsx`), `ds_jsx` (both).

## Severity policy

- `error`: blocks the gate. Used only where the kit is already clean and the rule
  is a hard contract (the `naming` rules).
- `warning`: existing intentional debt or forward-looking guards. The `design_token`
  rules are `warning` because the shipped kit carries a few deliberate raw literals
  (e.g. the `Theme.jsx` swatch palette), exactly as the upstream oxlint config flags
  them at `warn`; the `component_contract` import rule is `warning` because the kit
  composes via the global namespace and has no deep imports yet.

## Known engine limits (vs. the oxlint adherence config)

The upstream `_adherence.oxlintrc.json` also enforces **per-component prop
allowlists and variant enums** (e.g. `<MxButton variant>` ∈
`primary|secondary|outline|ghost|contrast`) via JSX-AST selectors. This guard
engine has only line/file regex, import, and file-name matchers — no JSX AST — so
those prop/variant checks are intentionally **not** reproduced here; run oxlint with
that config for full prop-level adherence. This registry covers the parts the
regex/import/file-name engine can verify reliably: raw-value bans, the import
contract, and file naming.

## Adding / changing a rule

1. Pick the domain file (create `mxds-<domain>-rules.yaml` with a header + `metadata`
   and register it in `guard-manifest.yaml` `rules:` if new).
2. Use a `mxds.<domain>.<rule_name>` id; never reuse an id for a new meaning.
3. YAML style: list items indent under their parent key (`rules:` → 2 spaces →
   `- id:`); the config loader rejects a list item at column 0. Quote regex
   patterns with single quotes so backslashes stay literal.
4. Do not edit a rule to relax one file — use `config/overrides.yaml`
   (`disabled_rules` / `severity` / `rule_options`).
5. Verify:
   ```bash
   python code-verification-guard/guard/run.py check --project . --ruleset memox-design-jsx --debug
   ```
