#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
html=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')
css=(ROOT/'repo_scaffold/app/static/style.css').read_text(encoding='utf-8')
js=(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
employee_html=(ROOT/'repo_scaffold/app/static/employee.html').read_text(encoding='utf-8')
employee_js=(ROOT/'repo_scaffold/app/static/employee.js').read_text(encoding='utf-8')
combined_html=html+employee_html
ids=set(re.findall(r'id="([^"]+)"', combined_html))
labels=re.findall(r'<label for="([^"]+)"', combined_html)
checks={
 'aria_live_receipt_present':'aria-live="assertive"' in employee_html and 'kiosk_receipt' in employee_html,
 'form_inputs_labeled': all(x in ids for x in labels),
 'large_touch_targets_present': '.kiosk-action' in css and 'min-height:84px' in css,
 'responsive_mobile_media_query_present':'@media(max-width:640px)' in css,
 'states_text_not_color_only': all(x in employee_html+css+employee_js for x in ['Action not recorded','kiosk-receipt','kiosk_receipt_message']),
 'technical_details_disclosure_present':'download_last_receipt_btn' in html and '<pre' not in html and '<details class="technical-details"' not in html,
}
errors=[f'check_failed:{k}' for k,v in checks.items() if not v]
report={'version':VERSION,'status':'pass' if not errors else 'fail','checks':checks,'errors':errors}
(ROOT/f'validation/accessibility_static_check_report.v{VERSION}.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
