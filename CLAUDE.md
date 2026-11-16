## Compound Engineering

This repo is set up for the Compound Engineering skills. Team settings live in `.compound-engineering/config.yaml`. Documented solutions to past problems (bugs, best practices, workflow patterns) live in `docs/solutions/`, organized by category with YAML frontmatter (`module`, `tags`, `problem_type`), and are relevant when implementing or debugging in a documented area.

Issues live in GitHub Issues, managed with the `gh` CLI.

## Domain docs

The product, the code and the docs are in French. Write every new doc in French, Compound Engineering artifacts included, and follow the format of the file you add to.

- `GLOSSARY.md`: the domain vocabulary, under `## Langage`. Read it before working in an area. When a plan, issue, commit or test names a domain concept, use the glossary's term, never a synonym listed under `_À éviter_`. A concept missing from it gets an entry rather than a new word.
- `docs/adr/`: the decisions, numbered `NNNN-titre.md`. Read the ADRs that touch the area before planning or changing it. When a change contradicts one, say so explicitly and why it is worth reopening; never override it silently.
- `docs/sources.md`: the inventory of data sources (used, rejected, not found) with their access path. Read it before adding, changing or debugging a source; update it when a source changes.
- `docs/recherche/`: research notes, one per question, each tied to the issue that asked it.
- `docs/feuille-de-route.md` (temporary): milestones J0–J7, phase 2, backlog and the owner's actions, until they move to GitHub milestones and issues.

## Code standards

- `CODING_STANDARDS.md`: the rules code in this repo follows, each with the commits it came from. Read it before writing or reviewing code; update it when a change establishes or retires a rule.
- `REVIEW.md`: how code review behaves here (it includes `CODING_STANDARDS.md`). Read it before reviewing a change; update it when the team settles what a severity means or what not to flag.

## Working agreements

After a solved, verified problem, automatically invoke the `ce-compound` skill with `mode:non-interactive` at the completion checkpoint when the work corrected a wrong belief about how something behaves: an approach that failed, a review finding that exposed a real defect, or an assumption, document, or first diagnosis that turned out wrong. A naming, style, or preference change does not count. Work that went as first planned does not need it. Do not judge whether the lesson deserves a document: `ce-compound` decides whether it qualifies and what holds it (a test, a lint rule, a coding standard, or a learning), and writes nothing when nothing qualifies. Capture at the checkpoint so what it writes can ship in the PR that produced it, and only where the repository treats captured learnings as tracked, committed knowledge.

Write every report, summary, or handoff to the user through the `ce-noslop` skill. This applies when you are the top-level agent writing to the user, not when you are a subagent reporting to its caller. Do not apply it to code, config, verbatim quotes, or text the user asked to post as written.
