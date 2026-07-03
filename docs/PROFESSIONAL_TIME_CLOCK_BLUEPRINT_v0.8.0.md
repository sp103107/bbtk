# Professional Time Clock Blueprint — v0.8.0

## Mission

Define the professional application standard for the Best Buds Time Clock capsule without claiming production deployment.

## Component lanes

- Employee kiosk
- Owner dashboard
- Employee registry
- Time event ledger
- Timecard calculation engine
- Exception review
- Owner adjustments
- Pay-period close
- Payroll/export outputs
- Security and access
- Terminal/device posture
- Backup/restore
- Frontend design system
- Release readiness validation

## Current posture

The package remains a standalone Python stdlib runtime with a static HTML/CSS/JS frontend. JSONL remains the source-of-truth ledger. SQLite remains an operational mirror.

## v0.8.0 hardening

- Added backend connectivity guard so buttons do not appear silently broken when `index.html` is opened directly.
- Added local-network kiosk launcher for phones/tablets.
- Added release-readiness contracts and validation scripts.
- Added professional component map for future hardening.

## Non-claims

- No production deployment is claimed.
- No legal compliance seal is claimed.
- No payroll-provider integration is claimed.
- No cannabis compliance certification is claimed.
