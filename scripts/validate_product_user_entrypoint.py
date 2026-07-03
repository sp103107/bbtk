#!/usr/bin/env python3
from __future__ import annotations
import ast, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
errors=[]; checks={}
required=['scripts/start_here_user.py','docs/PRODUCT_USER_ENTRYPOINT.md','docs/KICKOFF_ENTRYPOINTS_v0.8.5.md']
for rel in required:
    ok=(ROOT/rel).exists(); checks[f'present:{rel}']=ok
    if not ok: errors.append(f'missing:{rel}')
text=(ROOT/'scripts/start_here_user.py').read_text(encoding='utf-8')
checks['product_language_present']='Product Start Here' in text and 'Employee flow' in text and 'Owner flow' in text
checks['short_windows_path_present']='C:\\\\bbtc' in text or 'C:\\bbtc' in text
checks['no_claimed_deployment']='not a hosted deployment' in text and 'not production-certified' in text
try: ast.parse(text); checks['python_parse']=True
except Exception as e: checks['python_parse']=False; errors.append(f'python_parse:{e}')
res=subprocess.run([sys.executable, str(ROOT/'scripts/start_here_user.py'), '--json'], cwd=ROOT, capture_output=True, text=True)
checks['script_executes_json']=res.returncode==0
if res.returncode: errors.append(res.stderr.strip() or 'start_here_user_failed')
else:
    try:
        payload=json.loads(res.stdout); checks['payload_version_alignment']=payload.get('version')==VERSION and payload.get('entrypoint')=='scripts/start_here_user.py'
    except Exception as e:
        checks['payload_version_alignment']=False; errors.append(f'payload_json:{e}')
for k,v in list(checks.items()):
    if not v and not k.startswith('present:'): errors.append(k)
report={'version':VERSION,'phase':'rc7_5_frontend_flow_graphics_status_language','status':'pass' if not errors else 'fail','checks':checks,'errors':errors,'non_claims':['product entrypoint prints instructions only','no backend started','no deployment claim']}
out=ROOT/f'validation/product_user_entrypoint_validation_report.v{VERSION}.json'
out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if report['status']=='pass' else 1)
