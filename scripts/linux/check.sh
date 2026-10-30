#!/usr/bin/env bash
set -Eeuo pipefail
atelier_scripts=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$atelier_scripts/session-env.sh"
exec python3 "$atelier_scripts/doctor.py"
