# System State Current

Current version: `0.9.0`

Primary runtime: `repo_scaffold/app/server.py` (Python standard library).

Primary UI routes:

- `/` manager/owner dashboard
- `/employee` kiosk and guest sign-in

The owner route links to the employee kiosk but does not render employee punch or
guest sign-in controls. This keeps the shared kiosk surface separate from private
owner operations.

Source truth:

- Accepted employee clock events: append-only JSONL ledger
- Guest visits: separate guest JSONL ledger
- Operational query mirror: SQLite
- Human exports: generated CSV/JSON/Markdown/HTML files

Realtime decision: owner-token-authenticated WebSocket push on the companion local
port, with authenticated 15-second HTTP polling as fallback. The server remains
authoritative for employee and guest elapsed time.

The Timeclock Summary onsite roster has All, Employees, and Guests views. Employee
cards expose runtime identity/status details and an owner-audited clock-out action.
Guest cards expose a guest sign-out action that closes the separate visit record.

Owner reset controls are split deliberately:

- Reset Screen clears browser fields and rendered results without changing runtime data.
- Factory Reset requires the owner token on the server computer, the exact phrase
  `RESET BBTC`, and two confirmations. It creates and verifies a backup before
  clearing runtime employees, punches, guests, exports, and operational records.
  Owner security credentials, the verified backup, and packaged seed employees remain.
