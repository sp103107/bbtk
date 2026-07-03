# Export File Formats — v0.3.0

## Live exports

Live exports remain available from the owner dashboard:

- CSV
- JSON
- Markdown
- HTML

These are ad-hoc outputs.

## Closed pay-period package

Closed periods produce a package with:

- `pay_period_manifest.json` — close metadata, hashes, totals, non-claims
- `summaries.json` — calculated employee summaries
- `accepted_events.json` — accepted source events used for the close
- `exceptions.json` — clock sequence exceptions
- `payroll_summary.csv` — owner/payroll-friendly table
- `payroll_summary.html` — browser-readable table
- `owner_review.md` — scan-friendly owner review report
- `<period_id>.zip` — package archive for handoff

## Recommended owner workflow

Use live exports for review during a period. Use closed packages for pay-period handoff.
