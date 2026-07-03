#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
REQ=[
 'contracts/ui_ux/ui_component_inventory.v0.8.2.json',
 'contracts/ui_ux/ui_state_contract.v0.8.2.json',
 'contracts/ui_ux/ui_interaction_contract.v0.8.2.json',
 'contracts/ui_ux/ui_error_copy_contract.v0.8.2.json',
 'contracts/ui_ux/ui_receipt_contract.v0.8.2.json',
 'contracts/ui_ux/mobile_kiosk_surface_contract.v0.8.2.json',
 'contracts/ui_ux/owner_console_surface_contract.v0.8.2.json',
 'contracts/ui_ux/ui_arc_series_contract.v0.8.2.json',
 'docs/UI_UX_TRUTH_LOCK_v0.8.2.md',
 'docs/CURRENT_UI_SURFACE_MAP_v0.8.2.md',
 'docs/MOBILE_KIOSK_USER_JOURNEY_v0.8.2.md',
 'docs/OWNER_CONSOLE_USER_JOURNEY_v0.8.2.md',
 'docs/UI_COMPONENT_INVENTORY_v0.8.2.md',
 'docs/UI_UX_ARC_SERIES_ROADMAP_v0.8.2.md',
 'frontend/save_state/ui_truth_lock_save_state.v0.8.2.json',
 'release_candidate/rc7_2_ui_ux_truth_lock_and_component_inventory/rc7_2_phase_contract.json'
]
errors=[]; checks={}
for rel in REQ:
    if not (ROOT/rel).exists(): errors.append('missing:'+rel)
checks['required_files_present']=not any(e.startswith('missing:') for e in errors)
inv=json.loads((ROOT/'contracts/ui_ux/ui_component_inventory.v0.8.2.json').read_text())
states=json.loads((ROOT/'contracts/ui_ux/ui_state_contract.v0.8.2.json').read_text())
copy=json.loads((ROOT/'contracts/ui_ux/ui_error_copy_contract.v0.8.2.json').read_text())
arc=json.loads((ROOT/'contracts/ui_ux/ui_arc_series_contract.v0.8.2.json').read_text())
component_ids={c.get('component_id') for c in inv.get('components',[])}
checks['component_count_minimum']=len(component_ids)>=18
checks['employee_components_present']={'employee_kiosk_panel','employee_punch_buttons','employee_receipt','today_hours_card'}.issubset(component_ids)
checks['owner_components_present']={'owner_console','owner_exports','pay_period_close','backup_restore_panel'}.issubset(component_ids)
state_ids={s.get('state_id') for s in states.get('states',[])}
checks['critical_states_present']={'backend_offline','punch_success','punch_rejected','offline_saved_local','offline_synced_pending_review'}.issubset(state_ids)
copy_codes={c.get('code') for c in copy.get('copy',[])}
checks['critical_copy_present']={'invalid_pin','backend_unreachable','offline_saved_local','unauthorized'}.issubset(copy_codes)
checks['arc_series_next_phase']=arc.get('series',[{},{}])[1].get('phase')=='rc7_3_employee_kiosk_gold_path_polish'
checks['hf_adapter_deferred']='huggingface_space_adapter_preview' in arc.get('deferred',[])
html=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')
js=(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
checks['current_ui_sources_still_present']=all(x in html+js for x in ['backend_connection_banner','employee_receipt','owner-section-grid','offline'])
for k,v in checks.items():
    if not v: errors.append('check_failed:'+k)
report={'version':VERSION,'phase':'rc7_2_ui_ux_truth_lock_preservation_check','status':'pass' if not errors else 'fail','checks':checks,'errors':errors,'non_claims':['static UI inventory only','no visual regression execution','no production deployment','no Hugging Face adapter included']}
(ROOT/f'validation/ui_ux_truth_lock_validation_report.v{VERSION}.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
# also specialized reports
(ROOT/f'validation/ui_component_inventory_report.v{VERSION}.json').write_text(json.dumps({'version':VERSION,'status':report['status'],'component_count':len(component_ids),'components':sorted(component_ids)},indent=2,sort_keys=True)+'\n',encoding='utf-8')
(ROOT/f'validation/ui_state_coverage_report.v{VERSION}.json').write_text(json.dumps({'version':VERSION,'status':report['status'],'state_count':len(state_ids),'states':sorted(state_ids)},indent=2,sort_keys=True)+'\n',encoding='utf-8')
(ROOT/f'validation/ui_copy_gap_report.v{VERSION}.json').write_text(json.dumps({'version':VERSION,'status':report['status'],'copy_codes':sorted(copy_codes),'gaps':[] if checks['critical_copy_present'] else ['missing critical copy']},indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if report['status']=='pass' else 1)
