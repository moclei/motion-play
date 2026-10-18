# Protocol

**Principle:** Documentation reduces friction, not creates it. Every document must earn its existence. Creating arbitrary documents clutters up the codebase and makes the project move slower. Tracking documents adds cognitive load to the user, which is a bad thing. This protocol aims to prescribe the documents we will create, and not create, and how we will organize them using custom defined agent roles.

---

## Agent Roles

**Principle:** Each agent owns one document type. Documents are frozen agents; agents are living documents.

| Agent        | Owns             | Function                                     |
| ------------ | ---------------- | -------------------------------------------- |
| Planner      | BRIEF, PLAN      | Defines scope and intent before work begins  |
| Orchestrator | SESSION, MASTER  | Sequences work and adapts when things change |
| Worker       | TASKS            | Executes one task at a time                  |
| Organizer    | CONTEXT.md files | Audits and maintains the context hierarchy   |
| Bugfix       | —                | Diagnoses user-found issues; proposes fixes, applies only on approval |
| Gardener     | GARDEN.md, HAZARDS.md | Clears accumulated cross-cutting refinements via orchestrated sub-agents |

Each role's full definition lives in its own file under `.claude/agents/`; this document holds only the sections shared across roles. 

**Invocation:** The user runs Planner, Orchestrator, Organizer, Bugfix, and Gardener as their own top-level sessions with `claude --agent <role>` — the active agent is fixed for a session's lifetime. The Worker is spawned by the Orchestrator via the Task tool (`subagent_type: worker`), never by the user or another role.

---

## Initiatives 

**Principle:** The "meat and potatoes" of a project are bodies of work that should be managed in a standardized way. We will call these "initiatives" and they will be comprised of four documents per initiative (BRIEF, PLAN, TASKS, SESSION). Transitions between sessions happen via Relays — structured prompts that reconstruct context for the next session - only what it needs to do it's task.

**Principle:** The only agent roles that directly interact with initiatives are the planner, orchestrator, worker and bugfix. Other agents do not directly interact with iniatives, other than suggesting one if it feels appropriate for a body of work.

**Structure:**

```
docs/initiatives/
└── <initiative-name>/
    ├── BRIEF.md               # Intent, goals, scope — stable
    ├── PLAN.md                # Technical approach, decisions — semi-stable
    ├── TASKS.md               # Execution checklist — living
    ├── SESSION.md             # Run log — append-only; Orchestrator and Workers both write
    └── RELAY-<purpose>.md     # Session bootstrap prompts — once they have been run they never get updated again.
```

**Principle:** If you feel the urge to create a document that is not part of these prescribed ones -- don't. Instead, notify the user of why you had wanted to, so we can reflect on it and consider improvements to the PROTOCOL for the future.

**Principle:** The user will try and keep to one active initiative at a time where possible.

## Initiative Documents

### BRIEF.md — The Anchor

Why this initiative exists and what it must achieve. Written at kickoff, rarely updated. Keep under half a page.

```markdown
# <Feature Name>

## Intent
What are we building and why? 1–3 sentences.

## Goals
- What does success look like? Be specific.

## Scope
In: ...
Out: ...

## Constraints
Technical constraints, dependencies, deadlines, non-negotiables.
```

Write it in plain language — no implementation details, that's PLAN.md. What's "out" is as important as what's "in". Only update if the fundamental goals or scope change.

---

### PLAN.md — The Design

How it's being built. Update when the approach changes, not when tasks complete.

```markdown
# <Feature Name> — Plan

## Approach
High-level architecture, key components, how they fit together.

## Technical Notes
Important implementation details, patterns, APIs, data models.

## Rejected Approaches
Append-only. One line each. Never cleaned up.

## Open Questions
- Unresolved decisions. Strike through when resolved.
```

Edited in place, never appended to. No date-stamped headings — a heading that needs a date is a log entry and belongs in SESSION.md. SESSION.md notes are a per-dispatch record; `## Rejected Approaches` is where a future session looks.

PLAN.md is read in full at the start of every Worker session. If `## Approach` + `## Technical Notes` no longer answer *what are we building*, say so in your session notes.

---

### TASKS.md — The Checklist

What to do next. Tasks must be concrete and actionable.

```markdown
# <Feature Name> — Tasks

## Phase 1: <name>

- [x] Completed task
- [~] In-progress task
- [ ] Upcoming task
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 2: <name>

- [ ] Task
- [ ] 🔄 Handoff

## Deferred

[from: <initiative>] One-line note.
```

**Task status markers:** `[ ]` not started · `[~]` in progress (set by Orchestrator at dispatch only) · `[x]` complete

Size each phase for one session. When in doubt, smaller — a session that finishes early can pull the next phase; a session that overruns creates mess.

`🔄 Handoff` is a real task. It must be completed before the session ends.

`## Deferred` is for out-of-scope discoveries. Never actioned directly — consulted when planning new initiatives. Refinements to *existing* features go to GARDEN.md instead.

---

## Non-Initiative Documents


