# Lab — Multiple Investigations — Plan

## Approach

**Registry by discovery.** A new `lablib.investigations(root)` scans `lab/investigations/*/STATE.md` and reads each file's front matter, returning name (the folder), `prefix`, `title`, `status` and its paths. Every tool gets prefixes and paths from this. Nothing is hard-coded except the folder name `investigations`.

**IDs.** One generic pattern: `^(?P<prefix>[A-Z][A-Z0-9]{1,5})-(?P<num>\d{3,})$`. Cards stay at `lab/cards/<PREFIX>-NNN-<slug>.md`, captures at `lab/captures/<ID>/`, evidence at `lab/evidence/<ID>/`. A tool accepts an ID only if its prefix belongs to a registered investigation. Numbering is per prefix (`next_id(prefix)`).

**Checker (`check_state.py`).** It runs every §4.2 check per open investigation, with output grouped under each investigation's name. STALE in any investigation is still the only hard failure. Closed investigations are skipped, except for a check that their open-card list is empty. `--inv <name>` limits the run to one investigation. `--load` needs `--inv` when more than one investigation is open, and otherwise uses the one open investigation. The MEMORY check's pattern is built from the registered prefixes and titles plus the existing v7 terms. New checks:
- a STATE with no `prefix` (hard failure, since nothing can be checked without it);
- two investigations with the same prefix (hard failure);
- a card whose prefix matches no investigation (warning);
- `lab/BENCH.md` missing (warning).

**Hook (`precommit.py`).** Rule 1 applies per prefix: a card moved to recorded/abandoned needs *its* investigation's STATE staged, with `as_of` equal to that prefix's highest ID. Rule 2 is unchanged. Rule 3 checks for duplicate numbers within each prefix. Rule 4 is unchanged.

**Other tools.** `capture.py`, `ingest_usb.py` and `validate_log.py` use the generic ID check plus the registry. Help text says `<PREFIX>-NNN`. `validate_log.py`'s `BASELINES` stays as it is, since `other` already covers new investigations; a future investigation can add its own baselines by changing the code.

**Scaffold.** `tools/lab/new_investigation.py --name <folder> --prefix <PFX> --title "<title>"` creates `lab/investigations/<name>/STATE.md` and `NOTEBOOK.md` from `lab/templates/STATE.md` and `lab/templates/NOTEBOOK.md`. It sets `as_of: <PFX>-000` and fills the sentinel front matter. It refuses an existing name or a prefix already in use. It writes files only and doesn't commit.

**Templates.** `lab/templates/STATE.md` is the empty nine-section skeleton, taken from context-strategy §4.1 and the v7 STATE's headings and caps, with no rows. §6 holds baselines only, plus a pointer to BENCH.md. `lab/templates/NOTEBOOK.md` is the header plus the entry formats, taken from the v7 notebook's header. `card.md` and `instruction.md` get `<PREFIX>-NNN` placeholders, and the v7 example values become labelled examples.

**BENCH.md.** `lab/BENCH.md` is shared across investigations and holds:
- boards: ID, condition, mods, role, and which investigations use it;
- fixtures;
- what's flashed now: board → commit + env, with the card ID that set it;
- the bench state at the last stop.

Its entries cite card IDs, as STATE does. A card that changes a board or what's flashed updates BENCH.md in the same commit. That rule is written down here and in the role, and is not hook-enforced in this initiative. The v7 STATE's §6 keeps its baselines line and a "Boards and bench: see `lab/BENCH.md`" line. Its heading and cap stay, so the CAP check is unaffected.

## Technical Notes

- Sources: `docs/research/v7-retry/context-strategy.md` §4.1 (STATE sections), §4.2 (checks), §6 (lab layout, IDs); `tools/CONTEXT.md` § Lab Tools; the current `tools/lab/*.py` and `tools/lab/tests/`.
- Front matter added to v7 STATE: `prefix: V7R`, `title: v7 I²C fault`, `status: open`. The existing keys are unchanged.
- Fixtures: every existing fixture gets the three new keys, so their results stay the same. New fixtures:
  - `multi`: two open investigations, one STALE, to check grouping and the exit code;
  - `closed`: a closed investigation with an open card;
  - `dup_prefix` and `no_prefix`;
  - `orphan_card`.
  
  `tool_tests.py` gets cases for a second prefix in capture, ingest and validate_log, and for the scaffold.
- Checker tags as built: `NO-PREFIX`, `DUP-PREFIX` (hard, with `STALE`), `ORPHAN-CARD`, `BENCH`, and `CLOSED-OPEN` (a closed investigation whose `open_cards` is non-empty or that has a pre-registered|run card; warning). Registry findings print first, then one `== <name>` group per investigation. An investigation with no prefix or a duplicated prefix is listed but not checked. The MEMORY check is global (one memory dir).
- The Phase 1 `V7R` fallback lives in `lablib.build_registry` (constant `LEGACY_PREFIX`), so the hook gets it too. It applies only while exactly one investigation exists; a second investigation before Phase 3 makes v7 a `NO-PREFIX`. `lablib.id_num`/`fmt_id` keep `V7R` as the default prefix for the Phase 2 tools until they move to the registry.
- The hook reads the registry from the index (staged STATE front matter). A card moving to recorded|abandoned whose prefix no investigation declares is rejected.
- Hook acceptance always runs in a throwaway clone: a second-prefix card recorded without its STATE is rejected; recorded with the *other* investigation's STATE it is rejected; with its own STATE it is accepted.
- Concurrency: Debugger sessions may commit on their own branches during this work. Merge `main` (and any open Debugger branch) in before Phase 3's `lab/` edits and again before the final merge back.

**User waits.**
- **W1** (Phase 3): approve the v7 STATE front-matter + §6 diff and the new `lab/BENCH.md`.
- **W2** (Phase 3): the user applies the role-draft changes, or declines them.
- **W3** (Phase 3): the user merges the PR to `main`.

## Rejected Approaches
- A registry file (`lab/investigations.yaml`): it duplicates what the folder already says, and the user preferred the folder.
- Flat `lab/investigations/STATE-<name>.md` files: the notebook is per investigation too, so it became a folder per investigation (2026-11-02).
- Moving cards/log/evidence into the investigation folders: it would break many `lab/cards/V7R-…` / `lab/evidence/V7R-…` citations for no gain. The prefix already separates them.
- The board inventory kept in each STATE, or owned by v7: boards are shared between investigations (#0004, #0005), so the copies would drift (user, 2026-11-02).

## Open Questions
- None blocking. Should the hook enforce the BENCH.md same-commit rule? Deferred until the rule has been used for a while.
