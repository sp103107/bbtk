#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
text='\n'.join(p.read_text(encoding='utf-8', errors='ignore') for p in list((ROOT/'docs').glob('*.md'))+list((ROOT/'contracts').rglob('*.json'))+[(ROOT/'repo_release_state.json')])
forbidden_claims=['production deployment completed','legal compliance seal achieved','cannabis compliance certification achieved','biometric identity proof implemented','geofence proof implemented','camera verification implemented','payroll-provider integration completed']
forbidden_impl=['stripe payroll','adp integration','gusto integration active','quickbooks api key','facial recognition model','gps geofence enforced']
checks={
 'forbidden_claims_absent': not any(x.lower() in text.lower() for x in forbidden_claims),
 'forbidden_implementation_terms_absent': not any(x.lower() in text.lower() for x in forbidden_impl),
 'phase_is_allowed_hardening_or_release_readiness': ('rc6_1_ui_ux_hardening_and_operator_clarity' in text or 'rc7_production_installation_readiness_candidate' in text),
 'non_claims_preserved': 'No production deployment' in text and 'No payroll-provider integration' in text,
}
errors=[f'check_failed:{k}' for k,v in checks.items() if not v]
report={'version':VERSION,'status':'pass' if not errors else 'fail','checks':checks,'errors':errors}
(ROOT/f'validation/no_scope_expansion_report.v{VERSION}.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
