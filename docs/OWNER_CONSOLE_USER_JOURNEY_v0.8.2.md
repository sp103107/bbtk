# Owner Console User Journey v0.8.2

## Standard owner path

```text
Enter owner token
↓
Review Today summary
↓
Check exceptions/offline sync receipts
↓
Generate export if needed
↓
Close pay period when ready
↓
Download closed package
↓
Backup and verify data
```

## Required operator clarity

Every owner action should show:

- success/fail banner
- file link if generated
- next recommended action
- technical JSON only under details

## Boundary

Owner console hardening does not claim production RBAC, payroll-provider submission, or compliance certification.
