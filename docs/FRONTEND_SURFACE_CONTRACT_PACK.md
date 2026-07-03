# Frontend Surface Contract Pack — v0.6.0

## Purpose

This pack governs the static web UI for the Best Buds Time Clock Capsule. The UI is not treated as decoration only; it is a typed surface with required states, required outputs, and acceptance checks.

## Contract files

- `contracts/frontend_surface/frontend_surface_contract.v0.6.0.json`
- `contracts/frontend_surface/employee_punch_receipt.surface.v0.6.0.json`
- `contracts/frontend_surface/ui_screen_map.v0.6.0.json`
- `contracts/frontend_surface/visual_design_tokens.v0.6.0.json`
- `contracts/schemas/frontend_surface_contract.schema.json`
- `contracts/schemas/employee_punch_receipt.schema.json`
- `contracts/schemas/employee_day_summary.schema.json`

## Required employee UX behavior

After every accepted punch, the employee station must show a visible receipt panel with:

1. accepted action label,
2. clear success message,
3. today net hours,
4. current clock state,
5. local captured time,
6. technical JSON receipt available under a disclosure panel.

Rejected punches must show a visible error state and must not pretend a punch succeeded.

## Non-claims

The frontend receipt is not payroll approval, not biometric proof, not geofence proof, and not legal compliance certification.
