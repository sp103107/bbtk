# Company Branding Clone Porter

This lane turns the time clock into a reusable branded package for another company.

## 1. Audit current branding

```powershell
python scripts/audit_branding_references.py
```

Outputs:

- `output/branding/branding_reference_report.json`
- `output/branding/branding_reference_report.md`

Use the report to separate runtime branding from historical docs and internal `bbtc_*`
security/token namespaces. Runtime branding can be templated. Internal token prefixes
should stay stable unless there is a separate migration plan.

## 2. Create a company profile

Start from:

```text
contracts/company_branding_profile.example.json
```

Recommended profile fields:

- `company.display_name`
- `company.legal_name`
- `company.site_id`
- `company.timezone`
- `branding.app_short_name`
- `branding.primary_color`
- `branding.accent_color`
- `branding.logo_path` if a company SVG logo is available
- `package.folder_name`
- `package.zip_name`

If `branding.logo_path` is blank, the packager creates a neutral initials logo.

## 3. Build the branded ZIP

```powershell
python scripts/build_company_timeclock_zip.py --profile contracts/company_branding_profile.example.json
```

Outputs:

- `output/company_zips/<company>.zip`
- `output/company_zips/<company>.manifest.json`

## 4. Validate portability

Before copying a branded package to another computer, run:

```powershell
python scripts/validate_portability.py --zip output/company_zips/<company>.zip
```

For the source repo runtime/tooling scope, run:

```powershell
python scripts/validate_portability.py
```

The validator rejects user-specific home-folder paths, version-pinned local workspace
paths, and absolute temp/output paths inside company ZIPs. Loopback URLs such as
`127.0.0.1` are allowed because they are local defaults that work on any device.

## Safety rules

The clone packager does not copy:

- runtime punch/guest data
- exports
- backups
- restore candidates
- existing owner tokens
- backup tokens
- existing administrator users

Each cloned company starts with default security placeholders and must complete first-run
administrator setup from the operator panel.
