#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
html=(ROOT/'repo_scaffold/app/static/index.html').read_text(encoding='utf-8')
css=(ROOT/'repo_scaffold/app/static/style.css').read_text(encoding='utf-8')
js=(ROOT/'repo_scaffold/app/static/app.js').read_text(encoding='utf-8')
ids=set(re.findall(r'id="([^"]+)"', html))
labels=re.findall(r'<label for="([^"]+)"', html)
checks={
 'aria_live_receipt_present':'aria-live="polite"' in html and 'employee_receipt' in html,
 'form_inputs_labeled': all(x in ids for x in labels),
 'large_touch_targets_present': '.punch-btn' in css and 'padding:18px' in css,
 'responsive_mobile_media_query_present':'@media(max-width:640px)' in css,
 'states_text_not_color_only': all(x in html+css+js for x in ['Success','Punch rejected','status-strip','receipt-message']),
 'technical_details_disclosure_present':'<details class="technical-details"' in html,
}
errors=[f'check_failed:{k}' for k,v in checks.items() if not v]
report={'version':VERSION,'status':'pass' if not errors else 'fail','checks':checks,'errors':errors}
(ROOT/f'validation/accessibility_static_check_report.v{VERSION}.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True))
sys.exit(0 if not errors else 1)
