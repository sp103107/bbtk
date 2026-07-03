# Frontend Graphics Reference Binding v0.8.2

## Referenced artifact

```text
aos_ks_frontend_flow_graphics_v0_1_15.zip
```

## Use allowed in this time clock package

- Flow/status language
- Component readiness matrix concepts
- Preview gallery concept
- Visual baseline concept
- Theme/design-token discipline

## Use not allowed in this time clock package

- Do not vendor graphics assets into the business capsule in this bump.
- Do not create animated cockpit clutter.
- Do not claim visual regression execution without screenshot tooling.

## Application to time clock

Employee flow:

```text
ID → PIN → Punch → Receipt → Synced
```

Owner flow:

```text
Review → Export → Close → Backup → Verify
```

Offline flow:

```text
Backend Down → Local Queue → Sync Pending → Owner Review → Accepted/Rejected
```
