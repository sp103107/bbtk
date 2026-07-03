# Onboarding Program (`scripts/onboard_bbtc.py`)

A single onboarding program for the Best Buds Time Clock app that serves both a human
operator and an LLM agent. It guides setup, then proves the app actually works by
exercising the full clock lifecycle against a live, throwaway server instance.

## Why this exists

`scripts/onboard_agent.py` (agent, read-only) and `scripts/start_here_user.py` (operator)
print guidance but never touch a running server. `onboard_bbtc.py` adds a **guided + live**
path: it checks the environment, surfaces the one real setup step, and then runs an
end-to-end punch lifecycle so a new operator (or an agent) gets proof the system works.

## How to run

```bash
# Interactive human walkthrough (offers to run live verification)
python scripts/onboard_bbtc.py

# Machine-readable JSON for an LLM agent (no prompts)
python scripts/onboard_bbtc.py --json
python scripts/onboard_bbtc.py --agent      # alias of --json

# Informational only - skip the live server check
python scripts/onboard_bbtc.py --no-live

# Options
python scripts/onboard_bbtc.py --port 0 --timeout 10 --yes
python scripts/onboard_bbtc.py --owner-token YOUR_TOKEN   # also checks an owner endpoint
```

## Modes

- **Default (human):** readable, phase-by-phase output. In an interactive terminal it
  asks whether to run live verification; answer `n` to skip it.
- **`--agent` / `--json`:** emits one canonical JSON object
  (`json.dumps(..., indent=2, sort_keys=True)`); no prompts.
- **`--no-live`:** skips the live phase; useful where starting a server is not desired.
- **`--yes`:** run live verification without the interactive prompt.

## Phases

1. **environment_check** - Python version (3.9+ required, 3.11+ recommended) and presence
   of required files (`repo_scaffold/app/server.py`, `config/settings.json`,
   `config/employees.seed.json`, `scripts/start_kiosk_server.py`, `VERSION`).
2. **config_check** - loads `repo_scaffold/app/config/settings.json` and warns if
   `owner_token` / `pin_pepper` are still the defaults (the one true setup step). Advisory,
   not a hard failure. Surfaces site name, timezone, and `min_pin_length`.
3. **live_verification** - copies the app into a temp directory (excluding `data/`),
   starts the server on `127.0.0.1` on a free port, then over HTTP:
   `GET /api/health` -> `clock_in` -> `break_start` -> `break_end` -> `clock_out` ->
   `POST /api/employee/summary` -> a bad-PIN punch that must be rejected. Uses the seed
   employee `emp_001` / PIN `1234`. The temp copy is removed afterward, so the operator's
   real ledger is never touched.
4. **next_steps** - the operator gold path: change the two secrets, start the real server,
   open the owner console (`/`) and employee portal (`/employee`).

## Output shape (agent mode)

```json
{
  "program": "scripts/onboard_bbtc.py",
  "version": "0.8.6",
  "overall_status": "pass",
  "phases": [ { "phase": "environment_check", "status": "pass", "...": "..." } ],
  "next_steps": ["..."],
  "non_claims": ["..."]
}
```

`overall_status` is `pass` when `environment_check` passes, `config_check` is `pass`/`warn`,
and `live_verification` is `pass`/`skipped`. Exit code is `0` on pass, `1` on fail.

## Boundaries / non-claims

- Additive only: does not modify `server.py` domain logic and adds no third-party deps.
- Live verification uses a temporary app copy only; the real runtime ledger is untouched.
- No production deployment, hosting, payroll-provider, or compliance claim.

## Related ARC blueprint (training material, untracked)

This program was planned with an ARC-launcher-style blueprint stack under
`_arc_blueprints_tmp/bbtc_onboarding_arc/` (gitignored, kept locally as ARC evolution
training material; never written into the ARC launcher repo).
