## v0.9.0 — arc_employee_management_kiosk_timeclock

- Added manager summary and employee lifecycle panels.
- Added active, inactive, and soft-removed employee states with restore.
- Added optional hourly-rate and tax-estimate fields plus audit-recorded manual hours.
- Added separate guest sign-in/out records, JSONL ledger, and guest CSV.
- Replaced raw employee CSV headers with human-readable session rows.
- Fixed Summary and Manage Employees button destinations.
- Added server-authoritative active-session state with 15-second polling timers.
- Added duplicate open-session and invalid-transition rejection.
- Added required contracts, docs, component/route surfaces, context records, and validation.
- No production, payroll compliance, tax compliance, or WebSocket/SSE runtime claim.

## v0.8.6 — rc7_6_employee_qr_entry_and_kiosk_fit

- Added dedicated employee portal at `/employee` with mobile-first layout.
- Added owner console Employee Kiosk Link / QR card and server-side SVG QR generation.
- Added `POST /api/employee/summary` for PIN-gated today-hours lookup without punching.
- Added `scripts/start_all.bat`, `scripts/start_all.sh`, and dev startup validation.
- Fixed backend static serving for `offline_queue.js`.
- Added local development library binding pattern and BBTC hardening arc-series record.
- Preserved prior runtime behavior, owner console, offline queue, and flow/status rails.
- No hosted adapter, production deployment, or compliance seal claimed.

## v0.8.5 — rc7_5_frontend_flow_graphics_status_language

- Added restrained frontend flow/status rails for employee, owner, and offline recovery workflows.
- Added read-only developer/Cursor onboarding entrypoint: `scripts/onboard_agent.py`.
- Added product-facing operator entrypoint: `scripts/start_here_user.py`.
- Added kickoff documentation and DOCX kickoff packaging support.
- Shortened external repo ZIP/root name to reduce Windows path-length risk.
- Preserved prior runtime behavior, offline queue, JSONL ledger, CSV mirror, owner console, and employee kiosk flows.
- No hosted adapter, production deployment, visual regression execution, or compliance seal claimed.

## v0.8.4 — Owner Console Operator Clarity

- Added `rc7_4_owner_console_operator_clarity` as the next full repo/package lane.
- Reorganized the owner console into a professional operator control panel with status grid, task rail, grouped cards, action summary, and card-level result hints.
- Added owner-token presence guard before owner actions to prevent silent unauthorized API calls from the UI.
- Hid technical owner JSON behind a closed details panel by default while keeping audit visibility.
- Preserved offline recovery as pending-owner-review evidence only.
- Added owner console operator-clarity contract, docs, save-state, release-candidate phase files, and validator.
- Preserved full v0.1.0 through v0.8.3 package state.
- Non-claims: no production deployment, hosted adapter, legal/payroll/cannabis compliance seal, visual regression execution, or release seal.


## v0.8.3 — Employee Kiosk Gold Path Polish

- Added `rc7_3_employee_kiosk_gold_path_polish` as the next full repo/package lane.
- Polished the employee kiosk screen into a clearer one-screen gold path: ID, PIN, action, receipt, today-hours, backend/offline state.
- Added dedicated today-hours and last-punch display cards outside the technical receipt JSON.
- Added frontend input guard so empty employee ID/PIN does not silently fall into backend or offline flows.
- Strengthened offline-pending language so recovery evidence is not confused with payroll truth.
- Added employee kiosk gold-path contract, docs, save-state, release-candidate phase files, and validator.
- Fixed detected drift: `repo_scaffold/app/server.py` had stale `APP_VERSION = "0.8.1"`; updated to `0.8.3`.
- Preserved full v0.1.0 through v0.8.2 package state.
- Non-claims: no production deployment, hosted adapter, legal/payroll/cannabis compliance seal, visual regression execution, or release seal.

## v0.8.2 — UI/UX Truth Lock and Component Inventory

- Added `rc7_2_ui_ux_truth_lock_and_component_inventory` as the next full repo/package lane.
- Added UI/UX component inventory, state contract, interaction contract, receipt contract, error-copy contract, mobile kiosk contract, and owner console contract.
- Added frontend save-state record for the UI truth-lock surface.
- Added UI/UX arc-series roadmap through `v0.9.0` professional UI shell candidate.
- Resolved next-phase drift by deferring Hugging Face adapter work and setting the next phase to employee kiosk gold-path polish.
- Preserved full v0.1.0 through v0.8.1 package state and runtime code.
- Non-claims: no visual regression execution, no production deployment, no hosted adapter, no compliance seal, and no release seal.

## v0.8.0 - Professional Release Readiness and Backend Connectivity Guard

- Added RC7 production installation readiness candidate folder with non-claim boundary.
- Added backend connection banner and file-preview warning for phone/tablet use.
- Added local-network kiosk launcher script.
- Added professional component blueprint contract pack.
- Added release-readiness validation scripts and reports.
- Preserved v0.1.0 through v0.7.1 package state.


## v0.7.1 - UI/UX hardening and operator clarity

- Added `rc6_1_ui_ux_hardening_and_operator_clarity` as an internal patch phase.
- Hardened employee kiosk screen with workflow strip, status strip, larger receipt copy, and local time display.
- Grouped owner dashboard actions into summary, exports, pay-period close, people/review, and backup/restore dry-run cards.
- Added frontend surface contracts for employee kiosk, owner dashboard, receipt states, and acceptance checklist.
- Added UI copy, accessibility static, and no-scope-expansion validators.
- Preserved all prior v0.1.0-v0.7.0 runtime, ledger, pay-period, backup, pilot, and context records.
- Non-claim: no production deployment, payroll-provider integration, legal seal, geofence/camera/biometric implementation, or vendor UI asset copying.


