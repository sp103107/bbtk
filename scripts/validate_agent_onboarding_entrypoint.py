#!/usr/bin/env python3
from __future__ import annotations
import ast, json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
errors=[]; checks={}
for rel in ['scripts/onboard_agent.py','docs/AGENT_ONBOARDING_ENTRYPOINT.md','cursor/CURSOR_KICKOFF_TIME_CLOCK.md']:
    ok=(ROOT/rel).exists(); checks[f'present:{rel}']=ok
    if not ok: errors.append(f'missing:{rel}')
text=(ROOT/'scripts/onboard_agent.py').read_text(encoding='utf-8')
checks['read_only_language_present']='read-only' in text.lower() and 'does not start the backend server' in text.lower()
checks['no_network_or_server_start']='start_kiosk_server.py --host' in text and 'subprocess' not in text and 'requests' not in text and 'urllib' not in text
checks['source_of_truth_listed']=all(x in text for x in ['repo_release_state.json','VERSION','validation/','context/resume_pack/'])
checks['non_claims_listed']=all(x in text.lower() for x in ['no production deployment claim','no release seal claim','no qemu/iso/boot pod/systemd/rootfs claim'])
try: ast.parse(text); checks['python_parse']=True
except Exception as e: checks['python_parse']=False; errors.append(f'python_parse:{e}')
res=subprocess.run([sys.executable, str(ROOT/'scripts/onboard_agent.py'), '--json'], cwd=ROOT, capture_output=True, text=True)
checks['script_executes_json']=res.returncode==0
if res.returncode: errors.append(res.stderr.strip() or 'onboard_agent_failed')
else:
    try:
        payload=json.loads(res.stdout); checks['payload_version_alignment']=payload.get('version')==VERSION and payload.get('entrypoint')=='scripts/onboard_agent.py'
    except Exception as e:
        checks['payload_version_alignment']=False; errors.append(f'payload_json:{e}')
for k,v in list(checks.items()):
    if not v and not k.startswith('present:'): errors.append(k)
report={'version':VERSION,'phase':'rc7_6_employee_qr_entry_and_kiosk_fit','status':'pass' if not errors else 'fail','checks':checks,'errors':errors,'non_claims':['read-only onboarding validation only','no runtime activation','no network calls']}
out=ROOT/f'validation/agent_onboarding_entrypoint_validation_report.v{VERSION}.json'
out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if report['status']=='pass' else 1)
