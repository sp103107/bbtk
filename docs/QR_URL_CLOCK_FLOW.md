# QR / URL Clock Flow — v0.8.6

## Employee entry

Use the owner-generated employee URL or QR code to open:

```text
/employee
```

The employee-only page supports:

- PIN-gated today-hours lookup
- clock in / out / break actions
- offline recovery evidence when the backend drops

## Security boundary

- The QR code or URL opens the employee portal only.
- PIN is still required for hours lookup and punches.
- QR does not prove identity, geolocation, or device trust.

## Owner responsibilities

- Start the Python backend on the local network.
- Share the LAN URL or QR from the owner console card.
- Do not publish the employee URL to the public internet in this package lane.

## Non-claims

- No hosted adapter.
- No production deployment.
- No payroll or compliance seal.
