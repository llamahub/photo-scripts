Devcontainer share mounts

This devcontainer mounts both a network share and a local fallback, then creates
the /mnt/photo_drive symlink inside the container based on what’s available.

Photo drive mounts
- Host: /Volumes/photo_drive → Container: /mnt/photo_drive_remote
- Host: ${HOME}/Pictures → Container: /mnt/photo_drive_local

Symlink behavior (inside container)
- If /mnt/photo_drive_remote exists, /mnt/photo_drive points to it.
- Otherwise /mnt/photo_drive points to /mnt/photo_drive_local.

Additional mount
- Host: ${HOME}/Movies → Container: /media/Movies

Notes
- Ensure the host paths exist before rebuilding the container.
- The container always uses /mnt/photo_drive, so scripts don’t need to change.
