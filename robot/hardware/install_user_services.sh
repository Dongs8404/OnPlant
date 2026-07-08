#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${HOME}/.config/onplant"
SYSTEMD_DIR="${HOME}/.config/systemd/user"

mkdir -p "${CONFIG_DIR}" "${SYSTEMD_DIR}"

if [ ! -f "${CONFIG_DIR}/onplant-robot.env" ]; then
  cp "${PROJECT_DIR}/onplant-robot.env.example" "${CONFIG_DIR}/onplant-robot.env"
  sed -i "s|ONPLANT_PROJECT_DIR=.*|ONPLANT_PROJECT_DIR=${PROJECT_DIR}|" "${CONFIG_DIR}/onplant-robot.env"
  echo "Created ${CONFIG_DIR}/onplant-robot.env"
  echo "Edit ONPLANT_SERVER if the server PC IP is different."
fi

cp "${PROJECT_DIR}/systemd/onplant-display.service" "${SYSTEMD_DIR}/onplant-display.service"
cp "${PROJECT_DIR}/systemd/onplant-drive.service" "${SYSTEMD_DIR}/onplant-drive.service"

systemctl --user daemon-reload
systemctl --user enable onplant-display.service

echo "Display service installed and enabled."
echo "Start display now:"
echo "  systemctl --user start onplant-display.service"
echo
echo "After lidar_fsm_drive.py is ready, enable drive:"
echo "  systemctl --user enable --now onplant-drive.service"
