# CSV Ledger Mirror — v0.8.1

The backend now writes an owner-readable CSV mirror after the canonical JSONL ledger write.

## Ordering

1. JSONL ledger write.
2. CSV mirror append.
3. SQLite accepted-event mirror when applicable.

If the CSV mirror fails, the JSONL event remains the canonical record and a mirror warning is attached where possible.

## Non-claim

CSV is a recovery/export convenience, not source-of-truth.
