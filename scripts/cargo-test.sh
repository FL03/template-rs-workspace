#! /bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

cargo nextest run --locked --no-fail-fast "$@"
