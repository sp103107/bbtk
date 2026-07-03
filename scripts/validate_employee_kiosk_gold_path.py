#!/usr/bin/env python3
import json, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
checks={}; errors=[]
def require_file(p):
    ok=(ROOT/p).exists(); checks[f"file:{p}"]=ok
    if not ok: errors.append(f"missing:{p}")
    return ok
for p in [
    pathlib.Path('repo_scaffold/app/static/index.html'),
    pathlib.Path('repo_scaffold/app/static/app.js'),
    pathlib.Path('repo_scaffold/app/static/style.css'),
    pathlib.Path('contracts/ui_ux/employee_kiosk_gold_path_contract.v0.8.3.json'),
    pathlib.Path('docs/EMPLOYEE_KIOSK_GOLD_PATH_POLISH_v0.8.3.md'),
    pathlib.Path('release_candidate/rc7_3_employee_kiosk_gold_path_polish/README.md')]: require_file(p)
html=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')
js=(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
css=(ROOT/'repo_scaffold/app/static/style.css').read_text(encoding='utf-8')
server=(ROOT/'repo_scaffold/app/server.py').read_text(encoding='utf-8')
requirements={
 'employee_focus_card_present':'employee-focus-card' in html and 'employee-focus-title' in html,
 'input_guard_present':'employee_input_guard' in html and 'validateEmployeeInputs' in js,
 'data_punch_actions_present':html.count('data-punch-action=') >= 4,
 'today_hours_card_present':'today-hours-card' in html and 'today_hours_value' in html and 'updateTodayCard' in js,
 'receipt_visibility_present':'kiosk-receipt' in html and 'receipt_next' in html,
 'offline_non_claim_copy_present':'pending owner review' in html.lower() or 'pending-owner-review' in html.lower(),
 'technical_json_hidden_by_details':'<details class="technical-details">' in html,
 'tap_target_css_present':'.employee-panel .punch-btn{min-height:86px}' in css,
 'app_version_current':f'APP_VERSION = "{VERSION}"' in server,
 'no_hf_adapter_claim':'hugging face space adapter active' not in html.lower(),
}
for k,v in requirements.items():
    checks[k]=bool(v)
    if not v: errors.append(k)
report={'version':VERSION,'phase':'rc7_3_employee_kiosk_gold_path_polish_preserved','status':'pass' if not errors else 'fail','checks':checks,'errors':errors,'non_claims':['static UI validation only','no visual regression execution','no production deployment','offline queue remains recovery evidence']}
out=ROOT/f'validation/employee_kiosk_gold_path_validation_report.v{VERSION}.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
