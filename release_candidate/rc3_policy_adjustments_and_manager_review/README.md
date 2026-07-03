# RC3 — Policy Adjustments and Manager Review

## Version

v0.4.0

## Mission

Add a bounded owner correction lane and manager review surface without mutating prior ledger events.

## Added

- Owner adjustment request contract.
- Manager review report contract.
- Owner adjustment runtime endpoint.
- Manager review runtime endpoint.
- Policy validation script.
- Frozen release-candidate roadmap.

## Acceptance

- Owner adjustment creates an append-only JSONL event.
- Manager review detects rejected events, adjustments, and calculation exceptions.
- Pay-period close includes a manager review report artifact.
- Runtime smoke proves adjustment + review path in a temporary app copy.

## Non-claims

No legal compliance seal, payroll integration, production security seal, AoS Boot Pod install, QEMU pass, rootfs materialization, or systemd activation is claimed.
