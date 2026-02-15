#!/usr/bin/env bash
set -euo pipefail

./setup-system-deps.sh

# Set up SSH keys from host FIRST (needed for SSHFS)
if [ -d /root/.ssh-host ]; then
	echo "Setting up SSH keys from host..."
	mkdir -p /root/.ssh
	cp -r /root/.ssh-host/* /root/.ssh/ 2>/dev/null || true
	chmod 700 /root/.ssh
	chmod 600 /root/.ssh/id_* 2>/dev/null || true
	chmod 644 /root/.ssh/id_*.pub 2>/dev/null || true
	chmod 644 /root/.ssh/known_hosts 2>/dev/null || true
	chmod 600 /root/.ssh/config 2>/dev/null || true
	echo "✓ SSH keys configured"
fi

# Set timezone
ln -snf /usr/share/zoneinfo/America/New_York /etc/localtime
echo America/New_York | tee /etc/timezone

