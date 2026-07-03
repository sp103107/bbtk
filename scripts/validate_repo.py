#!/usr/bin/env python3
from __future__ import annotations
import ast, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
PHASE='rc8_validation_and_context_checkpoint'
NEXT_PHASE='arc_role_based_manager_permissions'
REQUIRED=[
 'README.md','guide_pack.json','package.json','repo_release_state.json','CHANGELOG.md','VERSION',
 'contracts/ui_ux/employee_qr_entry_contract.v0.8.6.json','contracts/frontend_surface/employee_portal_surface.v0.8.6.json','contracts/development_library_crosswalk.v0.8.6.json',
 'docs/EMPLOYEE_QR_ENTRY_PORTAL_v0.8.6.md','docs/QR_URL_CLOCK_FLOW.md','docs/AGENT_ONBOARDING_ENTRYPOINT.md','docs/PRODUCT_USER_ENTRYPOINT.md',
 'cursor/CURSOR_KICKOFF_TIME_CLOCK.md','pipeline/pipeline_plan.v0.8.6.json','pipeline/bbtc_hardening_arc_series.v0.8.6.json',
 'scripts/validate_repo.py','scripts/runtime_smoke.py','scripts/onboard_agent.py','scripts/start_here_user.py','scripts/start_all.bat','scripts/start_all.sh',
 'scripts/validate_employee_qr_entry.py','scripts/validate_dev_startup_scripts.py','scripts/validate_agent_onboarding_entrypoint.py','scripts/validate_product_user_entrypoint.py',
 'scripts/validate_owner_token_generator.py','docs/OWNER_TOKEN_GENERATOR.md',
 'scripts/validate_employee_management_kiosk_arc.py','docs/SYSTEM_STATE_CURRENT.md','docs/EMPLOYEE_MANAGEMENT_ARC.md','docs/KIOSK_MODE_TIMECLOCK_FLOW.md','docs/GUEST_SIGN_IN_EXPORT_RULES.md','docs/HUMAN_READABLE_CSV_STANDARD.md','docs/LIVE_CLOCKED_IN_STATUS_TRANSPORT.md','docs/SUMMARY_AND_MANAGE_BUTTON_FIX.md','docs/NON_CLAIMS.md',
 'contracts/employee/employee_record.v1.schema.json','contracts/employee/employee_status.v1.schema.json','contracts/timeclock/time_entry.v1.schema.json','contracts/timeclock/active_session.v1.schema.json','contracts/timeclock/kiosk_event.v1.schema.json','contracts/guest/guest_sign_in.v1.schema.json','contracts/export/employee_time_export.v1.schema.json','contracts/export/guest_sign_in_export.v1.schema.json','contracts/export/human_readable_csv.v1.schema.json','contracts/realtime/live_clocked_in_status.v1.schema.json',
 'pipeline/arc_employee_management_kiosk_timeclock.v0.9.0.json','validation/employee_management_validation_report.json','validation/kiosk_mode_validation_report.json','validation/guest_export_validation_report.json','validation/csv_format_validation_report.json','validation/realtime_status_validation_report.json','validation/summary_button_bugfix_validation_report.json',
 'context/working_set/working_set_update_0016.v0.9.0.json','context/episodes/episode_checkpoint_0016.v0.9.0.json','context/ledger/context_ledger.v0.9.0.jsonl','context/resume_pack/resume_pack_manifest.v0.9.0.json','context/source_artifacts/source_artifact_hashes.v0.9.0.json',
 'frontend/save_state/employee_management_kiosk_timeclock_save_state.v0.9.0.json','reports/drift_report.v0.9.0.json','reports/release_manifest.v0.9.0.json',
 'release_candidate/rc7_6_employee_qr_entry_and_kiosk_fit/README.md','release_candidate/rc7_6_employee_qr_entry_and_kiosk_fit/rc7_6_phase_contract.json',
 'reports/release_manifest.v0.8.6.json','reports/drift_report.v0.8.6.json','validation/employee_qr_entry_validation_report.v0.8.6.json',
 'context/working_set/working_set_update_0015.v0.8.6.json','context/episodes/episode_checkpoint_0015.v0.8.6.json','context/ledger/context_ledger.v0.8.6.jsonl','context/resume_pack/resume_pack_manifest.v0.8.6.json',
 'frontend/save_state/employee_qr_entry_save_state.v0.8.6.json','development/README.md','development/local_library_bindings.example.json',
 'repo_scaffold/app/server.py','repo_scaffold/app/qrcodegen.py','repo_scaffold/app/static/index.html','repo_scaffold/app/static/employee.html','repo_scaffold/app/static/employee.js','repo_scaffold/app/static/kiosk_link.js','repo_scaffold/app/static/app.js','repo_scaffold/app/static/style.css','repo_scaffold/app/static/offline_queue.js','repo_scaffold/app/config/settings.json','repo_scaffold/capsule/capsule.json','repo_scaffold/capsule/capsule.lock.json'
]
errors=[]; checks={}
for rel in REQUIRED:
    if not (ROOT/rel).exists(): errors.append(f'missing_required:{rel}')
