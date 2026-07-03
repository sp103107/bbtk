#!/usr/bin/env python3
from __future__ import annotations
import ast, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
checks={}; errors=[]; warnings=[]
required=[
 'repo_release_state.json','reports/runtime_smoke_report.v0.8.0.json','reports/deployment_preflight_report.v0.8.0.json',
 'validation/validation_report.v0.8.0.json','validation/backend_connectivity_guard_report.v0.8.0.json',
 'validation/professional_blueprint_validation_report.v0.8.0.json','docs/RELEASE_READINESS_RUNBOOK_v0.8.0.md',
 'scripts/start_kiosk_server.py'
]
for rel in required:
    if not (ROOT/rel).exists(): errors.append('missing:'+rel)
checks['required_release_files_present']=not any(e.startswith('missing:') for e in errors)
for rel in ['scripts/start_kiosk_server.py','repo_scaffold/app/server.py']:
    try: ast.parse((ROOT/rel).read_text(encoding='utf-8')); checks[f'python_parses:{rel}']=True
    except Exception as e: checks[f'python_parses:{rel}']=False; errors.append(f'python_parse_failed:{rel}:{e}')
state=json.loads((ROOT/'repo_release_state.json').read_text())
checks['full_repo_scope']=state.get('bump_scope')=='full_repo'
checks['non_claims_preserved']='No production deployment is claimed.' in json.dumps(state) or 'No production deployment.' in json.dumps(state)
checks['backend_guard_status_pass']=state.get('backend_connectivity_guard_status')=='pass'
checks['release_readiness_status_set']=state.get('release_readiness_status') in {'pass_with_operator_warnings','pass'}
if 'owner_token_default_change_required_before_live_use' not in json.dumps(state): warnings.append('expected_default_secret_warning_not_recorded')
for k,v in list(checks.items()):
    if not v: errors.append('check_failed:'+k)
status='fail' if errors else ('pass_with_warnings' if warnings else 'pass')
report={'version':VERSION,'status':status,'checks':checks,'errors':errors,'warnings':warnings,'non_claims':['Release readiness is not a production deployment claim.','Default secrets must be changed before live use.']}
(ROOT/f'reports/release_readiness_report.v{VERSION}.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
