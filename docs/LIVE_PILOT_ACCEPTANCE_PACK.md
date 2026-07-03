# Live Pilot Acceptance Pack — v0.7.0

## Purpose

This bump adds the controlled pre-production pilot lane for the Best Buds Time Clock capsule. The goal is to let the owner test the runtime with real operators while preserving audit discipline, issue capture, and explicit non-claims.

## Added surfaces

- `/api/owner/pilot/readiness`
- `/api/owner/pilot/issue`
- `/api/owner/pilot/signoff`
- `/api/owner/pilot/package`
- `/api/owner/pilot/download`

## Acceptance posture

The pilot may be considered usable only when:

1. Active employees are configured.
2. Default owner token and PIN pepper are changed before real use.
3. A backup is created and verified.
4. The owner reviews the pilot readiness report.
5. Any blocking issue is resolved or the pilot is deferred.
6. The owner records a sign-off receipt.

## Non-claims

- This is not a production deployment seal.
- This is not legal, payroll, or cannabis regulatory compliance certification.
- This does not install into AoS Boot Pod, QEMU, rootfs, or systemd.
