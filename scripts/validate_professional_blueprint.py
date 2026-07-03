#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
required=[
 'contracts/professional_app_blueprint/professional_time_clock_component_map.v0.8.0.json',
 'contracts/professional_app_blueprint/backend_connectivity_surface.v0.8.0.json',
 'contracts/professional_app_blueprint/release_readiness_contract.v0.8.0.json',
 'docs/PROFESSIONAL_TIME_CLOCK_BLUEPRINT_v0.8.0.md',
 'docs/RELEASE_READINESS_RUNBOOK_v0.8.0.md',
 'docs/PHONE_TABLET_KIOSK_STARTUP_v0.8.0.md'
]
errors=[]
for rel in required:
    if not (ROOT/rel).exists(): errors.append('missing:'+rel)
component=json.loads((ROOT/required[0]).read_text()) if (ROOT/required[0]).exists() else {'components':[]}
ids={c.get('id') for c in component.get('components',[])}
expected={'employee_kiosk','owner_dashboard','time_event_ledger','timecard_calculation_engine','pay_period_close','security_access','backup_restore','frontend_design_system'}
checks={
 'required_files_present':not errors,
 'component_coverage':expected.issubset(ids),
 'non_claims_present':'No production deployment is claimed.' in json.dumps(component),
 'release_readiness_contract_present':(ROOT/'contracts/professional_app_blueprint/release_readiness_contract.v0.8.0.json').exists()
}
for k,v in checks.items():
    if not v: errors.append('check_failed:'+k)
report={'version':VERSION,'status':'pass' if not errors else 'fail','checks':checks,'errors':errors}
(ROOT/f'validation/professional_blueprint_validation_report.v{VERSION}.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
