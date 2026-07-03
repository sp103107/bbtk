# Employee Kiosk State and Receipt Copy v0.8.3

## Required visible states

- Ready: employee sees ID/PIN/action instructions.
- Pending: employee sees that the punch is being submitted and should not tap repeatedly.
- Success: receipt states the accepted action, local time, today's hours, and current status.
- Rejected: receipt gives a plain-language reason and next action.
- Offline saved: receipt says the punch is saved locally as recovery evidence, pending sync and owner review.

## Copy boundary

Do not use words that imply payroll approval for a normal punch receipt. A receipt is acknowledgement only.
