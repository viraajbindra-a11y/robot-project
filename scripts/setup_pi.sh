#!/usr/bin/env bash
# Comprehensive Raspberry Pi bootstrap script for the humanoid robot project.
# Safe to rerun; performs idempotent setup of system packages, Python tooling,
# audio stack, and useful services.

set -euo pipefail

#--------------- helper functions ---------------#
log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

die() {
  printf '\n[ERROR] %s\n' "$*" >&2
  exit 1
}

require_root() {
  if [[ $(id -u) -ne 0 ]]; then
    die "Please run this script with sudo: sudo ./scripts/setup_pi.sh"
  fi
}

#--------------- configuration ---------------#
PROJECT_DIR=${PROJECT_DIR:-/home/pi/robot-project}
PYTHON_BIN=${PYTHON_BIN:-python3}
VENV_DIR=${VENV_DIR:-$PROJECT_DIR/.venv}
REQUIREMENTS_FILE=${REQUIREMENTS_FILE:-$PROJECT_DIR/requirements.txt}
EXTRA_PACKAGES=(git rsync python3 python3-venv python3-dev build-essential libportaudio2)
GPIO_PACKAGES=(python3-rpi.gpio python3-gpiozero)
AUDIO_PACKAGES=(alsa-utils sox pulseaudio python3-pyaudio)
VISION_PACKAGES=(python3-opencv)

#--------------- main steps ---------------#
require_root

log "Updating apt package index"
apt update

log "Upgrading existing packages"
DEBIAN_FRONTEND=noninteractive apt -y upgrade

log "Installing base packages: ${EXTRA_PACKAGES[*]}"
DEBIAN_FRONTEND=noninteractive apt -y install "${EXTRA_PACKAGES[@]}"

log "Installing GPIO packages: ${GPIO_PACKAGES[*]}"
DEBIAN_FRONTEND=noninteractive apt -y install "${GPIO_PACKAGES[@]}"

log "Installing audio packages: ${AUDIO_PACKAGES[*]}"
DEBIAN_FRONTEND=noninteractive apt -y install "${AUDIO_PACKAGES[@]}"

log "Installing vision packages: ${VISION_PACKAGES[*]}"
DEBIAN_FRONTEND=noninteractive apt -y install "${VISION_PACKAGES[@]}"

if ! id -u pi >/dev/null 2>&1; then
  log "User 'pi' not present; creating minimal user"
  adduser --disabled-password --gecos "" pi || true
fi

log "Ensuring project directory $PROJECT_DIR exists"
mkdir -p "$PROJECT_DIR"
chown -R pi:pi "$PROJECT_DIR"

log "Setting up Python virtual environment at $VENV_DIR"
sudo -u pi "$PYTHON_BIN" -m venv "$VENV_DIR"

log "Installing Python requirements"
sudo -u pi "$VENV_DIR/bin/pip" install --upgrade pip
if [[ -f "$REQUIREMENTS_FILE" ]]; then
  sudo -u pi "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE"
else
  log "No requirements.txt found at $REQUIREMENTS_FILE; skipping"
fi

log "Configuring ALSA default sound card (if not already set)"
cat <<'ALSA' >/etc/asound.conf
pcm.!default {
  type plug
  slave.pcm "hw:1,0"
}
ctl.!default {
  type hw
  card 1
}
ALSA

log "Enabling I2C and SPI interfaces (needed for some sensors)"
raspi-config nonint do_i2c 0 || true
raspi-config nonint do_spi 0 || true

log "Disabling onboard audio power saving to avoid pops"
if ! grep -q 'snd_bcm2835.enable_headphones=1' /boot/config.txt 2>/dev/null; then
  echo 'snd_bcm2835.enable_headphones=1' >> /boot/config.txt
fi

log "Setup complete. Recommended next steps:"
printf '  sudo reboot\n'
printf '  sudo raspi-config to adjust locale/timezone if needed\n'
printf '  After reboot: source %s/bin/activate\n' "$VENV_DIR"
printf '  Run python3 src/keyboard_control.py --simulate\n'
