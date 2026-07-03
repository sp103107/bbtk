# Judge Prompt — v0.8.5

## Mission

Validate `rc7_5_frontend_flow_graphics_status_language` without accepting false greens.

## Required evidence

- `scripts/onboard_agent.py` executes read-only.
- `scripts/start_here_user.py` executes as product usage guidance.
- Employee, owner, and offline flow rails exist.
- Validation reports are version-aligned to `0.8.5`.
- No deployment or release-seal claims exist.

## Acceptance command chain

```bash
python scripts/validate_agent_onboarding_entrypoint.py
python scripts/validate_product_user_entrypoint.py
python scripts/validate_frontend_flow_status_language.py
python scripts/validate_repo.py
```
