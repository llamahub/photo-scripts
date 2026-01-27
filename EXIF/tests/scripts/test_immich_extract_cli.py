import subprocess
import sys
import os
from pathlib import Path
import unittest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "immich_extract.py"


class TestImmichExtractCLI(unittest.TestCase):
    def run_cli(self, args, env=None):
        cmd = [sys.executable, str(SCRIPT_PATH)] + args
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        return result

    def test_help(self):
        result = self.run_cli(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("immich", result.stdout.lower())
        self.assertIn("search-path", result.stdout)

    def test_missing_required(self):
        result = self.run_cli([])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("search-path", result.stderr + result.stdout)

    def test_invalid_combo(self):
        # Both --search and --album not allowed, should error on mutually exclusive arguments
        result = self.run_cli(["--search", "--album", "foo", "--search-path", "/tmp"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "you cannot specify both --album and --search",
            (result.stdout + result.stderr).lower(),
        )

    def test_minimal_search(self):
        # Should fail due to missing required arguments, not missing config
        env = os.environ.copy()
        env["IMMICH_URL"] = "http://dummy"
        env["IMMICH_API_KEY"] = "dummykey"
        result = self.run_cli(["--search", "--search-path", "/tmp"], env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "required arguments missing", (result.stdout + result.stderr).lower()
        )

    def test_disable_sidecars_flag_recognized(self):
        """Test that --disable-sidecars flag is recognized in help"""
        result = self.run_cli(["--help"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("disable-sidecars", result.stdout)
        self.assertIn("sidecar", result.stdout.lower())

    def test_disable_sidecars_with_search(self):
        """Test --disable-sidecars with --search flag"""
        env = os.environ.copy()
        env["IMMICH_URL"] = "http://dummy"
        env["IMMICH_API_KEY"] = "dummykey"
        result = self.run_cli([
            "--search", 
            "--search-path", "/tmp",
            "--disable-sidecars"
        ], env=env)
        # Should fail due to missing --updatedAfter, not due to --disable-sidecars
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "required arguments missing", (result.stdout + result.stderr).lower()
        )

    def test_disable_sidecars_with_album(self):
        """Test --disable-sidecars with --album flag"""
        env = os.environ.copy()
        env["IMMICH_URL"] = "http://dummy"
        env["IMMICH_API_KEY"] = "dummykey"
        result = self.run_cli([
            "--album", "test-album-id",
            "--search-path", "/tmp",
            "--disable-sidecars"
        ], env=env)
        # Should fail due to missing Immich connection, not due to --disable-sidecars
        # (The flag should be parsed successfully)
        self.assertNotEqual(result.returncode, 0)
        # The error should be about connection, not parsing
        output = result.stdout + result.stderr
        self.assertTrue(
            "connection" in output.lower() or 
            "url" in output.lower() or
            "immich" in output.lower() or
            "failed" in output.lower()
        )

    def test_disable_sidecars_dry_run_combination(self):
        """Test --disable-sidecars with --dry-run flag"""
        env = os.environ.copy()
        env["IMMICH_URL"] = "http://dummy"
        env["IMMICH_API_KEY"] = "dummykey"
        result = self.run_cli([
            "--search", 
            "--search-path", "/tmp",
            "--disable-sidecars",
            "--dry-run",
            "--updatedAfter", "2025-01-01T00:00:00Z"
        ], env=env)
        # The flag combination is valid, so either success or connection error is acceptable
        # The important thing is that --disable-sidecars doesn't cause a parsing error
        output = result.stdout + result.stderr
        self.assertNotIn("unrecognized arguments", output.lower())
        self.assertNotIn("disable-sidecars", output.lower())  # Not an error about the flag itself


if __name__ == "__main__":
    unittest.main()
