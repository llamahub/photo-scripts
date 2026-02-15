#!/usr/bin/env python3
"""Tests for link_photo_drive script."""

from pathlib import Path
import importlib.util
import sys
import types
import pytest

# Add COMMON src to path for imports
immich_root = Path(__file__).parent.parent
sys.path.insert(0, str(immich_root.parent / "COMMON" / "src"))

script_path = immich_root / "scripts" / "link_photo_drive.py"
spec = importlib.util.spec_from_file_location("link_photo_drive_script", script_path)
link_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(link_script)

from common.argument_parser import ScriptArgumentParser


def test_script_info_fields():
    info = link_script.SCRIPT_INFO
    assert info["name"]
    assert info["description"]
    assert isinstance(info.get("examples"), list)


def test_script_arguments_required():
    args = link_script.SCRIPT_ARGUMENTS
    assert args["remote"]["flag"] == "--remote"
    assert args["local"]["flag"] == "--local"


def test_main_success_auto(monkeypatch, capsys):
    class MockLogger:
        def info(self, *_args, **_kwargs):
            return None

        def error(self, *_args, **_kwargs):
            return None

    class MockLinker:
        def __init__(self, *args, **kwargs):
            return None

        def link_auto(self):
            return types.SimpleNamespace(linked_to="/mnt/photo_drive_remote")

    def fake_setup_logging(self, _resolved_args, _script_name=None):
        return MockLogger()

    def fake_display_configuration(self, _resolved_args):
        return None

    monkeypatch.setattr(ScriptArgumentParser, "setup_logging", fake_setup_logging)
    monkeypatch.setattr(ScriptArgumentParser, "display_configuration", fake_display_configuration)
    monkeypatch.setattr(link_script, "LinkPhotoDrive", MockLinker)
    monkeypatch.setattr(sys, "argv", ["link_photo_drive.py"])

    link_script.main()
    output = capsys.readouterr().out
    assert "Linked /mnt/photo_drive" in output


def test_main_conflicting_flags(monkeypatch, capsys):
    class MockLogger:
        def info(self, *_args, **_kwargs):
            return None

        def error(self, *_args, **_kwargs):
            return None

    def fake_setup_logging(self, _resolved_args, _script_name=None):
        return MockLogger()

    def fake_display_configuration(self, _resolved_args):
        return None

    monkeypatch.setattr(ScriptArgumentParser, "setup_logging", fake_setup_logging)
    monkeypatch.setattr(ScriptArgumentParser, "display_configuration", fake_display_configuration)
    monkeypatch.setattr(sys, "argv", ["link_photo_drive.py", "--remote", "--local"])

    with pytest.raises(SystemExit):
        link_script.main()

    output = capsys.readouterr().out
    assert "ERROR" in output
