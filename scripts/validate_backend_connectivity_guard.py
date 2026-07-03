#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
html=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')
js=(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
css=(ROOT/'repo_scaffold/app/static/style.css').read_text(encoding='utf-8')
checks={
 'backend_banner_present':'backend_connection_banner' in html,
 'runtime_card_state_present':'runtime_card' in html and 'runtime-dot' in html,
 'file_protocol_detection':'location.protocol === "file:"' in js,
 'health_check_function_present':'function checkBackendHealth' in js and '/api/health' in js,
 'offline_payload_present':'backendOfflinePayload' in js and 'backend_unreachable' in js,
 'fetch_errors_are_caught':'catch (err)' in js and 'setBackendConnection("offline"' in js,
 'operator_copy_present':'Start the Python server' in html+js and 'local network URL' in html+js,
 'offline_css_present':'.connection-banner.offline' in css and '.runtime-card.offline' in css,
 'kiosk_launcher_present':(ROOT/'scripts/start_kiosk_server.py').exists(),
}
errors=[f'check_failed:{k}' for k,v in checks.items() if not v]
report={'version':VERSION,'status':'pass' if not errors else 'fail','checks':checks,'errors':errors}
(ROOT/f'validation/backend_connectivity_guard_report.v{VERSION}.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
