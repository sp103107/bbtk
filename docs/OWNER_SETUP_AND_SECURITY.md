# Owner Setup and Security Notes v0.2.0

## Mission

This document defines the v0.2.0 owner setup hardening lane for the Best Buds Time Clock Capsule.

## Required first setup

Edit:

```text
repo_scaffold/app/config/settings.json
```

Replace these defaults before live use:

```text
owner_token = CHANGE_ME_OWNER_TOKEN
pin_pepper = CHANGE_ME_PIN_PEPPER
```

## Owner surfaces

The following HTTP surfaces require the owner token:

```text
GET  /api/owner/summary
GET  /api/owner/employees
GET  /api/owner/download
POST /api/owner/export
POST /api/owner/employees
POST /api/owner/backup
```

## Employee surfaces

Employee punches require:

```text
employee_id
PIN
event_type
```

Accepted event types:

```text
clock_in
clock_out
break_start
break_end
```

## Hard boundary

This is owner-token and PIN gated. It is not production security hardening. Before real deployment, add HTTPS, real authentication, secure hosting, formal backup restore testing, and access logging review.
