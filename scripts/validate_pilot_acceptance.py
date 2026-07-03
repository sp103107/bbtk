#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'validation/pilot_acceptance_validation_report.v0.8.0.json'
REQUIRED=[
 'contracts/schemas/pilot_readiness_report.schema.json',
 'contracts/schemas/pilot_issue.schema.json',
 'contracts/schemas/pilot_signoff_receipt.schema.json',
 'contracts/schemas/pilot_acceptance_pack_manifest.schema.json',
 'docs/LIVE_PILOT_ACCEPTANCE_PACK.md',
 'docs/EMPLOYEE_QUICK_START_CARD.md',
 'docs/OWNER_LIVE_PILOT_RUNBOOK.md',
 'release_candidate/rc6_live_pilot_acceptance_pack/README.md',
 'repo_scaffold/app/static/index.html',
 'repo_scaffold/app/static/app.js'
]

def main() -> int:
    errors=[]
    for rel in REQUIRED:
        if not (ROOT/rel).exists(): errors.append(f'missing:{rel}')
    server=(ROOT/'repo_scaffold/app/server.py').read_text(encoding='utf-8')
    ui=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')+(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
    checks={
      'required_files_exist': not errors,
      'pilot_routes_present': all(x in server for x in ['/api/owner/pilot/readiness','/api/owner/pilot/issue','/api/owner/pilot/signoff','/api/owner/pilot/package','pilot_readiness_report','create_pilot_acceptance_pack']),
      'pilot_ui_present': all(x in ui for x in ['pilot_readiness_btn','pilot_issue_btn','pilot_signoff_btn','pilot_pack_btn','pilot_result']),
      'non_claims_present': 'not a production deployment seal' in server.lower() and 'not a production deployment seal' in ui.lower(),
    }
    for k,v in checks.items():
        if not v: errors.append(f'check_failed:{k}')
    report={'version':'0.8.0','status':'pass' if not errors else 'fail','checks':checks,'errors':errors}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status']=='pass' else 1
if __name__=='__main__': sys.exit(main())
