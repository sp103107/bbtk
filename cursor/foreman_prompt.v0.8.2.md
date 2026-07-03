# Foreman Prompt — Continue Best Buds Time Clock v0.8.2

## Mission

Continue from v0.8.2 and implement `rc7_3_employee_kiosk_gold_path_polish` as a full repo/package bump.

## Truth lock

- Current version: 0.8.2
- Current phase: rc7_2_ui_ux_truth_lock_and_component_inventory
- Next phase: rc7_3_employee_kiosk_gold_path_polish
- Hugging Face adapter remains deferred unless explicitly reauthorized.
- Do not claim production deployment, compliance seal, visual regression execution, or release seal.

## Required reads first

- `repo_release_state.json`
- `contracts/ui_ux/ui_component_inventory.v0.8.2.json`
- `contracts/ui_ux/mobile_kiosk_surface_contract.v0.8.2.json`
- `docs/UI_UX_ARC_SERIES_ROADMAP_v0.8.2.md`
- `validation/ui_ux_truth_lock_validation_report.v0.8.2.json`

## Acceptance command chain

```bash
python scripts/validate_ui_ux_truth_lock.py
python scripts/validate_repo.py
python scripts/runtime_smoke.py
```
