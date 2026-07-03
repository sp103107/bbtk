#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SETTINGS=ROOT/'repo_scaffold/app/config/settings.json'
VERSION=(ROOT/'VERSION').read_text().strip()
REPORT=ROOT/f'validation/policy_validation_report.v{VERSION}.json'
errors=[]; checks={}
settings=json.loads(SETTINGS.read_text(encoding='utf-8'))
checks['policy_version_present']=settings.get('app_security_policy_version')==VERSION
checks['runtime_version_present']=settings.get('runtime_version')==VERSION
checks['owner_token_not_empty']=bool(settings.get('owner_token'))
checks['pin_pepper_not_empty']=bool(settings.get('pin_pepper'))
checks['min_pin_length_floor']=int(settings.get('min_pin_length',0))>=4
checks['adjustment_reason_required']=settings.get('owner_adjustment_reason_required') is True
checks['owner_adjustments_explicitly_configured']='allow_owner_adjustments' in settings
checks['backup_manifest_required']=settings.get('backup_policy',{}).get('manifest_required') is True
checks['restore_dry_run_required']=settings.get('backup_policy',{}).get('restore_dry_run_required_before_apply') is True
checks['server_route_cannot_apply_restore']=settings.get('backup_policy',{}).get('server_route_can_apply_restore') is False
checks['deployment_preflight_required']=settings.get('deployment_policy',{}).get('preflight_required_before_live_use') is True
checks['pilot_mode_enabled']=settings.get('pilot_policy',{}).get('pilot_mode_enabled') is True
checks['pilot_readiness_required']=settings.get('pilot_policy',{}).get('readiness_check_required_before_live_pilot') is True
checks['pilot_issue_log_required']=settings.get('pilot_policy',{}).get('issue_log_required') is True
checks['pilot_signoff_required']=settings.get('pilot_policy',{}).get('owner_signoff_required') is True
for k,v in checks.items():
    if not v: errors.append('policy_check_failed:'+k)
res={'version':VERSION,'status':'pass' if not errors else 'fail','checks':checks,'errors':errors,'non_claims':['policy validation checks config shape only','no production security seal','restore apply is not enabled from owner web route']}
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(res, indent=2, sort_keys=True)+'\n', encoding='utf-8')
print(json.dumps(res, indent=2, sort_keys=True))
sys.exit(0 if res['status']=='pass' else 1)
