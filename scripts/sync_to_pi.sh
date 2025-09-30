#!/usr/bin/env bash

# Safe rsync-based sync script for Raspberry Pi
# Usage: ./scripts/sync_to_pi.sh [pi_user@pi_host] [target_dir]
# Example: ./scripts/sync_to_pi.sh pi@192.168.1.100 /home/pi/robot-project

set -euo pipefail

PI=${1:-pi@192.168.1.100}
TARGET_DIR=${2:-/home/pi/robot-project}

echo "Syncing project to ${PI}:${TARGET_DIR}"

# Files/folders to exclude from rsync
EXCLUDES=(--exclude='.git' --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc')

# Ensure destination exists on Pi
ssh ${PI} "mkdir -p ${TARGET_DIR}"

# Run rsync (preserve perms, compress, verbose)
rsync -avz --delete "${EXCLUDES[@]}" ./ ${PI}:${TARGET_DIR}/

echo "Sync complete. You can SSH to the Pi and run:"
echo "  ssh ${PI}"
echo "  cd ${TARGET_DIR}"
echo "  source .venv/bin/activate  # if you created a venv on the Pi"
echo "  python3 src/keyboard_control.py"

# Note: If you prefer pulling from GitHub on the Pi, run there:
#   git pull <your-remote>
