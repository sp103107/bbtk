# UI/UX Hardening v0.7.1

## Mission

Harden the existing Best Buds time clock UI without expanding product scope.

## Research-derived patterns applied

- Shared tablet/kiosk posture.
- PIN-based employee identity.
- Large one-tap punch actions.
- Immediate success or rejection receipt.
- Today-hours metric visible after punch.
- Owner dashboard grouped by task.
- Technical JSON hidden behind disclosure blocks.

## Non-scope expansion guard

This bump does not add payroll-provider integration, geofence/GPS, camera/selfie capture, biometric identity, native mobile app, or production deployment.

## Acceptance

The UI passes if an employee can see a clear success notification and today's hours after a punch, and the owner can find existing actions without reading raw JSON first.
