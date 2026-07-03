# UI/UX Polished Experience — v0.6.0

## Operator goal

Make the kiosk obvious for employees and keep owner tools separated from employee punch flow.

## Employee station

- Large touch targets for clock actions.
- Plain success/error receipt.
- Today hours are shown directly in the page after clock-in, clock-out, break start, and break end.
- Technical JSON is available but hidden behind a details disclosure to reduce visual noise.

## Owner dashboard

- Owner token is visually separated.
- Pay-period close, exports, manager review, backups, and employee setup are grouped as owner commands.
- Download links render only after an export or pay-period package exists.

## Accessibility and clarity

- Inputs use labels.
- Employee receipt uses `aria-live`.
- Buttons remain native buttons for keyboard/touch compatibility.
- Mobile layout collapses to one column.

## Boundary

This is still a static HTML/CSS/JS scaffold served by the stdlib Python runtime. No production auth hardening or payroll-provider integration is claimed.
