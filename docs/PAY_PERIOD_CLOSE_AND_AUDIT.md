# Pay Period Close and Audit Package — v0.3.0

## Purpose

v0.3.0 adds an owner-token-gated pay-period close lane. The lane converts accepted JSONL clock events into a closed owner review package.

## Source of truth

The source of truth remains the append-only JSONL clock event ledger. SQLite is still only an operational mirror.

## Close output

Each close writes a folder under:

```text
data/pay_periods/<year>/<period_id>/
```

Required files:

```text
pay_period_manifest.json
summaries.json
accepted_events.json
exceptions.json
payroll_summary.csv
payroll_summary.html
owner_review.md
<period_id>.zip
```

## Owner review posture

The package is designed for owner review before payroll submission. It is not a legal compliance seal and does not replace wage-law review, payroll policy review, or accountant review.

## Hash posture

The manifest records the source ledger hash and per-file hashes for the generated close artifacts. A ZIP archive is also generated for handoff.
