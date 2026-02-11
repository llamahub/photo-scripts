#!/usr/bin/env bash
set -euo pipefail

./setup-system-deps.sh

if [ -d /mnt/photo_drive_remote ]; then
	ln -sfn /mnt/photo_drive_remote /mnt/photo_drive
elif [ -d /mnt/photo_drive_local ]; then
	ln -sfn /mnt/photo_drive_local /mnt/photo_drive
fi

ln -snf /usr/share/zoneinfo/America/New_York /etc/localtime
echo America/New_York | tee /etc/timezone
