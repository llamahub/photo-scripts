"""
Shared argument parsing utilities for consistent CLI interfaces across all scripts.

This module provides a standardized approach to CLI argument parsing using
data-driven configuration. Scripts define their arguments in SCRIPT_INFO and
ARGUMENTS dictionaries, and this module automatically generates help text
and argument parsers.

Usage:
    from common.argument_parser import ScriptArgumentParser

    # Define script metadata and arguments
    SCRIPT_INFO = {
        'name': 'My Script',
        'description': 'What this script does',
        'examples': ['--input file.txt --output result.txt']
    }

    ARGUMENTS = {
        'input': {
            'positional': True,
            'help': 'Input file to process'
        },
        'verbose': {
            'short': '-v',
            'action': 'store_true',
            'help': 'Enable verbose output'
        }
    }

    # Create parser and use it
    script_parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    args = script_parser.parse_args()
"""

import argparse
import sys
from typing import Dict, Any, List


class ScriptArgumentParser:
    def error(self, message: str):
        """Print error message and exit with status 2 (like argparse default)."""
        print(f"❌ Error: {message}", file=sys.stderr)
        sys.exit(2)
    """
    Standardized argument parser that generates CLI interfaces from configuration.

    This class eliminates duplication by providing a single source of truth for
    argument definitions and automatically generating help text and parsers.
    """

    def __init__(self, script_info: Dict[str, Any], arguments: Dict[str, Any]):
        """
        Initialize the argument parser.

        Args:
            script_info: Dictionary containing script metadata:
                - name: Script name for display
                - description: Brief description of what script does
                - examples: List of usage examples
            arguments: Dictionary defining all CLI arguments:
                - Key is argument name
                - Value is dict with 'help', optional 'flag', 'short', 'action', etc.
        """
        self.script_info = script_info
        self.arguments = arguments
        self._parser = None

    def create_help_text(self) -> str:
        """
        Generate comprehensive help text from argument definitions.

        Returns:
            Formatted help text string showing usage patterns and examples.
        """
        lines = []
        lines.append("Usage patterns:")

        # Required arguments
        required_args = []
        for key, arg_def in self.arguments.items():
            if arg_def.get("required") or arg_def.get("positional"):
                if arg_def.get("positional"):
                    required_args.append(key.upper())
                else:
                    flag = arg_def.get("flag", f"--{key}")
                    required_args.append(f"{flag} VALUE")

        if required_args:
            lines.append(f"  %(prog)s {' '.join(required_args)} [OPTIONS]")
        else:
            lines.append("  %(prog)s [OPTIONS]")

        lines.append("")
        lines.append("Required arguments:")

        # Positional arguments
        for key, arg_def in self.arguments.items():
            if arg_def.get("positional"):
                lines.append(f"  {key.upper():<12} {arg_def['help']}")

        # Required named arguments
        for key, arg_def in self.arguments.items():
            if arg_def.get("required") and not arg_def.get("positional"):
                flag = arg_def.get("flag", f"--{key}")
                lines.append(f"  {flag} VALUE    {arg_def['help']}")

        lines.append("")
        lines.append("Optional arguments:")

        # Optional arguments (not flags)
        for key, arg_def in self.arguments.items():
            if not arg_def.get("required") and not arg_def.get("action"):
                flag = arg_def.get("flag", f"--{key}")
                metavar = flag.upper().replace("--", "").replace("-", "_")
                lines.append(f"  {flag} {metavar:<8} {arg_def['help']}")

        # Flags
        for key, arg_def in self.arguments.items():
            if arg_def.get("action"):
                flag_text = arg_def.get("flag", f"--{key}")
                if arg_def.get("short"):
                    flag_text += f", {arg_def['short']}"
                lines.append(f"  {flag_text:<14} {arg_def['help']}")

        lines.append("")
        lines.append("Examples:")
        for example in self.script_info["examples"]:
            lines.append(f"  %(prog)s {example}")

        return "\n".join(lines)

    def create_argument_parser(self) -> argparse.ArgumentParser:
        """
        Create and configure the argument parser from argument definitions.

        Returns:
            Configured ArgumentParser instance ready to parse command line arguments.
        """
        # Build description with help text
        full_description = f"""
{self.script_info['description']}

{self.create_help_text()}
"""

        parser = argparse.ArgumentParser(
            description=self.script_info["description"],
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=full_description,
        )

        # Add arguments based on definitions
        for key, arg_def in self.arguments.items():
            if arg_def.get("positional"):
                # Add positional argument
                parser.add_argument(key, nargs="?", help=arg_def["help"])
                # Add named alternative
                alt_help = f"{arg_def['help']} (alternative to positional)"
                parser.add_argument(f"--{key}", dest=f"{key}_file", help=alt_help)
            else:
                # Build argument parameters
                args = [arg_def.get("flag", f"--{key}")]
                if arg_def.get("short"):
                    args.append(arg_def["short"])

                kwargs = {"help": arg_def["help"]}

                if arg_def.get("dest"):
                    kwargs["dest"] = arg_def["dest"]
                if arg_def.get("action"):
                    kwargs["action"] = arg_def["action"]
                if arg_def.get("type"):
                    kwargs["type"] = arg_def["type"]
                if arg_def.get("default") is not None:
                    kwargs["default"] = arg_def["default"]
                if arg_def.get("choices"):
                    kwargs["choices"] = arg_def["choices"]
                if arg_def.get("required"):
                    kwargs["required"] = arg_def["required"]

                parser.add_argument(*args, **kwargs)

        return parser

    def parse_args(self, args: List[str] = None) -> argparse.Namespace:
        """
        Parse command line arguments using the configured parser.

        Args:
            args: Optional list of arguments to parse. If None, uses sys.argv.

        Returns:
            Parsed argument namespace.
        """
        if self._parser is None:
            self._parser = self.create_argument_parser()

        return self._parser.parse_args(args)

    def print_header(self) -> None:
        """Print a standardized script header using script info."""
        print("=" * 80)
        print(f"=== [{self.script_info['name']}] - {self.script_info['description']}")
        print("=" * 80)
        print()

    def validate_required_args(
        self, args: argparse.Namespace, required_mappings: Dict[str, List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate and resolve required arguments with positional/named alternatives.

        Args:
            args: Parsed argument namespace
            required_mappings: Dict mapping final arg names to list of possible sources
                Example: {'input_file': ['input_file', 'input']}

        Returns:
            Dictionary of resolved argument values

        Raises:
            SystemExit: If required arguments are missing
        """
        if required_mappings is None:
            return vars(args)

        resolved = {}
        missing = []

        for final_name, sources in required_mappings.items():
            value = None
            for source in sources:
                value = getattr(args, source, None)
                if value:
                    break

            if value:
                resolved[final_name] = value
            else:
                missing.append(final_name)

        if missing:
            missing_str = ", ".join(missing)
            print(f"❌ Error: Required arguments missing: {missing_str}")
            sys.exit(1)

        # Add all other arguments
        for key, value in vars(args).items():
            # Check if this key is not in any of the required mapping sources
            all_sources = [
                source for sources in required_mappings.values() for source in sources
            ]
            if key not in all_sources:
                resolved[key] = value

        return resolved

    def setup_logging(self, resolved_args: Dict[str, Any], script_name: str = None):
        """
        Setup logging with consistent pattern using ScriptLogging or fallback.

        Args:
            resolved_args: Dictionary of resolved arguments
            script_name: Optional script name for fallback logger

        Returns:
            Configured logger instance
        """
        debug_mode = resolved_args.get("verbose") and not resolved_args.get("quiet")

        try:
            from common.logging import ScriptLogging

            # Generate proper script name with timestamp if provided
            if script_name:
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                full_script_name = f"{script_name}_{timestamp}"
            else:
                full_script_name = None

            logger = ScriptLogging.get_script_logger(
                name=full_script_name, debug=debug_mode
            )
        except ImportError:
            # Fallback logging setup
            import logging

            level = logging.DEBUG if debug_mode else logging.INFO
            log_format = "%(asctime)s - %(levelname)s - %(message)s"
            logging.basicConfig(level=level, format=log_format)
            logger_name = script_name or "script"
            logger = logging.getLogger(logger_name)

        return logger

    def display_configuration(
        self, resolved_args: Dict[str, Any], config_map: Dict[str, str] = None
    ) -> None:
        """
        Display script configuration if not in quiet mode.

        Args:
            resolved_args: Dictionary of resolved arguments
            config_map: Optional mapping of arg keys to display labels
                       If None, uses standard mapping for common args
        """
        if resolved_args.get("quiet"):
            return

        # Default configuration mapping for common arguments
        if config_map is None:
            config_map = {
                "input_file": "Input file",
                "output_file": "Output file",
                "source_dir": "Source directory",
                "target_dir": "Target directory",
            }

        # Display main configuration
        for arg_key, display_label in config_map.items():
            value = resolved_args.get(arg_key)
            if value:
                print(f"{display_label}: {value}")

        # Special handling for dry run mode
        if resolved_args.get("dry_run"):
            print("Mode: DRY RUN (simulation only)")

        print()


def create_standard_arguments() -> Dict[str, Any]:
    """
    Create a standard set of common arguments used across many scripts.

    Scripts can use this as a base and add their specific arguments.

    Returns:
        Dictionary of standard argument definitions.
    """
    return {
        "verbose": {
            "short": "-v",
            "action": "store_true",
            "help": "Enable verbose/debug output",
        },
        "quiet": {
            "short": "-q",
            "action": "store_true",
            "help": "Suppress non-error output",
        },
        "dry_run": {
            "flag": "--dry-run",
            "action": "store_true",
            "help": "Show what would be done without making changes",
        },
    }


def merge_arguments(*arg_dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple argument dictionaries, with later ones taking precedence.

    Args:
        *arg_dicts: Variable number of argument dictionaries to merge

    Returns:
        Merged argument dictionary
    """
    result = {}
    for arg_dict in arg_dicts:
        result.update(arg_dict)
    return result
