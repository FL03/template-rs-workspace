#!/usr/bin/env bash
# Legacy entry point: test a freshly generated workspace.
set -euo pipefail
exec python3 "$(dirname "$0")/test-generation.py" --mode test "$@"
