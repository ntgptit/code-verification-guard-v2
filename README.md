# Code Verification Guard

Code Verification Guard is a manifest-driven static rule runner for checking a
project's code against the rules defined by the project owner or manager.

It is intended to act as a guardrail for user, Codex, Claude, or other agent
changes: it detects project-specific bad patterns, reports violations, and helps
enforce the coding standards, architecture boundaries, and workflow rules that
the project manager has decided the project must follow.

Run against the current project from a vendored source copy:

```powershell
python guard\run.py check --project .
```

The tool is intended to be copied into a project as source. Built-in YAML
resources are loaded only from the source tree:

- `guard-manifest.yaml`
- `profiles/`
- `scopes/`
- `registries/`

YAML templates are available in `templates/`. Use them when adding new project
configs, profiles, scopes, registries, or manifest rule-set entries so new
rules keep the repository's expected YAML format.
