#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT/'VERSION').read_text().strip()
checks = {}; errors = []
required = [
  'contracts/frontend_surface/frontend_surface_contract.v0.8.0.json',
  'contracts/frontend_surface/employee_kiosk_surface.v0.8.0.json',
  'contracts/frontend_surface/owner_dashboard_surface.v0.8.0.json',
  'contracts/frontend_surface/receipt_state_surface.v0.8.0.json',
  'contracts/frontend_surface/frontend_acceptance_checklist.v0.8.0.json',
  'repo_scaffold/app/static/index.html','repo_scaffold/app/static/app.js','repo_scaffold/app/static/style.css'
]
for rel in required:
    if not (ROOT/rel).exists(): errors.append(f'missing:{rel}')
html=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')
js=(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
css=(ROOT/'repo_scaffold/app/static/style.css').read_text(encoding='utf-8')
checks['required_frontend_files_present'] = not any(e.startswith('missing') for e in errors)
checks['employee_receipt_panel_present'] = all(x in html for x in ['employee_receipt','receipt_hours','receipt_status','receipt_time','aria-live','employee_status_strip'])
checks['owner_grouped_cards_present'] = all(x in html for x in ['owner-section-grid','owner-action-card','Payroll Exports','Pay Period Close','Backup / Restore Dry Run'])
checks['receipt_renderer_present'] = 'function renderPunchReceipt' in js and 'today_summary.net_work_hours' in js and 'punch_receipt' in js and 'friendlyError' in js
checks['backup_verify_existing_route_exposed'] = 'backup_verify_btn' in html and '/api/owner/backup/verify' in js
checks['professional_style_tokens_present'] = all(x in css for x in ['--brand', '--ok-bg', '.receipt.success', '.owner-section-grid', '.workflow-strip'])
checks['technical_json_disclosure_present'] = '<details class="technical-details">' in html or '<details class="technical-details" open>' in html
checks['pilot_acceptance_panel_preserved'] = all(x in html+js for x in ['pilot_readiness_btn','pilot_issue_btn','pilot_signoff_btn','pilot_pack_btn','pilot_result'])
checks['backend_connection_guard_present'] = all(x in html+js for x in ['backend_connection_banner','checkBackendHealth','backendOfflinePayload','Start the Python server'])
for k,v in checks.items():
    if not v: errors.append(f'check_failed:{k}')
report={'version':VERSION,'status':'pass' if not errors else 'fail','checks':checks,'errors':errors}
(ROOT/f'validation/frontend_surface_validation_report.v{VERSION}.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2, sort_keys=True))
sys.exit(0 if report['status']=='pass' else 1)
