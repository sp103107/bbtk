# Kickoff Entrypoints — v0.8.5

## Two-entrypoint model

This bump adds two separate entrypoints so developer agents and product users do not collide.

| Audience | Entrypoint | Purpose | Scope |
|---|---|---|---|
| Cursor/developer agent | `python scripts/onboard_agent.py` | read repo state and continuation boundaries | read-only development onboarding |
| Owner/operator/product user | `python scripts/start_here_user.py` | start and use the product after unzip | product usage instructions only |

## Cursor kickoff pointer

```text
Start by running: python scripts/onboard_agent.py
```

## Product kickoff pointer

```text
Start by running: python scripts/start_here_user.py
```

## Short Windows package path

Use short paths to avoid Windows path-length issues:

```text
C:\bbtc\bbtc_v0_8_5
```

## Boundary

The kickoff DOCX ZIP is a user convenience artifact. The repo bump remains the full repo/package state.
