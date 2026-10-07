#!/usr/bin/env bash
set -euo pipefail

# TEXTRIS 단일 실행 파일 빌드 스크립트
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

exec "$PYTHON" "$SCRIPT_DIR/scripts/build.py" "$@"
