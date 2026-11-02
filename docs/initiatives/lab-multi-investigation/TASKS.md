# Lab — Multiple Investigations — Tasks

> Run `python3 tools/lab/tests/run_tests.py` after every code change. Before and after each phase, record its output and `python3 tools/lab/check_state.py` on the real lab in SESSION.md. Real-lab results must not change except where a task says so.

## Phase 1: Registry, IDs, checker, hook

- [x] Record the baseline: `run_tests.py` and `check_state.py` (plus `--load`) output on the real lab, in SESSION.md
- [x] `lablib.py`: a generic ID/card pattern, `investigations(root)` discovery from STATE front matter, and per-prefix `next_id`. Keep any existing helper signatures that other tools call working
- [x] Add `prefix`, `title`, `status` to every existing fixture's STATE (fixtures only; the real v7 STATE waits for Phase 3). `run_tests.py` unchanged
- [x] `check_state.py`: run checks per investigation with grouped output, `--inv`, `--load` rules, and the new checks (no prefix, duplicate prefix, orphan card, BENCH.md missing as a warning), per PLAN. Build the MEMORY pattern from the registry. Until Phase 3 adds `prefix` to the real STATE, a single investigation with no prefix falls back to `V7R`, and this fallback is removed in Phase 3
- [x] `precommit.py`: rules 1 and 3 per prefix
- [x] New fixtures `multi`, `closed`, `dup_prefix`, `no_prefix`, `orphan_card`; each condition fires exactly once. Hook acceptance in a throwaway clone (cases in PLAN Technical Notes); log the outputs in SESSION.md
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 2: Other tools, templates, scaffold

- [ ] `capture.py`, `ingest_usb.py`, `validate_log.py`: generic ID check through the registry, with `<PREFIX>-NNN` in help and errors. Add `tool_tests.py` cases with a second prefix
- [ ] `lab/templates/STATE.md` and `lab/templates/NOTEBOOK.md` per PLAN. `card.md` and `instruction.md` get `<PREFIX>-NNN` placeholders, and the v7 values are kept as labelled examples
- [ ] `tools/lab/new_investigation.py` per PLAN, with tests: scaffold into a fixture root, then `check_state.py --root` on it is clean (sentinel state). A duplicate name or prefix is refused
- [ ] `tools/CONTEXT.md` § Lab Tools: registry, ID pattern, the new script, `--inv`, BENCH.md
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 3: BENCH.md, v7 front matter, docs, merge

- [ ] Merge the latest `main` in (and any open Debugger branch the user names). If a v7 card is open (`open_cards` not empty), stop and ask the user before touching `lab/`
- [ ] Draft `lab/BENCH.md`. Move the boards, fixtures, flashed-now and bench-at-last-stop content out of the v7 STATE's §6 *verbatim*, adding which investigations use each board. Reduce §6 to its baselines plus a pointer. Add `prefix: V7R`, `title`, `status: open` to the v7 STATE front matter. Remove the Phase 1 `V7R` fallback
- [ ] **W1:** show the user the diff (STATE + BENCH.md), and apply it only on approval. `check_state.py` on the real lab gives the same results as the baseline (the BENCH.md warning gone)
- [ ] PROTOCOL.md § lab/: one investigation folder per fault, the shared files, BENCH.md, the scaffold command. Present it as a diff for approval
- [ ] **W2:** draft the role-draft changes (`docs/research/v7-retry/debugger-role-draft.md`) as a diff for the user: choosing an investigation at session start (`check_state.py` lists the open investigations, the user picks one, then `--load --inv`); BENCH.md read at start and updated in the same commit as a card that changes boards or flashing; scaffolding a new investigation at relay intake. The user applies or declines
- [ ] End-to-end check in a throwaway clone: scaffold `power`/`PWR`, pre-register and record a dummy `PWR-001` with its STATE, check the hook and checker, then delete the clone. Log it in SESSION.md
- [ ] **W3:** open a PR to `main` for the user to merge, and tell the user that `v8-debug-board` Phase 2's power relay can now run as `PWR` cards
- [ ] 🔄 Handoff

## Deferred
