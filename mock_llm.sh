#!/usr/bin/env bash
# mock_llm.sh - Run local mock LLM server (Linux & macOS)
set -uo pipefail
cd "$(dirname "$0")"

PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
      PY="$candidate"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "Python 3.9 or newer was not found on your system."
  exit 1
fi


exec "$PY" mock_llm.py "$@"