checks['required_files_exist']=not any(e.startswith('missing_required') for e in errors)
jc=0
for p in ROOT.rglob('*.json'):
    try: json.loads(p.read_text(encoding='utf-8')); jc+=1
    except Exception as e: errors.append(f'json_parse_failed:{p.relative_to(ROOT)}:{e}')
checks['json_parses']=not any(e.startswith('json_parse_failed') for e in errors)
jlc=0
for p in ROOT.rglob('*.jsonl'):
    for i,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
        if line.strip():
            try: json.loads(line); jlc+=1
            except Exception as e: errors.append(f'jsonl_parse_failed:{p.relative_to(ROOT)}:{i}:{e}')
checks['jsonl_parses']=not any(e.startswith('jsonl_parse_failed') for e in errors)
py_ok=True
for p in list((ROOT/'scripts').glob('*.py')) + [ROOT/'repo_scaffold/app/server.py', ROOT/'repo_scaffold/app/qrcodegen.py']:
    try: ast.parse(p.read_text(encoding='utf-8'))
    except Exception as e: py_ok=False; errors.append(f'python_compile_failed:{p.relative_to(ROOT)}:{e}')
checks['python_compiles']=py_ok
shell_ok=True; shell_checked=0
for p in (ROOT/'scripts').glob('*.sh'):
    shell_checked+=1
    res=subprocess.run(['bash','-n', p.relative_to(ROOT).as_posix()], cwd=ROOT, capture_output=True, text=True)
    if res.returncode: shell_ok=False; errors.append(f'shell_syntax_failed:{p.relative_to(ROOT)}:{res.stderr.strip()}')
checks['shell_syntax']=shell_ok
version_ok=True
for rel in ['repo_release_state.json','guide_pack.json','package.json','repo_scaffold/capsule/capsule.json','repo_scaffold/capsule/capsule.lock.json']:
    data=json.loads((ROOT/rel).read_text(encoding='utf-8'))
    candidate=data.get('version') or data.get('capsule_version')
    if candidate != VERSION: version_ok=False; errors.append(f'version_mismatch:{rel}:{candidate}!={VERSION}')
checks['version_consistency']=version_ok
state=json.loads((ROOT/'repo_release_state.json').read_text(encoding='utf-8'))
for k,v in {'full_repo_bump_scope':state.get('bump_scope')=='full_repo','current_phase_alignment':state.get('current_internal_phase')==PHASE,'next_phase_alignment':state.get('next_internal_phase')==NEXT_PHASE,'short_zip_policy_present':'zip_name_policy' in state,'product_entrypoint_present':(ROOT/'scripts/start_here_user.py').exists(),'agent_entrypoint_present':(ROOT/'scripts/onboard_agent.py').exists(),'start_all_present':(ROOT/'scripts/start_all.bat').exists() and (ROOT/'scripts/start_all.sh').exists()}.items():
    checks[k]=v
    if not v: errors.append(f'check_failed:{k}')
