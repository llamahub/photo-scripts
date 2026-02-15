#!/usr/bin/env python3
"""Business logic for linking the photo drive."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass
class LinkPhotoDriveResult:
    linked_to: str
    remote_mounted: bool


class LinkPhotoDrive:
    def __init__(
        self,
        logger,
        remote_host: str = "tigerserver",
        remote_path: str = "/mnt/photo_drive",
        remote_mount: str = "/mnt/photo_drive_remote",
        local_mount: str = "/mnt/photo_drive_local",
        link_path: str = "/mnt/photo_drive",
        dry_run: bool = False,
    ) -> None:
        self._logger = logger
        self._remote_host = remote_host
        self._remote_path = remote_path
        self._remote_mount = remote_mount
        self._local_mount = local_mount
        self._link_path = link_path
        self._dry_run = dry_run

    def _run_command(self, cmd: Sequence[str], check: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, check=check, capture_output=True, text=True)

    def _is_mounted(self, path: str) -> bool:
        result = self._run_command(["mountpoint", "-q", path])
        return result.returncode == 0

    def _ensure_dir(self, path: str) -> None:
        if os.path.isdir(path):
            return
        if self._dry_run:
            self._logger.info("DRY RUN: would create directory %s", path)
            return
        os.makedirs(path, exist_ok=True)

    def _link(self, target: str) -> None:
        if self._dry_run:
            self._logger.info("DRY RUN: would link %s -> %s", self._link_path, target)
            return

        if os.path.islink(self._link_path):
            os.unlink(self._link_path)
        elif os.path.exists(self._link_path):
            raise RuntimeError(f"Link path exists and is not a symlink: {self._link_path}")

        os.symlink(target, self._link_path)

    def _mount_remote(self) -> bool:
        self._ensure_dir(self._remote_mount)
        if self._is_mounted(self._remote_mount):
            return True

        if self._dry_run:
            self._logger.info(
                "DRY RUN: would mount %s:%s to %s",
                self._remote_host,
                self._remote_path,
                self._remote_mount,
            )
            return True

        result = self._run_command(
            [
                "sshfs",
                f"{self._remote_host}:{self._remote_path}",
                self._remote_mount,
                "-o",
                "allow_other,default_permissions,reconnect",
            ]
        )
        if result.returncode != 0:
            error = result.stderr.strip() or "sshfs failed"
            raise RuntimeError(error)
        return True

    def link_remote(self) -> LinkPhotoDriveResult:
        mounted = self._mount_remote()
        if mounted:
            self._link(self._remote_mount)
            return LinkPhotoDriveResult(linked_to=self._remote_mount, remote_mounted=True)
        raise RuntimeError("Remote mount not available")

    def link_local(self) -> LinkPhotoDriveResult:
        if not os.path.isdir(self._local_mount):
            raise RuntimeError(f"Local mount not available: {self._local_mount}")
        self._link(self._local_mount)
        return LinkPhotoDriveResult(linked_to=self._local_mount, remote_mounted=False)

    def link_auto(self) -> LinkPhotoDriveResult:
        try:
            result = self.link_remote()
            return result
        except Exception as exc:
            self._logger.warning("Remote mount failed: %s", exc)

        return self.link_local()
