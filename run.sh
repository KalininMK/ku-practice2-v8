#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "${1:-}" == "--tests" ]]; then
    exec python -m unittest discover -s tests -v
fi
exec python -m src.main "$@"
