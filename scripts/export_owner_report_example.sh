#!/usr/bin/env bash
set -euo pipefail
curl -s -X POST http://127.0.0.1:8080/api/owner/export -H 'Content-Type: application/json' -d '{"owner_token":"CHANGE_ME_OWNER_TOKEN","format":"csv"}'
