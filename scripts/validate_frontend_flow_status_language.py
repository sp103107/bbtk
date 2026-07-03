#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
errors=[]; checks={}
required=[
 'repo_scaffold/app/static/index.html','repo_scaffold/app/static/app.js','repo_scaffold/app/static/style.css',
 'contracts/ui_ux/frontend_flow_status_language_contract.v0.8.5.json','contracts/ui_ux/frontend_flow_status_language_contract.schema.json',
 'contracts/frontend_surface/frontend_flow_status_surface.v0.8.5.json','docs/FRONTEND_FLOW_GRAPHICS_STATUS_LANGUAGE_v0.8.5.md',
 'release_candidate/rc7_5_frontend_flow_graphics_status_language/README.md','frontend/save_state/frontend_flow_status_language_save_state.v0.8.5.json'
]
for rel in required:
    ok=(ROOT/rel).exists(); checks[f'present:{rel}']=ok
    if not ok: errors.append('missing:'+rel)
html=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')
js=(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
css=(ROOT/'repo_scaffold/app/static/style.css').read_text(encoding='utf-8')
requirements={
 'employee_flow_rail_present':'employee_flow_rail' in html and all(x in html for x in ['ID','PIN','Punch','Receipt','Synced']),
 'owner_flow_rail_present':'owner_flow_rail' in html and all(x in html for x in ['Review','Export','Close','Backup','Verify']),
 'offline_flow_rail_present':'offline_flow_rail' in html and all(x in html for x in ['Backend','Local Queue','Sync','Owner Review','Decision']),
 'flow_js_helpers_present':all(x in js for x in ['setFlowStep','setEmployeeFlow','setOwnerFlow','setOfflineFlow']),
 'flow_css_present':'flow-status-rail' in css and '.flow-step.done' in css and '.flow-step.warning' in css,
 'no_busy_cockpit_claim':'busy cockpit' in (ROOT/'docs/FRONTEND_FLOW_GRAPHICS_STATUS_LANGUAGE_v0.8.5.md').read_text(encoding='utf-8').lower(),
 'docs_non_claims_present':'does not add animation-heavy dashboards' in (ROOT/'docs/FRONTEND_FLOW_GRAPHICS_STATUS_LANGUAGE_v0.8.5.md').read_text(encoding='utf-8'),
}
for k,v in requirements.items():
    checks[k]=bool(v)
    if not v: errors.append(k)
report={'version':VERSION,'phase':'rc7_5_frontend_flow_graphics_status_language','status':'pass' if not errors else 'fail','checks':checks,'errors':errors,'non_claims':['static flow status language validation only','no visual regression execution','no hosted deployment','no new backend route family']}
out=ROOT/f'validation/frontend_flow_status_language_validation_report.v{VERSION}.json'
out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if report['status']=='pass' else 1)
