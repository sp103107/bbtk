# Employee QR Entry Portal — v0.8.6

## Employee link

After the owner starts the backend:

```text
http://COMPUTER-IP:8080/employee
```

Employees can also open the link from the owner console QR card on the same Wi-Fi network.

## Employee flow

1. Open the employee link or scan the QR code.
2. Enter Employee ID and PIN.
3. Tap **View Today's Hours** or choose a punch action.
4. Wait for the receipt before stepping away.

## Owner flow

1. Start the backend:

```bash
python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080
```

Or on Windows for local review:

```bat
scripts\start_all.bat
```

2. Open the owner console at `/`.
3. Use **Employee Kiosk Link / QR** to copy or print the employee entry URL.

## API

`POST /api/employee/summary`

```json
{ "employee_id": "emp_001", "pin": "1234" }
```

Returns today hours and last punch after PIN validation.

## Non-claims

- LAN/local-network entry only.
- QR does not prove identity.
- Today hours are runtime-calculated evidence, not payroll approval.
- No hosted deployment or production seal.
