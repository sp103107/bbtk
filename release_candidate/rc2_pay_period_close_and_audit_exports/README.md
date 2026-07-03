# RC2 — Pay Period Close and Audit Exports

## Mission

Add a deterministic owner close workflow for payroll periods.

## Added surfaces

- `POST /api/owner/pay_period/close`
- `GET /api/owner/pay_periods`
- `GET /api/owner/pay_period/download`

## Acceptance evidence

- Runtime smoke creates a temporary clock sequence.
- Runtime smoke closes a pay period.
- Runtime smoke confirms generated manifest, ZIP, summaries, and exception files.
- Repo validation confirms full repo packaging and no RC-only external ZIP.

## Non-claims

This phase does not claim payroll legal compliance, production deployment, or identity proof.
