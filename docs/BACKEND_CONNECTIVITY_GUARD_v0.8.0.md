# Backend Connectivity Guard — v0.8.0

## Problem

A user can open `index.html` directly on a phone and see the UI, but buttons require backend routes such as `/api/clock` and `/api/health`.

## Fix

The frontend now performs a backend health check and displays a clear banner when the backend is unavailable or the page is opened with `file://`.

## Acceptance

- Backend online shows a connected runtime state.
- Backend unavailable shows an actionable warning.
- Punch fetch failures return a clear receipt/error payload.
- The UI tells the operator to start the Python server and open the local network URL.
