# Local development bindings

This folder holds **local-only** development pointers. Files here are gitignored and are not part of release package truth.

## Setup

1. Copy `local_library_bindings.example.json` to `local_library_bindings.json`.
2. Edit paths to match your machine.
3. Do not commit `local_library_bindings.json`.

## Purpose

- Point BBTC development work at local AoS library packs for blueprint and UI pattern reference.
- Keep release/repo truth in `VERSION`, `repo_release_state.json`, `contracts/`, and `validation/`.

## Non-claims

- Local bindings do not activate external libraries at runtime.
- Local bindings are not proof of integration or deployment readiness.
