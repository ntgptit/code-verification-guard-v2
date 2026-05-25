# Agent Architecture Notes

## Distribution Model

The tool is source-only and vendored into the project that wants to use it. It
does not keep a packaged copy of built-in YAML resources under
`code_verification_guard/`, and it does not support a separate installed-package
resource mode.

The source tree supports ruleset-local YAML sources of truth:

```text
registries/projects/<ruleset>/
  guard-manifest.yaml
  config/
  rules/
```

`--project` selects the scan root. `--ruleset` selects the policy bundle under
`registries/projects/<ruleset>`. Ruleset manifest paths resolve relative to the
ruleset root, while file scanning always runs against the project root.

Ruleset manifests may select shared bundles from the root `guard-manifest.yaml`
with `rule_sets`. Keep project-owned registry files under
`registries/projects/<ruleset>/rules/`; do not copy common or language
registries into that folder.

## Core Flow

The architecture must remain:

```text
Vendored Source Root
        |
Ruleset Manifest
        |
Ruleset Config / Rules
        |
Project Scan Root
        |
Ruleset Profile Selection
        |
Scope Registry
        |
Rule Registry
        |
Profile Config
        |
Overrides
        |
RuleRegistry
        |
RuleFactory
        |
GenericRule
        |
MatcherFactory / MatcherRegistry
        |
Reporter
```

The engine must not know concrete rules. Python core code should only know how
to load project config, resolve root YAML resources, register
scopes/rules/matchers, execute matchers, report violations, and return the
correct exit code.

Do not introduce a second YAML source under the package code. Root YAML files
are edited directly and do not require a sync step.

## Registry Rules

`RuleRegistry`, `ScopeRegistry`, and `MatcherRegistry` are runtime registries. They should be singleton-style registries or app-level single runtime instances.

Registries must:

- detect duplicate IDs
- support clear/reset for tests
- avoid dirty state between test cases
- avoid silently overwriting existing IDs

Do not use singleton for individual matcher instances, `GenericRule` instances, `RuleRunner`, or reporters.

## Factory And Matcher Rules

Rule execution must go through:

```text
RuleFactory
GenericRule
MatcherFactory
MatcherRegistry
Matcher
```

Do not create one Python class per YAML rule. Only create a new matcher class when a new rule type cannot be expressed by existing matchers.

Generic matcher types such as `regex`, `file_name`, `max_lines`, and `forbidden_import` should remain generic.

## Constants And Style

Do not introduce magic strings or magic numbers in Python code. Use constants/enums for config keys, YAML keys, severity values, rule types, matcher types, report formats, default paths, default thresholds, and exit codes.

Prefer small focused changes, clear names, early returns, and fail-fast validation. Do not rewrite the whole tool unless explicitly requested.

Do not swallow exceptions silently. Error messages should explain what failed, which file failed, which rule/config caused the failure, and how to fix it when possible.
