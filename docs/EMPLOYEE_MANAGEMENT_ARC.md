# Employee Management Arc

Version 0.9.0 adds a real manager employee panel backed by the SQLite operational
mirror and audit receipts.

- Active employees can use the kiosk.
- Inactive employees cannot punch but may be restored.
- Removed employees are soft-deleted with `removed_at_utc`; they remain in manager
  history and all historical ledger/export joins.
- Editing supports display name, role, optional hourly rate, and optional tax-estimate
  fields. A blank PIN preserves the existing PIN.
- Manual hours adjustments are separate audit records. They do not rewrite raw clock
  events.

Hourly rate, gross pay, tax withholding, and net pay values are estimates only.
