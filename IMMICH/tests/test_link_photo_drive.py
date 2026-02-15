#!/usr/bin/env python3
"""Tests for link_photo_drive business logic."""

from pathlib import Path
import sys
import types
import pytest

# Add IMMICH src to path for imports
immich_root = Path(__file__).parent.parent
sys.path.insert(0, str(immich_root / "src"))

from link_photo_drive import LinkPhotoDrive


class DummyLogger:
    def __init__(self):
        self.messages = []

    def info(self, message, *args):
        self.messages.append(("info", message % args if args else message))

    def warning(self, message, *args):
        self.messages.append(("warning", message % args if args else message))

    def error(self, message, *args):
        self.messages.append(("error", message % args if args else message))


class FakeResult:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


def test_link_remote_success(tmp_path, monkeypatch):
    logger = DummyLogger()
    remote_mount = tmp_path / "remote"
    local_mount = tmp_path / "local"
    link_path = tmp_path / "link"

    linker = LinkPhotoDrive(
        logger=logger,
        remote_mount=str(remote_mount),
        local_mount=str(local_mount),
        link_path=str(link_path),
    )

    def fake_run(_self, cmd, check=False):
        if cmd[:2] == ["mountpoint", "-q"]:
            return FakeResult(returncode=1)
        return FakeResult(returncode=0)

    monkeypatch.setattr(LinkPhotoDrive, "_run_command", types.MethodType(fake_run, linker))

    result = linker.link_remote()
    assert Path(result.linked_to).resolve() == remote_mount
    assert link_path.is_symlink()


def test_link_remote_failure(tmp_path, monkeypatch):
    logger = DummyLogger()
    remote_mount = tmp_path / "remote"
    link_path = tmp_path / "link"

    linker = LinkPhotoDrive(
        logger=logger,
        remote_mount=str(remote_mount),
        link_path=str(link_path),
    )

    def fake_run(_self, cmd, check=False):
        if cmd[:2] == ["mountpoint", "-q"]:
            return FakeResult(returncode=1)
        return FakeResult(returncode=1, stderr="no such file")

    monkeypatch.setattr(LinkPhotoDrive, "_run_command", types.MethodType(fake_run, linker))

    with pytest.raises(RuntimeError):
        linker.link_remote()


def test_link_local_success(tmp_path):
    logger = DummyLogger()
    local_mount = tmp_path / "local"
    local_mount.mkdir()
    link_path = tmp_path / "link"

    linker = LinkPhotoDrive(
        logger=logger,
        local_mount=str(local_mount),
        link_path=str(link_path),
    )

    result = linker.link_local()
    assert Path(result.linked_to).resolve() == local_mount
    assert link_path.is_symlink()


def test_link_auto_falls_back_to_local(tmp_path, monkeypatch):
    logger = DummyLogger()
    remote_mount = tmp_path / "remote"
    local_mount = tmp_path / "local"
    local_mount.mkdir()
    link_path = tmp_path / "link"

    linker = LinkPhotoDrive(
        logger=logger,
        remote_mount=str(remote_mount),
        local_mount=str(local_mount),
        link_path=str(link_path),
    )

    def fake_run(_self, cmd, check=False):
        if cmd[:2] == ["mountpoint", "-q"]:
            return FakeResult(returncode=1)
        return FakeResult(returncode=1, stderr="no such file")

    monkeypatch.setattr(LinkPhotoDrive, "_run_command", types.MethodType(fake_run, linker))

    result = linker.link_auto()
    assert Path(result.linked_to).resolve() == local_mount
    assert link_path.is_symlink()
