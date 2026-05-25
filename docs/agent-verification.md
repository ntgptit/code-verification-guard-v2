# Agent Verification Notes

## Default Check

For MemoX ruleset verification, run from the MemoX repository root:

```powershell
python code-verification-guard\guard\run.py check --project . --ruleset memox
```

The expected success output includes:

```text
Code verification passed.
No violations found.
```

## Extended Gates

When Python code changes, also run:

```powershell
pytest -q
python -m compileall -q code_verification_guard
```

When source archive behavior changes, also run the zip creation path:

```powershell
python scripts\create_zip.py . code-verification-guard.zip
```

## Guard Self-Check Policy

This project must pass its own guard.

Do not weaken rules just to make self-check pass. If a rule produces a false positive, improve the rule, matcher, scope, or exclude strategy properly.

Do not disable a rule unless there is a strong architectural reason.
