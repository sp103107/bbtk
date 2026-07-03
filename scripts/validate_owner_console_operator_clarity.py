#!/usr/bin/env python3
import json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
VERSION='0.8.4'
PHASE='rc7_4_owner_console_operator_clarity'
errors=[]; checks={}
def req(rel):
    ok=(ROOT/rel).exists(); checks['file:'+rel]=ok
    if not ok: errors.append('missing:'+rel)
for rel in [
 'repo_scaffold/app/static/index.html','repo_scaffold/app/static/app.js','repo_scaffold/app/static/style.css',
 'contracts/ui_ux/owner_console_operator_clarity_contract.v0.8.4.json','contracts/frontend_surface/owner_dashboard_surface.v0.8.4.json',
 'docs/OWNER_CONSOLE_OPERATOR_CLARITY_v0.8.4.md','docs/OWNER_ACTION_RESULT_COPY_v0.8.4.md','docs/OWNER_CONSOLE_ACCEPTANCE_v0.8.4.md',
 'release_candidate/rc7_4_owner_console_operator_clarity/README.md']:
    req(rel)
html=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')
js=(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
css=(ROOT/'repo_scaffold/app/static/style.css').read_text(encoding='utf-8')
requirements={
 'owner_console_status_grid_present':'owner-console-status-grid' in html and 'owner_console_state' in html,
 'owner_action_summary_present':'owner_action_summary' in html and 'renderOwnerActionSummary' in js,
 'owner_task_rail_present':'owner-task-rail' in html and all(x in html for x in ['Today','Employees','Payroll','Review','Recovery','Readiness']),
 'owner_cards_have_groups':html.count('data-owner-group=') >= 6,
 'card_result_hints_present':html.count('owner-card-result') >= 5 and 'markOwnerCard' in js,
 'technical_json_hidden_by_default':'<details class="technical-details owner-json-details">' in html,
 'owner_token_guard_present':'validateOwnerTokenPresent' in js and js.count('validateOwnerTokenPresent()') >= 8,
 'offline_review_non_claim':'pending-owner-review evidence' in html.lower() and 'recovery evidence only' in html.lower(),
 'css_operator_console_present':'owner-console-status-grid' in css and 'owner-action-summary' in css,
 'no_hf_adapter_claim':'hugging face space adapter active' not in (html+js).lower()
}
for k,v in requirements.items():
    checks[k]=bool(v)
    if not v: errors.append(k)
report={'version':VERSION,'phase':PHASE,'status':'pass' if not errors else 'fail','checks':checks,'errors':errors,'non_claims':['static owner console validation only','no new backend route family','no visual regression execution','no production deployment']}
out=ROOT/f'validation/owner_console_operator_clarity_validation_report.v{VERSION}.json'
out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if report['status']=='pass' else 1)