forbidden_names=['roadmap-only.zip','scaffold-only.zip','validator-only.zip','ui-only.zip']
found=[str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.name in forbidden_names or (p.suffix=='.zip' and 'rc' in p.name.lower())]
checks['forbidden_paths_absent']=not found
if found: errors.append('forbidden_paths_found:'+repr(found))
checks['pycache_absent']=not any('__pycache__' in p.parts or p.suffix=='.pyc' for p in ROOT.rglob('*'))
if not checks['pycache_absent']: errors.append('pycache_or_pyc_found')
top_required={'contracts','docs','cursor','pipeline','scripts','validation','release_candidate','reports','context','repo_scaffold','manifests','development','backend','runtime','frontend'}
checks['full_repo_shape']=all((ROOT/x).exists() for x in top_required)
if not checks['full_repo_shape']: errors.append('full_repo_shape_failed')
all_text='\n'.join(p.read_text(encoding='utf-8', errors='ignore') for p in list(ROOT.rglob('*.md'))+list(ROOT.rglob('*.json'))+list(ROOT.rglob('*.js')) if 'validation/validation_report' not in str(p))
forbidden_claims=['production deployment completed','release seal achieved','QEMU pass achieved','ISO boot passed','systemd activation completed','Hugging Face Space adapter active']
violations=[x for x in forbidden_claims if x in all_text]
checks['forbidden_claims_absent']=not violations
if violations: errors.append('forbidden_claims:'+repr(violations))
html=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')
emp_html=(ROOT/'repo_scaffold/app/static/employee.html').read_text(encoding='utf-8')
js=(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
server=(ROOT/'repo_scaffold/app/server.py').read_text(encoding='utf-8')
checks['flow_status_language_present']='employee_flow_rail' in html and 'owner_flow_rail' in html and 'offline_flow_rail' in html and 'setEmployeeFlow' in js and 'setOwnerFlow' in js
if not checks['flow_status_language_present']: errors.append('flow_status_language_missing')
checks['employee_qr_entry_present']='kiosk_employee_url' in html and '/employee' in emp_html and 'parsed.path == "/api/employee/summary"' in server and 'parsed.path == "/employee"' in server
if not checks['employee_qr_entry_present']: errors.append('employee_qr_entry_missing')
checks['owner_token_generator_present']='generate_owner_token_btn' in html and '/api/security/owner-token/generate' in js and 'def generate_and_save_owner_token' in server and 'generate_backup_tokens_btn' in html and '/api/security/backup-tokens/recover' in js and 'def recover_owner_token' in server
if not checks['owner_token_generator_present']: errors.append('owner_token_generator_missing')
checks['employee_management_kiosk_arc_present']='employee_management_panel' in html and 'timeclock_summary_panel' in html and 'def guest_sign_in' in server and 'def active_sessions' in server and 'arc_employee_management_kiosk_timeclock' in (ROOT/'pipeline/arc_employee_management_kiosk_timeclock.v0.9.0.json').read_text()
if not checks['employee_management_kiosk_arc_present']: errors.append('employee_management_kiosk_arc_missing')
checks['entrypoints_execute']=subprocess.run([sys.executable,str(ROOT/'scripts/onboard_agent.py'),'--json'],cwd=ROOT,capture_output=True,text=True).returncode==0 and subprocess.run([sys.executable,str(ROOT/'scripts/start_here_user.py'),'--json'],cwd=ROOT,capture_output=True,text=True).returncode==0
if not checks['entrypoints_execute']: errors.append('entrypoints_execute_failed')
res={'version':VERSION,'phase':PHASE,'status':'pass' if not errors else 'fail','checks':checks,'json_files_checked':jc,'jsonl_lines_checked':jlc,'shell_scripts_checked':shell_checked,'errors':errors}
(ROOT/f'validation/validation_report.v{VERSION}.json').write_text(json.dumps(res,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(res,indent=2,sort_keys=True))
sys.exit(0 if res['status']=='pass' else 1)
