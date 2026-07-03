# Agent Onboarding Entrypoint — v0.8.5

## Purpose

`scripts/onboard_agent.py` is the canonical read-only onboarding entrypoint for Cursor or another developer agent.

It prints the current repo version, current phase, next phase, source-of-truth files, safe validation commands, and non-claim boundaries.

## Command

```bash
python scripts/onboard_agent.py
```

Machine-readable mode:

```bash
python scripts/onboard_agent.py --json
```

## What it does

- reads `VERSION` and `repo_release_state.json`
- identifies `current_internal_phase` and `next_internal_phase`
- lists source-of-truth files
- lists validation commands
- lists non-claims
- warns if required high-level paths are missing

## What it does not do

- does not edit files
- does not start the backend server
- does not make network calls
- does not claim runtime pass or deployment readiness
- does not bypass the continuation workflow

## Validation

```bash
python scripts/validate_agent_onboarding_entrypoint.py
```

## Next agent command

```text
continue rc7_6_accessibility_mobile_and_kiosk_fit_finish
```
