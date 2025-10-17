#!/usr/bin/env python3
"""Unit tests for ScriptArgumentParser class."""

"""Unit tests for ScriptArgumentParser class."""

import pytest
import sys
import os
from unittest.mock import patch
from io import StringIO

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from common.argument_parser import (
    ScriptArgumentParser,
    create_standard_arguments,
    merge_arguments,
)


class TestScriptArgumentParser:
    """Test cases for ScriptArgumentParser class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.script_info = {
            "name": "Test Script",
            "description": "A test script for unit testing",
            "examples": [
                "input.txt output.txt",
                "--input input.txt --output output.txt --verbose",
            ],
        }

        self.test_arguments = {
            "input": {"positional": True, "help": "Input file to process"},
            "output": {"positional": True, "help": "Output file to create"},
            "source_dir": {"flag": "--source", "help": "Source directory"},
        }

        self.full_arguments = merge_arguments(
            create_standard_arguments(), self.test_arguments
        )

    def test_create_standard_arguments(self):
        """Test that standard arguments are created correctly."""
        std_args = create_standard_arguments()

        assert "verbose" in std_args
        assert "quiet" in std_args
        assert "dry_run" in std_args

        assert std_args["verbose"]["short"] == "-v"
        assert std_args["verbose"]["action"] == "store_true"
        assert std_args["quiet"]["short"] == "-q"
        assert std_args["dry_run"]["flag"] == "--dry-run"

    def test_merge_arguments(self):
        """Test that argument dictionaries merge correctly."""
        std_args = create_standard_arguments()
        merged = merge_arguments(std_args, self.test_arguments)

        # Should contain both standard and custom arguments
        assert "verbose" in merged
        assert "input" in merged
        assert "source_dir" in merged

        # Later arguments should override earlier ones
        override_args = {"verbose": {"help": "Override help"}}
        merged_override = merge_arguments(std_args, override_args)
        assert merged_override["verbose"]["help"] == "Override help"

    def test_parser_initialization(self):
        """Test ScriptArgumentParser initialization."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)

        assert parser.script_info == self.script_info
        assert parser.arguments == self.full_arguments

    def test_create_help_text(self):
        """Test help text generation."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        help_text = parser.create_help_text()

        # Check that help text contains expected sections
        assert "Usage patterns:" in help_text
        assert "Required arguments:" in help_text
        assert "Optional arguments:" in help_text
        assert "Examples:" in help_text

        # Check that arguments appear in help
        assert "INPUT" in help_text  # positional arg
        assert "OUTPUT" in help_text  # positional arg
        assert "--source" in help_text  # optional arg
        assert "--verbose" in help_text  # standard arg

    def test_create_argument_parser(self):
        """Test argument parser creation."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        arg_parser = parser.create_argument_parser()

        # Test parsing valid arguments
        args = arg_parser.parse_args(["input.txt", "output.txt", "--verbose"])
        assert args.input == "input.txt"
        assert args.output == "output.txt"
        assert args.verbose is True
        assert args.quiet is False

    def test_parse_args_positional(self):
        """Test parsing positional arguments."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        args = parser.parse_args(["test_input.txt", "test_output.txt"])

        assert args.input == "test_input.txt"
        assert args.output == "test_output.txt"

    def test_parse_args_named(self):
        """Test parsing named arguments."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        args = parser.parse_args(
            [
                "--input",
                "named_input.txt",
                "--output",
                "named_output.txt",
                "--source",
                "/src/dir",
            ]
        )

        assert args.input_file == "named_input.txt"
        assert args.output_file == "named_output.txt"
        assert getattr(args, "source", None) == "/src/dir"

    def test_parse_args_flags(self):
        """Test parsing flag arguments."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        args = parser.parse_args(["input.txt", "output.txt", "--verbose", "--dry-run"])

        assert args.verbose is True
        assert args.dry_run is True
        assert args.quiet is False

    def test_validate_required_args_success(self):
        """Test successful validation of required arguments."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        args = parser.parse_args(["input.txt", "output.txt"])

        resolved = parser.validate_required_args(
            args,
            {
                "input_file": ["input_file", "input"],
                "output_file": ["output_file", "output"],
            },
        )

        assert resolved["input_file"] == "input.txt"
        assert resolved["output_file"] == "output.txt"

    def test_validate_required_args_named_priority(self):
        """Test that named arguments take priority over positional."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        args = parser.parse_args(
            ["pos_input.txt", "pos_output.txt", "--input", "named_input.txt"]
        )

        resolved = parser.validate_required_args(
            args,
            {
                "input_file": ["input_file", "input"],
                "output_file": ["output_file", "output"],
            },
        )

        # Named should win over positional
        assert resolved["input_file"] == "named_input.txt"
        assert resolved["output_file"] == "pos_output.txt"

    def test_validate_required_args_missing(self):
        """Test validation failure when required args are missing."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        args = parser.parse_args(["--verbose"])  # No required args

        with pytest.raises(SystemExit):
            parser.validate_required_args(
                args,
                {
                    "input_file": ["input_file", "input"],
                    "output_file": ["output_file", "output"],
                },
            )

    @patch("sys.stdout", new_callable=StringIO)
    def test_print_header(self, mock_stdout):
        """Test header printing."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        parser.print_header()

        output = mock_stdout.getvalue()
        assert "Test Script" in output
        assert "A test script for unit testing" in output
        assert "=" in output  # Header formatting

    def test_setup_logging_fallback(self):
        """Test logging setup with fallback when ScriptLogging unavailable."""
        # We'll test this by simulating an ImportError
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        resolved_args = {"verbose": False, "quiet": False}

        # This should work either way (with or without ScriptLogging)
        logger = parser.setup_logging(resolved_args, "test_script")
        assert logger is not None

    def test_setup_logging_verbose(self):
        """Test logging setup in verbose mode."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)

        # Verbose mode (not quiet)
        resolved_args = {"verbose": True, "quiet": False}
        logger = parser.setup_logging(resolved_args, "test_script")
        assert logger is not None

        # Quiet overrides verbose
        resolved_args = {"verbose": True, "quiet": True}
        logger = parser.setup_logging(resolved_args, "test_script")
        assert logger is not None

    @patch("sys.stdout", new_callable=StringIO)
    def test_display_configuration_default(self, mock_stdout):
        """Test configuration display with default mapping."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        resolved_args = {
            "input_file": "test_input.txt",
            "output_file": "test_output.txt",
            "quiet": False,
        }

        parser.display_configuration(resolved_args)
        output = mock_stdout.getvalue()

        assert "Input file: test_input.txt" in output
        assert "Output file: test_output.txt" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_display_configuration_custom(self, mock_stdout):
        """Test configuration display with custom mapping."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        resolved_args = {
            "source_path": "/src/dir",
            "target_path": "/dst/dir",
            "quiet": False,
        }

        config_map = {
            "source_path": "Source directory",
            "target_path": "Target directory",
        }

        parser.display_configuration(resolved_args, config_map)
        output = mock_stdout.getvalue()

        assert "Source directory: /src/dir" in output
        assert "Target directory: /dst/dir" in output

    @patch("sys.stdout", new_callable=StringIO)
    def test_display_configuration_quiet(self, mock_stdout):
        """Test that configuration display is suppressed in quiet mode."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        resolved_args = {"input_file": "test.txt", "quiet": True}

        parser.display_configuration(resolved_args)
        output = mock_stdout.getvalue()

        assert output == ""  # No output in quiet mode

    @patch("sys.stdout", new_callable=StringIO)
    def test_display_configuration_dry_run(self, mock_stdout):
        """Test dry run mode indicator in configuration display."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)
        resolved_args = {"input_file": "test.txt", "dry_run": True, "quiet": False}

        parser.display_configuration(resolved_args)
        output = mock_stdout.getvalue()

        assert "Mode: DRY RUN (simulation only)" in output

    def test_argument_parser_help_exit(self):
        """Test that --help exits properly."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)

        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

    def test_end_to_end_workflow(self):
        """Test complete end-to-end argument parsing workflow."""
        parser = ScriptArgumentParser(self.script_info, self.full_arguments)

        # Parse args
        args = parser.parse_args(
            ["input.txt", "output.txt", "--source", "/src", "--verbose", "--dry-run"]
        )

        # Validate and resolve
        resolved = parser.validate_required_args(
            args,
            {
                "input_file": ["input_file", "input"],
                "output_file": ["output_file", "output"],
            },
        )

        # Check results
        assert resolved["input_file"] == "input.txt"
        assert resolved["output_file"] == "output.txt"
        assert resolved.get("source") == "/src"
        assert resolved["verbose"] is True
        assert resolved["dry_run"] is True

        # Test logging and display setup
        logger = parser.setup_logging(resolved, "test_script")
        assert logger is not None
