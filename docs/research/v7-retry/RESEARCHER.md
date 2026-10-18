# Researcher — Conventions for the v7-retry Track

This folder holds the research artifacts produced before any v7 retry debugging begins. It is a parallel container to our initiative structure — research sessions here are informal, interactive, user-driven, and sit outside the Planner/Orchestrator/Worker protocol. Their output doesn't go into an initiative folder.

> This is a working document. Add "what works / what doesn't" notes at the bottom as we learn.

## Why research lives outside the initiative framework

Our protocol defines six roles (Planner, Orchestrator, Worker, Bugfix, Gardener, Organizer) tied to specific document types and execution patterns. Exploratory research doesn't fit any of them: it needs discussion and iteration with the user, its scope is often unclear until mid-session, and its output can spawn its own downstream initiatives.

The PROTOCOL explicitly acknowledges "research / ideation session" as a session type in its Relay table but intentionally leaves its behavior unformalized. This file is the lightweight convention set for *this track specifically* — not a protocol change.

## Session role

Research sessions here have **no formal agent role**. Launch with the default `claude` (no `--agent` flag). The kickoff relay prompt carries all the discipline the session needs: scope, output path, context-pressure rule, commit discipline.

If after a few sessions this becomes a problem, we may upgrade to a formal `researcher` role defined in `.claude/agents/`. For now: informal.

## File layout

```
docs/research/v7-retry/
├── RESEARCHER.md                          # this file
├── README.md                              # topic index with status
├── relays/
│   ├── RELAY-postmortem.md                # kickoff drafts, pre-launch
│   ├── RELAY-v6-v7-changelist.md
│   ├── RELAY-kicad-extraction-audit.md
│   ├── RELAY-test-workflow-audit.md
│   ├── RELAY-expert-approaches.md
│   └── RELAY-context-strategy.md
├── <topic>.md                             # one artifact per completed topic
└── RELAY-<topic>-continue.md              # only if a session ended mid-topic
```

- **One artifact per topic.** The `.md` next to this file is the research output.
- **The artifact is the handoff.** No separate SESSION.md log. If the next session needs to continue, it reads the artifact.
- **Relays live in `relays/`** when they are kickoff drafts for a session that hasn't run yet. Once a session has run, its relay is retained there as a record (same spirit as initiative relays — never overwritten after use).
- **Mid-session handoff**: if a session ends with a WIP artifact, it writes `RELAY-<topic>-continue.md` at this folder's root (not in `relays/`) describing what's partial and what the next session should do. Deleted when the topic completes.

## Session kickoff

To start a research session:

1. Open the relay draft under `relays/` for the topic.
2. Edit it as needed (scope, open questions, additional load list).
3. Launch a fresh `claude` session and paste the relay as the first message.

The relay should carry everything the session needs — don't rely on recall or compaction from a prior conversation.

## Continuity rules

- **Artifact = handoff.** A session that completes its topic produces the final `.md`. The next session reads it as context if relevant.
- **Unfinished sessions must leave a continuation relay.** If context pressure or scope expansion forces a stop, write `RELAY-<topic>-continue.md` and commit everything (WIP artifact included) before ending. Never leave a dangling in-progress state without a continuation plan.
- **README.md tracks status per topic.** Update your topic's row before ending the session.
- **No cross-topic edits.** A session is scoped to one topic. If a session discovers something relevant to another topic, log it in the artifact under an "Observations for other topics" section — don't edit the other artifact.

## Branch convention

- Single branch for all research work on this track: **`research/v7-retry`**.
- Branch off `main`. One PR per topic when the artifact is complete, or one bundled PR at the end — user's call.
- Each session's work gets at least one commit. Commit WIP freely with `WIP:` prefix.
- A session must never end with uncommitted changes.

## Context-pressure behavior

Same shape as our Worker rule: at **~60% context** with the topic not finished:

1. Finish the smallest coherent unit of work.
2. Commit (WIP: prefix if the artifact isn't complete).
3. Write `RELAY-<topic>-continue.md` describing what's partial, what's next, and what to load.
4. Stop and report to the user.

## Scope discipline

Each research session has **one job**. If a session discovers that work it's doing really belongs to a different session or to an implementation initiative:

- **Note it in the artifact** under an "Observations" or "Spawned work" section.
- **Do not start that work.** Research sessions never execute changes to code, scripts, or hardware configuration. They only produce artifacts.
- If a research topic turns out to need its own implementation initiative, the artifact *recommends* it; the user decides.

## Stage A → Stage B transition

When all Stage A topics are complete:

- A single synthesis session (also informal, launched from a kickoff relay to be drafted later) reads all artifacts under this folder and produces `docs/research/v7-retry/decisioning.md`.
- That synthesis session ends with a `RELAY-planner.md` in the folder for the first implementation initiative identified by the synthesis.
- Only then does the standard protocol flow (Planner → Orchestrator → Worker) resume.

---

## What works / what doesn't

Append notes here as research sessions complete. One line per observation. Keep terse.

### What worked

- Topic 1: surfacing top findings to the user before writing caught nothing wrong but surfaced four user concerns (measurement validity, layout understanding, synthesis, context budget) that became major sections.
- Topic 2: kicad-cli (`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`) XML netlist + pos export on `git archive`d refs gave a clean component/pin/net diff in seconds; regenerating gerbers and matching against the fabricated zips verified the anchors. Note zsh: quote `"${ref}:path"` — `$r:h` is a zsh modifier.
- Topic 3: answering one concrete question ("where does SDA route, what's near it?") with throwaway read-only kiutils+shapely probes exposed every extraction gap in under an hour; better than auditing scripts line by line.

### What didn't

- Topic 3: committed generated outputs (layout context, DRC report) had silently gone stale; any artifact derived from a source file needs a source hash.
