#!/usr/bin/env bash
# Validate generated projects; pass --mode all/build/test/clippy/bench/generate.
set -euo pipefail
exec python3 "$(dirname "$0")/test-generation.py" "$@"
