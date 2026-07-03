# Frontend Acceptance Runbook v0.7.1

## Commands

```bash
python scripts/validate_frontend_surface.py
python scripts/validate_ui_copy.py
python scripts/validate_accessibility_static.py
python scripts/validate_no_scope_expansion.py
python scripts/runtime_smoke.py
python scripts/validate_repo.py
```

## Human checks

1. Employee can identify where to enter ID and PIN.
2. Employee can identify all punch actions without explanation.
3. Employee sees a success receipt with today hours after accepted punch.
4. Employee sees friendly error copy on failed punch.
5. Owner dashboard is grouped by task.
6. Export and pay-period download links appear near their action.
7. Technical JSON is not the main employee experience.
