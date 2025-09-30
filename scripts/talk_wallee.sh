#!/usr/bin/env bash

set -euo pipefail

# Launch the chatbot with the WALL-E-like "cracked saga" persona.
# Usage:
#   bash scripts/talk_wallee.sh               # local dev (simulate, stdin input, prints TTS)
#   OPENAI_API_KEY=... bash scripts/talk_wallee.sh --no-sim  # use OpenAI if available
#   bash scripts/talk_wallee.sh --no-sim      # on Pi with audio deps (vosk/pyttsx3)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "${PROJECT_ROOT}"

SIMULATE=true
EXTRA_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --no-sim)
      SIMULATE=false
      ;;
    *)
      EXTRA_ARGS+=("$arg")
      ;;
  esac
done

if [ "$SIMULATE" = true ]; then
  python3 src/chatbot.py --simulate --persona-file src/personas/wallee.txt "${EXTRA_ARGS[@]}"
else
  python3 src/chatbot.py --persona-file src/personas/wallee.txt "${EXTRA_ARGS[@]}"
fi

