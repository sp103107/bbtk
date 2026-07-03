#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
html=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')
js=(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
checks={
 'success_copy_present': all(x in js+html for x in ['Success', 'Today', 'Status', 'Time']),
 'friendly_pin_error_present': 'PIN not accepted' in js,
 'employee_guidance_present': 'Enter Employee ID and PIN' in html and 'Read receipt' in html,
 'owner_next_action_copy_present': all(x in js for x in ['Download', 'Review', 'Backup verified', 'Pay period closed']),
 'technical_json_not_primary_copy': 'Technical receipt JSON' in html and 'Owner action result' in html,
}
errors=[f'check_failed:{k}' for k,v in checks.items() if not v]
report={'version':VERSION,'status':'pass' if not errors else 'fail','checks':checks,'errors':errors}
(ROOT/f'validation/ui_copy_validation_report.v{VERSION}.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
