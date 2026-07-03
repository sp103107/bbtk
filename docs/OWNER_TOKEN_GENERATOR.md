# Guided Owner Token Setup

BBTC now generates and saves the owner token from the owner console. The owner no
longer needs to edit `settings.json`.

## First-time setup

1. Start BBTC on the server computer.
2. Open the owner console on that same computer.
3. Select **Generate & Save Secure Token**.
4. BBTC creates the owner token and the first 10 single-use recovery tokens together.
5. Select **Download Private Recovery File** and store that file safely.
6. Keep both the owner token and recovery file private.

First-time generation is accepted only from the computer running BBTC while the default
token is still configured. Both `127.0.0.1` and that computer's own LAN interface
addresses are recognized. A phone or another computer on the local network cannot claim
first-time setup.

## Rotation

After setup, enter the current owner token and select **Rotate & Save New Token**.
The old token stops working immediately. BBTC returns the new token once and does not
provide an API for retrieving an existing token.

The browser does not save the owner token in local or session storage. The generated
token remains in the current page only until it is refreshed or closed.

## Backup tokens

The first recovery set is created during initial owner-token setup. Afterward, select
**Generate New Set of 10** whenever a replacement set is needed.

- BBTC stores only SHA-256 hashes of backup tokens.
- Plaintext backup tokens are shown once.
- Generating a new set atomically replaces and invalidates the entire previous set.
- One backup token can recover owner access by creating a new owner token.
- A redeemed backup token is marked used and cannot be used again.
- The other nine unused tokens remain available after one recovery.

Recovery does not require the forgotten owner token. It does require possession of one
unused high-entropy backup token, so the backup file must be stored privately.

Named users and role-based permissions for time adjustments, employee administration,
and assisted clock-in are intentionally reserved for the next security phase.

## Maintainer validation

```bash
python scripts/validate_owner_token_generator.py
python scripts/runtime_smoke.py
python scripts/validate_repo.py
```

The focused validator copies the app to a temporary directory before exercising setup
and rotation, so it does not modify the repository's real token.
