# Summary and Manage Employees Button Fix

The Summary endpoint now returns `ok: true` plus selected-range totals, completed
session count, active sessions, total hours, and export route hints. The Summary button
renders and scrolls to `#timeclock_summary_panel`.

Manage Employees now loads all employee lifecycle states into
`#employee_management_panel`. It no longer acts as a raw JSON-only list button.
