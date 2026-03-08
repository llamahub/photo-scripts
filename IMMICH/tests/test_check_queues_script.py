"""Tests for check_queues.py script."""

import subprocess
import sys
from pathlib import Path


def test_help_output():
    result = subprocess.run(
        [sys.executable, "scripts/check_queues.py", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    assert result.returncode == 0
    assert "Check Queues" in result.stdout
    assert "--verbose" in result.stdout
    assert "--wait" in result.stdout


def test_missing_immich_config():
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        return
    result = subprocess.run(
        [sys.executable, "scripts/check_queues.py"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        env={"PATH": subprocess.os.environ.get("PATH", "")},
    )

    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "Immich URL" in output or "API" in output
