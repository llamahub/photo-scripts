import importlib
import pkgutil
import inspect
import sys
from pathlib import Path

SRC_COMMON_PATH = Path(__file__).parent.parent / "src" / "common"

MODULE_DESCRIPTIONS = {
    "config": "Configuration management using Pydantic and dotenv.",
    "logging": "Centralized logging setup and logger utilities.",
    "utils": "General utility functions for common tasks.",
}

def main():
    sys.path.insert(0, str(SRC_COMMON_PATH.parent.parent))  # Add project root to sys.path
    print("Modules in src/common:")
    for module_info in pkgutil.iter_modules([str(SRC_COMMON_PATH)]):
        name = module_info.name
        desc = MODULE_DESCRIPTIONS.get(name, "No description available.")
        print(f"- {name}: {desc}")
        # Optionally, print docstring from the module
        try:
            mod = importlib.import_module(f"src.common.{name}")
            doc = inspect.getdoc(mod)
            if doc:
                print(f"    Doc: {doc.splitlines()[0]}")
        except Exception as e:
            print(f"    (Could not import: {e})")

if __name__ == "__main__":
    main()
