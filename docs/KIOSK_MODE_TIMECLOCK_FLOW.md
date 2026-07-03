# Kiosk Mode Timeclock Flow

The dedicated `/employee` route is the kiosk surface. It exposes employee clock
in/out, break controls, today-hours lookup, and a separate guest sign-in panel.
Manager controls and owner credentials are not rendered there.

The `/` route is the owner/operator console. It does not render kiosk controls.
A prominent **Open Employee Kiosk** link opens `/employee`, keeping shared-device
actions separate from private owner operations.

The server rejects duplicate open sessions and invalid state transitions. Accepted raw
events remain in the JSONL clock ledger; SQLite is the operational mirror.

The kiosk uses ordinary HTTP and remains functional without WebSockets or SSE.
