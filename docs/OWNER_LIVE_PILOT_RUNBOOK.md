# Owner Live Pilot Runbook

## Before pilot use

- Change `owner_token` in `repo_scaffold/app/config/settings.json`.
- Change `pin_pepper`.
- Confirm active employees and PINs.
- Run `python scripts/runtime_smoke.py`.
- Run `python scripts/deployment_preflight.py`.
- Create and verify a backup.
- Run `python scripts/live_pilot_readiness.py`.

## During pilot

- Use the web UI pilot panel to log issues.
- Do not edit raw JSONL ledger files.
- Use owner adjustment only for reviewed missed punches.

## After pilot

- Record pilot sign-off or defer.
- Create the pilot acceptance pack ZIP.
- Close the first pay period only after manager review.
