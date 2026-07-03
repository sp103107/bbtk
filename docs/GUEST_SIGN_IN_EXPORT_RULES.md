# Guest Sign-In and Export Rules

Guest visits use `guest_sessions` and a separate guest JSONL ledger. They never enter
employee time events or employee payroll/time CSV files.

The guest CSV columns are: Guest Name, Organization, Purpose, Sign In, Sign Out, Visit
Duration, and Notes. Open visits display `OPEN`. Creating a new guest export never
overwrites an earlier export.
