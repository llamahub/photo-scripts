---
mode: agent
---

consider these documens:

COMMON/ARCHITECTURE.md
COMMON/README.md
.vscode/ai-assistant-prompt.md
EXIF/TESTING_STRATEGY.md

Create a script COMMON/scripts/clean.py with these arguments:

--target : 1st positional/named - path to targert folder
--mac : if inluded then all apple generateed files: .DS_Store, ._* will be deleted
--empty : if included then all empty folders will be deleted
--log : all .log files


