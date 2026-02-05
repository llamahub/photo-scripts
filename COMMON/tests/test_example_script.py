#!/usr/bin/env python3
"""Tests for example_script.py."""

import sys
from pathlib import Path
import pytest

# Add COMMON src and scripts to path for imports
common_root = Path(__file__).parent.parent
sys.path.insert(0, str(common_root / "src"))
sys.path.insert(0, str(common_root / "scripts"))

import example_script
from common.argument_parser import ScriptArgumentParser


def test_script_info_fields():
    """Ensure SCRIPT_INFO contains required fields."""
    info = example_script.SCRIPT_INFO
    assert info["name"]
    assert info["description"]
    assert isinstance(info.get("examples"), list)
    assert len(info["examples"]) > 0


def test_script_arguments_required():
    """Ensure required args are both positional and named."""
    args = example_script.SCRIPT_ARGUMENTS
    assert args["input"]["positional"] is True
    assert args["input"]["flag"] == "--input"
    assert args["output"]["positional"] is True
    assert args["output"]["flag"] == "--output"


def test_parse_required_positional():
    """Ensure positional required args resolve correctly."""
    parser = ScriptArgumentParser(example_script.SCRIPT_INFO, example_script.ARGUMENTS)
    args = parser.parse_args(["input.csv", "output.csv"])
    resolved = parser.validate_required_args(
        args,
        {
            "input": ["input", "input_file"],
            "output": ["output", "output_file"],
        },
    )

    assert resolved["input"] == "input.csv"
    assert resolved["output"] == "output.csv"


def test_parse_required_named():
    """Ensure named required args resolve correctly."""
    parser = ScriptArgumentParser(example_script.SCRIPT_INFO, example_script.ARGUMENTS)
    args = parser.parse_args(["--input", "input.csv", "--output", "output.csv"])
    resolved = parser.validate_required_args(
        args,
        {
            "input": ["input", "input_file"],
            "output": ["output", "output_file"],
        },
    )

    assert resolved["input"] == "input.csv"
    assert resolved["output"] == "output.csv"


def test_main_success(monkeypatch, capsys):
    """Ensure main() runs successfully with required args."""
    class MockLogger:
        def info(self, *_args, **_kwargs):
            return None

        def debug(self, *_args, **_kwargs):
            return None

        def error(self, *_args, **_kwargs):
            return None

    def fake_setup_logging(self, _resolved_args, _script_name=None):
        return MockLogger()

    def fake_display_configuration(self, _resolved_args):
        return None

    monkeypatch.setattr(ScriptArgumentParser, "setup_logging", fake_setup_logging)
    monkeypatch.setattr(ScriptArgumentParser, "display_configuration", fake_display_configuration)
    monkeypatch.setattr(sys, "argv", ["example_script.py", "--input", "in.csv", "--output", "out.csv"])

    example_script.main()
    output = capsys.readouterr().out
    assert "Processing completed successfully" in output


def test_main_error(monkeypatch, capsys):
    """Ensure main() handles errors and exits non-zero."""
    class MockLogger:
        def info(self, *_args, **_kwargs):
            raise RuntimeError("boom")

        def debug(self, *_args, **_kwargs):
            return None

        def error(self, *_args, **_kwargs):
            return None

    def fake_setup_logging(self, _resolved_args, _script_name=None):
        return MockLogger()

    def fake_display_configuration(self, _resolved_args):
        return None

    monkeypatch.setattr(ScriptArgumentParser, "setup_logging", fake_setup_logging)
    monkeypatch.setattr(ScriptArgumentParser, "display_configuration", fake_display_configuration)
    monkeypatch.setattr(sys, "argv", ["example_script.py", "--input", "in.csv", "--output", "out.csv"])

    with pytest.raises(SystemExit):
        example_script.main()

    output = capsys.readouterr().out
    assert "Error:" in output
