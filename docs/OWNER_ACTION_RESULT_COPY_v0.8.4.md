# Owner Action Result Copy v0.8.4

Owner actions must return human-readable status before raw JSON.

## Required result order

1. `owner_notice` banner.
2. `owner_action_summary` card.
3. card-level result hint near the clicked task.
4. technical JSON under disclosure.

## Required copy posture

- Success copy must include what happened and the next review step.
- Warning copy must preserve non-claim boundaries.
- Offline sync copy must state pending owner review.
- Backup copy must distinguish created backup from verified restore dry run.