**GARDEN.md:** Sometimes there are small issues that don't seem to require the overhead of an initiative. The user gathers these in a document at the root of the initiatives folder called `docs/initiatives/GARDEN.md`. The gardener role owns that document and occasionally will run and triage the items in there, deciding what can be "knocked out" quickly in the gardener session, what might need an initiative, and so on. That is the gardener's job.

**MASTER.md:** Sometimes we need to track work across multiple initiatives. Not always, but when we do, we use this file to do so. It lives in `docs/initiatives/MASTER.md` and attempts to track progress and help sequence planned initiatives. The orchestrator owns this document.

**HAZARDS.md:** Known traps that waste a session's time or make a symptom look self-inflicted — environment, tooling, auth, CI, or "passes tests but breaks at runtime" gotchas. Lives at `.context/HAZARDS.md`. Any session may add one; the gardener curates and removes items once their cause is fixed.

Rules: one trap per entry, a line or two, no history. Route here when the value is *knowing before you start*; route a scoped fix to GARDEN, a durable "always do X" rule to a CONTEXT.md, and a decision or feature to MASTER. If an item is both a warning and a fix, HAZARDS holds the warning and links the GARDEN item that owns the fix.

---

## Session Management

AI agent sessions have a finite context window. Quality degrades as context fills. **Never exceed ~70% context usage in a single session** — Workers start wrapping up at ~60% to stay under it.

**Principle:** Ground every task in the source documents, not memory. Cite the specific sections of `.context/PROJECT.md`, the relevant `CONTEXT.md`, and the datasheets/references in `docs/references/` relevant to the task rather than recalling them. If a design decision is revisited, record it in the initiative's PLAN.md Open Questions and surface it to the user — never silently deviate from the source documents.

---

## Relays

A Relay is a structured prompt written at the end of a session that bootstraps the next session with a specific role and full context.

Relays are always written on request — by the current session, for the next one. They are saved as files in the initiative folder and once they have been run, they are never overwritten, because they are a record of how each phase began.

**When a Relay is needed:**

| From | To | File | Trigger |
|------|----|------|---------|
| Research / ideation session | `role:planner` | `RELAY-planner.md` | Enough explored to start an initiative |
| Planner session | `role:orchestrator` | `RELAY-orchestrator.md` | Initiative docs complete, ready to build |
| Orchestrator session | Bugfix / playtesting session | `RELAY-bugfix-<date>.md` | Build complete, testing needed |

**Relay template:**

```markdown
# Relay-<from session type> — <to session type> — <date>

role:<target role>

## Context
<1–3 sentences: what led to this relay. What was researched, decided, or built.>

## Load these files
- .context/PROTOCOL.md
- <initiative folder, if relevant>
- <any other files directly relevant to what comes next>

## State
Branch: <branch | n/a>
Build: <passing | broken — explain if broken | n/a>
TASKS.md current: <yes | no | n/a>

## What was done
<One line per significant decision, document written, or conclusion reached.
For a bugfix relay: one line per area of known issues or test coverage gaps.>

## Your task
<Precise instruction for what the next session should do first.
For role:planner → write the initiative docs.
For role:orchestrator → run the initiative named above.
For bugfix → the playtest checklist for the user to run; the session waits for reported issues.>

## Open questions
<Anything unresolved that the next session should be aware of. Empty if none.>
```

---

## Escalation Paths

In order of severity:

**Worker hits context pressure mid-task**
→ Finish the smallest completable unit → commit `WIP:` → return `PARTIAL`
→ Orchestrator emits evaluation line, re-dispatches or escalates to Planner

**Worker encounters a blocker**
→ Document in `## Rejected Approaches` in PLAN.md → add to `## Open Questions`
→ Return `BLOCKED` → Orchestrator emits evaluation line, escalates to Planner

**Orchestrator sees repeated failure or drift**
→ Stop dispatching → send replan request to Planner with specifics
→ Do not resume until Planner confirms task list is updated

**Planner cannot resolve without user input**
→ Surface to user: what the decision is, what the options are, what the implications are
→ Do not proceed until user decides
→ If user is unavailable, add to `## Open Questions` in PLAN.md, mark initiative blocked

**Any agent encounters something outside its role**
→ Escalate up one level — Worker → Orchestrator → Planner → user
→ Never act outside your defined responsibilities unilaterally

---

## Git

Branch for every initiative: `feat/<initiative-slug>` or `design/<what-youre-trying>`.

- The Orchestrator cuts the branch at the start of a run and commits its own SESSION.md and TASKS.md writes before dispatching.
- Always commit before switching branches, even broken work. `WIP:` prefix freely.
- Commit at every meaningful checkpoint — at minimum, at every `🔄 Handoff`.
- A session must never end with uncommitted changes.
- Abandoned branches stay. They are history.

---

## Maintenance Rules

1. **No orphan documents.** Every file in an initiative folder is one of: BRIEF.md, PLAN.md, TASKS.md, SESSION.md, RELAY-*.md.
2. **No stale tasks.** If a task is no longer relevant, remove it.
3. **One active focus.** At most one or two initiatives in active development at once.
