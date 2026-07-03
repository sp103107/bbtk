# Live Clocked-In Status Transport

Version 0.9.0 uses owner-token-authenticated WebSocket push with authenticated HTTP
polling every 15 seconds as a fallback.

The HTTP server keeps its configured port and the WebSocket listener uses the next
local port. For the default HTTP port `8080`, owner live updates use `8081`. The client
sends the owner token as its first WebSocket message so the token does not appear in
the connection URL.

The server reconstructs active employee and guest sessions and returns authoritative
start timestamps and elapsed seconds. Kiosk mutations broadcast a unified roster
immediately. If the WebSocket disconnects, the owner console displays `Polling
fallback` and continues authenticated HTTP refreshes.
