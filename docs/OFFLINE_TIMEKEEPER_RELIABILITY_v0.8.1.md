# Offline Timekeeper Reliability — v0.8.1

## Mission

Add a backend-interruption safety layer for phone/tablet kiosk use.

## Runtime behavior

- Normal online punch: frontend -> `/api/clock` -> JSONL canonical ledger -> CSV mirror -> SQLite accepted-event mirror.
- Backend interruption: browser saves an offline recovery item locally without persisting PIN.
- Reconnect/sync: browser posts pending items to `/api/offline/sync`.
- Synced offline items enter the JSONL ledger as `offline_recovery_pending_owner_review`.

## Truth boundary

Offline browser queue items are recovery evidence only. They are not payroll-counted accepted time until owner review/correction creates an accepted adjustment or the event is otherwise validated in a future authorized lane.

## Owner action

Owners should review offline sync receipts before payroll close. If an offline punch is legitimate, use the existing owner adjustment workflow so the payroll-counted record is explicit and auditable.

## Non-claims

- No Hugging Face Space adapter in this bump.
- No hosted deployment claim.
- No legal/payroll compliance seal.
- CSV is not source-of-truth.
