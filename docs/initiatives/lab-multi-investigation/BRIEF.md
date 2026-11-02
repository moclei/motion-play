# Lab — Multiple Investigations

## Intent
Let the Debugger run more than one bench investigation in `lab/`. Today the tools and templates assume one fault (the v7 I²C fault, `V7R-` cards). The first new investigation is the battery/power one requested by `v8-debug-board` (its `debugger/RELAY-power.md`).

## Goals
- Each investigation is a folder, `lab/investigations/<name>/`, holding its `STATE.md` and `NOTEBOOK.md`. Its STATE front matter declares its card prefix, title and status (open/closed). The folder is the registry; there is no separate registry file.
- Every `tools/lab/` tool accepts any registered prefix. These are the checker, the pre-commit hook, capture, ingest and the log validator. The checker and hook apply their rules per investigation.
- A one-command scaffold for a new investigation, from STATE and NOTEBOOK templates.
- Boards, fixtures, what's flashed and the bench state at the last stop move to one shared `lab/BENCH.md`. Each STATE's §6 keeps its own baselines and points to BENCH.md.
- The v7 investigation keeps working unchanged: same IDs, same cards, checker results unchanged.
- The proposed Debugger role changes (choosing an investigation at session start, BENCH.md) are drafted for the user to apply.

## Scope
In: `tools/lab/` code, tests and fixtures; `lab/templates/`; the new `lab/BENCH.md`; the v7 STATE front matter, plus moving its §6 boards/bench content into BENCH.md; PROTOCOL § lab/ and `tools/CONTEXT.md` § Lab Tools.
Out: creating the power investigation itself (the Debugger scaffolds it at intake); any card, notebook entry or STATE map content beyond the §6 move; editing the role file (the user does that); renaming `V7R-` IDs or moving cards, logs or evidence; rewriting historical docs.

## Constraints
- Must land before `v8-debug-board` hands over `debugger/RELAY-power.md` (end of its Phase 2).
- Edits to `lab/` content (v7 STATE, BENCH.md) are shown to the user as a diff and applied only on approval. The Debugger owns `lab/`.
- Python 3.7, stdlib (PyYAML optional, as today). `tools/lab/tests/run_tests.py` must pass after every phase.
- The branch is cut from `main` and merged back by PR. No open v7 card may be affected.
