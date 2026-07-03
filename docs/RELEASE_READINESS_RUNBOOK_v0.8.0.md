# Release Readiness Runbook — v0.8.0

## Purpose

This runbook prepares the app for a controlled local pilot or operator review. It is not a production deployment seal.

## Required command chain

```bash
python scripts/validate_repo.py
python scripts/runtime_smoke.py
python scripts/validate_frontend_surface.py
python scripts/validate_backend_connectivity_guard.py
python scripts/validate_professional_blueprint.py
python scripts/deployment_preflight.py
python scripts/validate_release_readiness.py
```

## Required operator actions before real use

1. Change `CHANGE_ME_OWNER_TOKEN` in `repo_scaffold/app/config/settings.json`.
2. Change `CHANGE_ME_PIN_PEPPER` in `repo_scaffold/app/config/settings.json`.
3. Run deployment preflight again.
4. Start the backend with `python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080`.
5. Open `/api/health` from the phone/tablet before the first employee punch.
6. Create a backup and run restore dry-run before relying on the system.

## Non-claims

This package does not claim legal compliance, production deployment, payroll-provider integration, or cannabis compliance certification.
