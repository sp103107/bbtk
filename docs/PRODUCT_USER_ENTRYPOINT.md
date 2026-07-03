# Product User Entrypoint — v0.8.5

## Purpose

`scripts/start_here_user.py` is the product-facing meta entrypoint for a normal owner/operator after the ZIP is loaded and unzipped.

This is separate from the developer agent onboarding path.

## Command

```bash
python scripts/start_here_user.py
```

Machine-readable mode:

```bash
python scripts/start_here_user.py --json
```

## What it explains

- where to unzip the repo using a short Windows path
- how to start the local backend
- how to open the time clock from a phone/tablet
- employee punch flow
- owner console flow
- offline recovery rule
- product boundaries and non-claims

## Recommended Windows path

```text
C:\bbtc\bbtc_v0_8_5
```

## Start backend

```bash
python scripts/start_kiosk_server.py --host 0.0.0.0 --port 8080
```

## What it does not do

- does not start the backend automatically
- does not edit repo files
- does not claim hosted deployment
- does not claim payroll-provider integration
- does not claim legal/payroll/cannabis compliance certification

## Validation

```bash
python scripts/validate_product_user_entrypoint.py
```
