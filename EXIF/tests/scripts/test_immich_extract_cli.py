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


if __name__ == "__main__":
    unittest.main()
