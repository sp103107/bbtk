#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../repo_scaffold/app"
python server.py --host 127.0.0.1 --port 8080
