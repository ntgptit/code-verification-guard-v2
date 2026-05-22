# AGENTS.md

## Project

This project is `code-verification-guard`, a portable YAML-first code standards verification tool.

Its purpose is to check a project's code and block or report patterns that the project owner or manager has defined as bad for that project. It helps make users, Codex, Claude, and other coding agents follow the project's declared rules, including coding standards, architecture boundaries, and workflow constraints.

Keep the Python engine generic. Concrete rules belong in YAML unless a new generic matcher, reporter, resource loader, CLI command, or validation capability is needed.

## Repository Boundary

- This directory is its own Git repository even when vendored inside `D:\workspace_STS_5\memox`.
- Commit and push guard changes from this directory, not from the parent MemoX repository.
- Expected remote: `https://github.com/ntgptit/code-verification-guard-v2.git`.
- The parent MemoX repository should only commit project-level guard config such as `code-verification-guard.yaml` and `code-verification-guard-scopes.yaml`.
- Do not ask the parent MemoX repository to stage or commit files under `code-verification-guard/**` unless the user explicitly requests submodule work.

## References

Read only when the task touches that area:

- Core architecture: `docs/agent-architecture.md`
- YAML rules/scopes/profiles: `docs/agent-yaml-contract.md`
- Source distribution/resource behavior: `docs/agent-packaging.md`
- Extended verification gates: `docs/agent-verification.md`

## Default Check

For normal changes, run:

```powershell
python guard\run.py check --project .
```

Expected success:

```text
Code verification passed.
No violations found.
```

## Completion Report

Report:

1. Files changed
2. Command run
3. Result
4. Remaining risk