## v0.7.0 — rc6_live_pilot_acceptance_pack

- Added live pilot readiness report.
- Added pilot issue log and pilot sign-off receipts.
- Added owner-generated live pilot acceptance pack ZIP.
- Added owner UI panel for pilot readiness, issue logging, sign-off, and pack download.
- Added pilot schemas, docs, validation, runtime smoke checks, and context records.
- Preserved non-claims: no production deployment, no legal/payroll/cannabis compliance seal.

# Changelog

## v0.6.0 — Frontend surface + validation freeze candidate

- Added frontend surface contract pack.
- Rebuilt static UI into a more professional kiosk/dashboard experience.
- Added employee success notification after accepted clock in/out/break events.
- Added today-hours receipt payload and UI display.
- Added frontend surface validation script/report.
- Added RC5 frozen-candidate phase records.
- Preserved prior v0.1.0-v0.5.0 package state.


## v0.5.0 — RC4 backup restore and deployment operator hardening

- Added backup manifest generation and backup archive verification helpers.
- Added restore dry-run script that validates and extracts backups into disposable restore candidates.
- Added deployment preflight script for operator readiness checks.
- Added owner backup verification route and UI button.
- Added backup/restore and deployment contracts/schemas.
- Added `release_candidate/rc4_backup_restore_and_deployment_operator_hardening/`.
- Updated RC phase matrix and frozen release-candidate roadmap toward v0.6.0.
- Added context working-set update 0005, episode checkpoint 0005, ledger records, and resume pack update.
- Preserved all v0.1.0 through v0.4.0 records.

Non-claims: no production restore, production deployment, legal compliance seal, payroll-provider integration, AoS Boot Pod install, QEMU pass, rootfs materialization, or systemd activation is claimed.

## v0.4.0 — RC3 Policy Adjustments and Manager Review

- Added owner adjustment runtime lane.
- Added manager review runtime report.
- Added policy validation script.
- Added pay-period close `manager_review_report.json` artifact.
- Added frozen release-candidate roadmap.
- Preserved full v0.1.0, v0.2.0, and v0.3.0 package state.
- Removed generated Python cache files from the v0.4.0 output ZIP.

# Changelog

## v0.2.0 — Owner setup hardening and operator export runtime

### Added

- Authenticated owner summary flow.
- Owner dashboard date filters.
- Downloadable owner exports with constrained file serving.
- Owner employee list/create endpoint.
- Runtime status endpoint with setup warnings.
- Ledger hash-chain verification script.
- Runtime backup script for data directory preservation.
- Runtime smoke script using a temporary app copy.
- `rc1_owner_setup_hardening` release-candidate phase.
- New schemas for owner policy, employee administration, backup receipts, and ledger verification reports.
- Context Module update sequence 0002.

### Changed

- Simple UI expanded into an operator dashboard with owner token, date filters, export generation, export download, and employee add form.
- `repo_release_state.json`, `guide_pack.json`, `package.json`, capsule metadata, manifests, docs, validation reports, and cursor prompts updated to v0.2.0.

### Preserved

- v0.1.0 schemas, docs, context records, release state artifacts, validation report, capsule files, runtime scaffold, and RC0 folder.

### Non-claims

- No production security seal.
- No legal compliance seal.
- No payroll-provider integration.
- No biometric/geofence/camera identity proof.
- No AoS Boot Pod install, QEMU pass, rootfs materialization, or systemd activation.

---

## Prior history

# Changelog

## v0.2.0

Added full repo-shaped AoS capsule app with contracts, simple HTML UI, stdlib Python runtime, JSONL ledger, SQLite mirror, owner exports, context module update, and validation.

Non-claims are preserved in `docs/NON_CLAIMS.md`.



## v0.3.0 — 2026-05-29T00:28:30.046816+00:00

### Added

- Full repo/package bump from v0.2.0 to v0.3.0.
- RC2 internal phase: `rc2_pay_period_close_and_audit_exports`.
- Owner-token-gated pay-period close endpoint.
- Pay-period manifest, summaries, events, exceptions, CSV, HTML, Markdown, and ZIP archive generation.
- Pay-period list/download endpoints.
- UI controls for close/list/download closed periods.
- Validation and runtime smoke coverage for close-package creation.
- Context Module update 0003.

### Preserved

- v0.1.0 and v0.2.0 contracts, docs, scripts, reports, context, and release state.
- JSONL source-of-truth design.
- SQLite operational mirror posture.

### Non-claims

- No legal/payroll compliance seal.
- No production deployment.
- No biometric/geofence identity proof.


## v0.8.1 — Offline Timekeeper Reliability Patch

- Added browser-side offline recovery queue for backend interruptions.
- Added emergency pending queue JSONL/CSV downloads.
- Added `/api/offline/sync` backend route.
- Added server-side CSV ledger mirror after JSONL writes.
- Added offline sync receipts and owner receipt listing.
- Added offline/csv validation scripts.
- Deferred Hugging Face Space adapter to later adapter phase.

Non-claims: offline queue is not payroll truth, CSV is not source-of-truth, and no hosted deployment/HF adapter is included.
