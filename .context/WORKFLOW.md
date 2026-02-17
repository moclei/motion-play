# Feature Development Workflow

This document defines how we create, organize, and maintain documentation for features and initiatives. It is the canonical reference for documentation practices in this project.

**The guiding principle:** Documentation should reduce friction, not create it. Every document must earn its existence by being actively useful. If a document isn't being read or updated, it shouldn't exist.

## Directory Structure

```
.context/
├── PROJECT.md              # Project-level context (what, why, where things live)
├── WORKFLOW.md             # This file — how we work on features
docs/       
└── initiatives/
    ├── <feature-name>/
    │   ├── BRIEF.md        # Intent, goals, and scope (stable)
    │   ├── PLAN.md         # Technical approach and design (semi-stable)
    │   └── TASKS.md        # Execution checklist (living)
    └── <another-feature>/
        ├── BRIEF.md
        ├── PLAN.md
        └── TASKS.md
```

## Documents Per Feature

Each feature gets **three documents, no more.** If you feel the urge to create a fourth document, that's a signal that one of the existing three needs better organization, not that you need another file.

Each document has a distinct purpose and update frequency:

| Document  | Purpose             | Written       | Updated                        |
|-----------|---------------------|---------------|--------------------------------|
| BRIEF.md  | Why we're doing this | At kickoff    | Rarely — only if goals shift   |
| PLAN.md   | How we're building it | At kickoff   | When the technical approach changes |
| TASKS.md  | What to do next      | At kickoff   | Every session                  |

---

### BRIEF.md — The Anchor

**Purpose:** Orient anyone (human or AI) on what this feature is and why it exists.

**Template:**

```markdown
# <Feature Name>

## Intent
What are we building and why? 1-3 sentences.

## Goals
- What does success look like? Be specific.
- What should be true when this is done?

## Scope
What's in:
- ...

What's out:
- ...

## Constraints
Any technical constraints, dependencies, deadlines, or non-negotiables.
```

**Guidelines:**
- Keep it under half a page. If it's longer, you're over-specifying.
- Write it in plain language. No implementation details — that's what PLAN.md is for.
- "What's out" is as important as "what's in." Explicitly stating what you're *not* building prevents scope creep and keeps the AI agent focused.
- Only update if the fundamental goals or scope of the feature change. If you're updating BRIEF.md frequently, scope is unstable and you should pause to resolve that before continuing implementation.

---

### PLAN.md — The Design

**Purpose:** Describe the technical approach for building the feature. This is the reference for *how* the feature works — architecture, key technical choices, integration points, and any important context about the implementation strategy.

**Template:**

```markdown
# <Feature Name> — Plan

## Approach
How are we building this? Cover the high-level architecture, key components,
and how they fit together. Reference specific parts of the codebase where
helpful.

## Technical Notes
Any important implementation details, patterns being used, APIs being
integrated with, data models, etc. Organize with subheadings as needed.

## Open Questions
- Any unresolved decisions or unknowns. Remove these as they get resolved
  and update the relevant section above.
```

**Guidelines:**
- This is a reference doc, not a working doc. It should be readable at any point and give an accurate picture of the technical design.
- Update it when the approach changes, not when tasks are completed. If you pivot on architecture or make a significant technical choice, reflect it here.
- Open Questions should trend toward empty. If questions linger without resolution across multiple sessions, that's a flag.
- Don't over-specify. Write enough to orient a new session on the design; the code itself is the detailed spec.

---

### TASKS.md — The Checklist

**Purpose:** A concrete, ordered list of tasks to execute the plan. This is the working doc — the thing you look at to know what to do next.

**Template:**

```markdown
# <Feature Name> — Tasks

## Phase 1: <name>
- [x] Completed task
- [x] Another completed task — brief note if relevant
- [ ] Current task
- [ ] Upcoming task

## Phase 2: <name>
- [ ] Task
- [ ] Task
```

**Guidelines:**
- Tasks should be concrete and actionable. "Set up DynamoDB table" not "figure out data storage."
- Brief inline notes on completed tasks are fine when they add useful context (e.g., `- [x] Set up auth — went with JWT over session cookies`). Not required, just allowed.
- Phases are optional. Use them if the feature has natural stages; skip them for simple features.
- Check off tasks as they're completed. **Remove tasks that are no longer relevant** — don't leave stale unchecked items sitting around.
- This is the doc that gets updated most frequently. Every session that makes progress should leave TASKS.md reflecting the current state.

---

## Lifecycle

### Starting a Feature
1. Create a new folder under `initiatives/` with a descriptive kebab-case name.
2. Write BRIEF.md first. Get clarity on intent and scope before touching any code.
3. Write PLAN.md with the initial technical approach.
4. Write TASKS.md with the initial task breakdown derived from the plan.
5. Reference the new feature in PROJECT.md if it's significant enough to be part of the project overview.

### During Development
- Update TASKS.md as you work. Treat it as part of the task: *the task isn't done until TASKS.md reflects it.*
- When starting a new chat or agent session, point it to the active feature's docs. This is the whole point — you shouldn't need to re-explain context.
- If you realize the technical approach is changing, update PLAN.md. If the goals are shifting, update BRIEF.md.
- If new tasks emerge during implementation, add them to TASKS.md in the appropriate position.

### Completing a Feature
- All tasks in TASKS.md should be checked off or removed.
- Open Questions in PLAN.md should be empty or resolved.
- The feature folder stays as a historical record. Don't delete it.

### Abandoning a Feature
- Add a note at the top of BRIEF.md: `**Status: Abandoned — <reason>**`
- Don't delete the folder. It's useful context for why you chose not to do something.

---

## Maintenance Rules

1. **No orphan documents.** Every file in an initiative folder must be one of: BRIEF.md, PLAN.md, or TASKS.md. No scratch files, no "notes.md", no "old-plan.md". If you have scratch thoughts, put them in PLAN.md under Open Questions.

2. **No stale tasks.** If a task in TASKS.md is no longer relevant, remove it. Unchecked tasks that sit untouched for multiple sessions are clutter.

3. **Periodic review.** Every few sessions, scan the active feature's docs and ask: do these accurately reflect where we are? If not, fix them before doing more work.

4. **One active focus.** Try to have at most one or two features actively in progress. More than that and documentation discipline breaks down — and so does focus.

---

## AI Agent Instructions

When working on a feature:
- Read BRIEF.md, PLAN.md, and TASKS.md at the start of every session involving that feature.
- After completing a task, check it off in TASKS.md before moving on to the next task.
- If the technical approach changes, update PLAN.md to reflect the current design.
- Do not create additional documentation files beyond BRIEF.md, PLAN.md, and TASKS.md.
- If you need to capture something and aren't sure where it goes, put it in PLAN.md under Open Questions.
- When a phase or the whole feature is complete, ensure all tasks are checked off and Open Questions are resolved.