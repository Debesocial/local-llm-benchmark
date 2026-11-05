#!/usr/bin/env bash
# run.sh - Launcher for LLM Benchmark (Linux & macOS)
# Usage: ./run.sh
# Or:    ./run.sh baseline --url http://localhost:8000/v1/chat/completions --model qwen-30b
set -uo pipefail
cd "$(dirname "$0")"

# Set terminal window title if running in an interactive TTY
if [ -t 1 ]; then
  printf "\033]0;LLM Benchmark\007"
fi

PY=""
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
      PY="$candidate"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "Python 3.9 or newer was not found on your system."
  echo "  Ubuntu/Debian     : sudo apt update && sudo apt install python3"
  echo "  RHEL/CentOS/Fedora: sudo dnf install python3"
  echo "  Arch Linux        : sudo pacman -S python"
  echo "  macOS (Homebrew)  : brew install python3"
  exit 1
fi

if [ ! -f llmload.py ]; then
  echo "File llmload.py was not found in directory: $(pwd)"
  exit 1
fi

if [ $# -gt 0 ] && [[ "$1" =~ ^(baseline|ramp|rate|soak|menu|compare|report)$ ]]; then
  exec "$PY" llmload.py "$@"
else
  exec "$PY" llmload.py menu "$@"
fi
