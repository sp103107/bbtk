# Judge Prompt — v0.8.2 UI/UX Truth Lock Acceptance

## Mission

Decide whether v0.8.2 truthfully added UI/UX surface inventory and did not overclaim runtime, deployment, or visual regression success.

## Required evidence to inspect

- `contracts/ui_ux/*.v0.8.2.json`
- `docs/UI_UX_TRUTH_LOCK_v0.8.2.md`
- `validation/ui_ux_truth_lock_validation_report.v0.8.2.json`
- `repo_release_state.json`
- `context/episodes/episode_checkpoint_0011.v0.8.2.json`

## Pass/fail posture

Pass only if contracts parse, required components/states are registered, Hugging Face adapter is deferred, and forbidden claims are absent. File presence alone is insufficient.
