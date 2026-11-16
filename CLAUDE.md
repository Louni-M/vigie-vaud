## Agent skills

### Issue tracker

Issues live in GitHub Issues, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context, in French: one root `GLOSSARY.md` + `docs/adr/`, with data sources in `docs/sources.md`. See `docs/agents/domain.md`. Documented solutions to past problems (bugs, best practices, workflow patterns) live in `docs/solutions/`, organized by category with YAML frontmatter (`module`, `tags`, `problem_type`), and are relevant when implementing or debugging in a documented area.

## Code standards

- `CODING_STANDARDS.md`: the rules code in this repo follows, each with the commits it came from. Read it before writing or reviewing code; update it when a change establishes or retires a rule.
- `REVIEW.md`: how code review behaves here (it includes `CODING_STANDARDS.md`). Read it before reviewing a change; update it when the team settles what a severity means or what not to flag.

## Working agreements

After a solved, verified problem, automatically invoke the `ce-compound` skill with `mode:non-interactive` at the completion checkpoint when the work corrected a wrong belief about how something behaves: an approach that failed, a review finding that exposed a real defect, or an assumption, document, or first diagnosis that turned out wrong. A naming, style, or preference change does not count. Work that went as first planned does not need it. Do not judge whether the lesson deserves a document: `ce-compound` decides whether it qualifies and what holds it (a test, a lint rule, a coding standard, or a learning), and writes nothing when nothing qualifies. Capture at the checkpoint so what it writes can ship in the PR that produced it, and only where the repository treats captured learnings as tracked, committed knowledge.

Write every report, summary, or handoff to the user through the `ce-noslop` skill. This applies when you are the top-level agent writing to the user, not when you are a subagent reporting to its caller. Do not apply it to code, config, verbatim quotes, or text the user asked to post as written.
