# Policy Adjustments and Manager Review — v0.4.0

## Purpose

This bump adds a controlled owner adjustment lane for missed/corrected punches and a manager review report for rejected punches, calculation exceptions, and owner-created adjustments.

## Runtime surfaces

- `GET /api/owner/review`
- `POST /api/owner/adjustment`

Both routes are owner-token gated. The adjustment lane does not silently rewrite old records. It appends a new audit-marked accepted event into the JSONL ledger with:

- `source = owner_adjustment`
- `auth_method = owner_token`
- `admin_adjustment = true`
- `policy_flags = ["owner_adjustment", "requires_owner_review"]`
- `owner_adjustment_id`
- hash-chain fields

## Manager review checks

The review report surfaces:

- accepted event count
- rejected event count
- owner adjustment count
- calculation exceptions
- source ledger hash
- recommended owner actions

## Non-claims

- This is not a legal compliance seal.
- This is not payroll-provider integration.
- This is not biometric/geofence proof.
- Owner corrections require human review before payroll reliance.
