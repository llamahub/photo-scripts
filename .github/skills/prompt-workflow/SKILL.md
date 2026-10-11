---
name: prompt-workflow
description: Use whenever the user requests a new feature, enhancement or other non-trivial change, and whenever continuing work tracked in a .github/prompts/*.md file. Creates a timestamped prompt file with a summary, assumptions and numbered clarifications, waits for the go-ahead, then implements test-first and logs work and test evidence to the file.
---

# Prompt workflow

New features and non-trivial changes get their own prompt file. Quick fixes, questions, and follow-ups on work that already has a prompt file go in that file's work log instead.

## 1. Intake: new request
1. Put the file in the repo the work mainly targets. Work that spans several repos goes in the coordinating repo (e.g. `server-app-dev`). In a monorepo whose subprojects have their own `.github/prompts/`, use the subproject's folder, or the root one if the work spans subprojects.
2. Name it `.github/prompts/YYYY-MM-DD_HHMM_<kebab-slug>.md`, taking the time from `date +%Y-%m-%d_%H%M`.
3. Sections, in order:
   - Front matter: `status: open` between `---` lines.
   - `# <Title>`
   - `## Request`: the user's words, verbatim, as a blockquote.
   - `## Summary`: your understanding of what is required and any analysis. Succinct, but enough to be useful later. End with **Assumptions** as bullets.
   - Task-specific detail (`## Plan`, `## Current state`, `## Options`…), as needed.
   - `## Clarifications`: always the last section before the work log, so the user can scroll straight to it. See format below. Omit if there are genuinely none.
   - `## Work log`: the first entry records creating the file.
4. Regenerate the index (see Status and index).
5. Stop. Reply with the file link and the number of clarifications. Do not implement.

## Clarification format
- As few as possible. Ask only what changes direction, complexity, quality or time. Turn everything else into a stated assumption.
- Number them. Keep each item short. Give lettered options a), b), c) or a yes/no question. Bold the recommended option and give a one-line reason.
- After each item: a blank line, a `>` line indented to the list item, then a blank line.

```markdown
1. **Short question?** One line of context if needed.
   - **a) Option (recommended).** Why.
   - b) Option.

   >

2. **Next question?**
```

## 2. Refine: after answers
- Read the answers on the `>` lines. Update Summary and Plan to match, and record decisions in the work log.
- Follow-up questions get the next numbers. Never renumber items that have been answered.

## 3. Implement: only after an explicit go-ahead
- Set `status: in-progress`.
- TDD: write a failing test, run it and see it fail, implement, then run it and see it pass. Refactor with the tests green. For docs/config-only work, write the verification check first.
- Append to `## Work log` after each unit of work, not only at the end, in chronological order: `### YYYY-MM-DD HH:MM TZ: <what>` (time from `date`). Record:
  - changes per repo
  - significant test evidence: the command, the red→green result, and pass counts
  - anything noticed but not changed
  - commit status
- Do not commit or push unless the user asks.
- When the work is complete and logged, set `status: done`.

## Status and index
- `status:` is one of:
  - `open`: awaiting answers or the go-ahead.
  - `in-progress`: the go-ahead has been given.
  - `done`: complete and logged.
  - `parked`: deferred by the user.
  - `reference`: a living document, not a work item (a backlog, a workflow doc, a reusable prompt).
- After any status change or new file, run `python3 .github/skills/prompt-workflow/scripts/build_index.py` from the repo root. It rewrites every `.github/prompts/README.md`: files grouped by status (in-progress, open, parked, reference, done), each with its date, a link, its title and its count of unanswered clarifications.
- `--check` verifies statuses and indexes without writing.
- Never edit `README.md` by hand.
