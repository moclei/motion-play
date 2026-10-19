# Context Strategy for v7-Retry Debug Sessions

> Stage A, topic 6 of 6. Session date: 2026-10-18. Scope: the **containers** a v7 debug session reads and writes, the tier each sits in, the rules that keep them current, and how debug sessions fit the protocol. It does not fill them: the hypothesis map, IS / IS NOT table, tombstones and next test are Stage B's content (`decisioning.md`).
>
> Inputs: relay `relays/RELAY-context-strategy.md`; targeted sections of topics 1–5; `.context/PROTOCOL.md`, `CLAUDE.md`, `.context/PROJECT.md`; the auto-memory index and v7 notes; headings only of the `docs/debugging/` handoff artefacts.

**User decisions taken at kickoff (2026-10-18):**

| Question | Decision |
|---|---|
| Protocol fit | Draft a formal `debugger` role (Appendix A). The user expects to edit it heavily before first launch, and may pivot away from it. |
| Where the debug home lives | Root `lab/`. |
| Shape of the retry | One continuous debug track, which spawns normal build initiatives (test workflow, board model, fixes). |
| Auto-memory | Keep v7 state out of it entirely. |

---

## Index: answers to the handed inputs

| # | Input | Answered in |
|---|---|---|
| 1 | Split briefing from notebook | §4 (STATE.md ≤ 150 lines), §5 (NOTEBOOK.md, L2) |
| 2 | One handoff artefact; fate of the old ones | §2.4 placement table, §7.2 |
| 3 | Handoffs carry state, not interpretation | §7.2 |
| 4 | One-line tombstones | §4, section 5 of STATE |
| 5 | Commit after every result, stable IDs | §6.2, §7.1 |
| 6 | Home and trigger for the hypothesis map and step-back checkpoint | §4, sections 3 and header of STATE; §4.3 |
| 7 | The ~56k-token doc as the anti-pattern | §1, §11 |
| 8 | A mechanism, not an intention, for stale summaries | §4.2 (pre-commit hook plus start-of-session check) |
| 9 | `lab/` location, card/log storage, default load, counter | §6 |
| 10 | Audit summary and baselines in the state file? | §4, sections 6–7 of STATE: yes, both |
| 11 | Captures into context; what gets written down | §6.4 |
| 12 | Route narratives over raw JSON | §8.1 |
| 13 | Source hash on generated files | §8.2 |
| 14 | kiutils probes before the board model lands | §8.3: yes, with rules |
| 15 | "Symptoms, not guesses" for handoffs | §7.2, §7.3 |
| 16 | IS / IS NOT as a standing section | §4, section 2 of STATE: yes |
| 17 | Role of auto-memory | §2.5: none for v7 state, with the drift guard |

---

## 1. Problem statement

The last investigation lost its context in two ways.

- **Orientation cost (PM §4.10).** One doc (~1,190 lines, ~56k tokens) was both lab notebook and briefing. A fresh session on the resume prompt's load list read ~70–80k tokens before doing anything, mostly superseded reasoning: refuted stories in full, embedded audit output, duplicated "what we know" lists.
- **Handoff decay (PM §4.6).** Five snapshots drifted apart: the investigation doc, the resume prompt, the fresh-perspective prompt, the scope guide and the memory note. None was retired when superseded. Summary sections went stale because nothing forced an update when a phase landed (PM §5). Handoffs carried interpretation ("this would support Story D-revised"). Phase IDs collided. Phase 25's result was lost.

The design goal: **a new session engages productively from about two pages of state plus named, on-demand lookups.** Every fact lives in exactly one place, and a mechanism, not good intentions, catches the place going stale.

---

## 2. The context pyramid

### 2.1 Tiers

| Tier | Loaded | Rule |
|---|---|---|
| **L0** | Always, before the first reply | Small, current, mechanically checked for staleness. Target < 500 lines in total. |
| **L1** | On relevance; each document is *named* in STATE.md's Lookups section with the condition that triggers it | Load the section, not the file, wherever the doc has headings. |
| **L2** | On demand, by ID or path, through an index (card ID, legacy phase ID, `grep -n`) | Never loaded whole. Quote the lines you need into the conversation, cite the ID. |
| **Retired** | Never | Kept in git history, or in place with a banner if other docs cite the path. |

### 2.2 L0 for a debugger session

| Item | How it gets loaded | Size |
|---|---|---|
| `CLAUDE.md` → `.context/PROJECT.md` | Harness auto-load | 150 lines, ~2.8k tokens |
| Auto-memory `MEMORY.md` index | Harness auto-load | ~5 lines, ~0.2k tokens (after the §2.5 cleanup) |
| `.claude/agents/debugger.md`: the rules and routing (the "entry doc", §3) | `claude --agent debugger` | ≤ 120 lines, ~2k tokens |
| `.context/PROTOCOL.md`, §Session Management and §Git only | Agent file instructs it | ~25 lines, ~0.4k tokens |
| `lab/STATE.md`: the current state (§4) | Agent file instructs it, after the staleness check | ≤ 150 lines, ≤ ~4k tokens |
| **Total** | | **~450 lines, ~9.5k tokens** |

The debugger does **not** load PROTOCOL.md in full. Its initiative sections (BRIEF/PLAN/TASKS templates, relays, escalation) don't apply to a bench session, and they cost ~2.5k tokens.

### 2.3 Default L1 at session start

Loaded by rule (§6.3), with no judgement needed:

- every open card (status `pre-registered` or `run`), in full;
- the **front matter and `## Conclusion` only** of the last two recorded cards;
- the current session's log, if one exists for today.

Typically ~3.5k tokens. **L0 plus default L1 ≈ 13k tokens, against 70–80k last time** (budget detail in §11.2).

### 2.4 Placement of every existing and planned artefact

| Artefact | Tier | Notes |
|---|---|---|
| `CLAUDE.md`, `.context/PROJECT.md` | L0 | Add one pointer line to PROJECT.md (§2.5). No v7 *state* in it. |
| `MEMORY.md` index | L0 | Index only; no v7 lines (§2.5). |
| `.claude/agents/debugger.md` *(new)* | L0 | Static rules. Holds no state, ever. |
| `lab/STATE.md` *(new)* | L0 | The single live handoff artefact. |
| `lab/cards/V7R-NNN-*.md` *(new)* | L1 (open cards plus the last two conclusions), else L2 by ID | §6 |
| `lab/log/*.yaml` *(new)* | L1 (today's session), else L2 | §6 |
| `lab/evidence/`, `lab/captures/` | L2 | Images enter context only at ingest or for a named audit question (§6.4). |
| `lab/NOTEBOOK.md` *(new)* | L2 | `grep` by test ID or date; never loaded whole. |
| `lab/procedures/` *(new, from `test-workflow-setup`)*: DHO804 setup validation and known-good reference | L1 at the start of any scope session | Replaces the scope guide. |
| `docs/debugging/v7-i2c-investigation.md` | **L2, frozen**: legacy notebook, volume 0 | Banner at top: "Frozen 2026-10. Historical only. Current state: `lab/STATE.md`." Lookups by phase heading (`grep -n "^### Phase"`). Its own summary sections (Fastest read, TL;DR, Current working theory, Candidate fixes, Firmware state, Revert list, Immediate next steps) are **not** to be read as current. Legacy IDs are cited as `L-Ph01`…`L-Ph25`, with `L-Ph24a` (Arduino-as-master) and `L-Ph24b` (Exp 1 glitch filter) for the duplicate. |
| `docs/debugging/v7-i2c-session-resume.md` | **Retired** | Banner "RETIRED, superseded by `lab/STATE.md`; do not load." Kept in place because topic 1 cites the path. |
| `docs/debugging/v7-i2c-fresh-perspective-prompt.md` | **Retired** | As above. A future outside-review prompt is generated from STATE (§7.3), not hand-maintained. |
| `docs/debugging/i2c-oscilloscope-debugging.md` (scope guide) | **Retired once `lab/procedures/` exists** | Delete vs. archive is already `test-workflow-setup` decision 3. Until then, L2 for DHO804 operating notes only; its outcome tables are not to be used (PM §4.6). |
| `docs/explorations/esp32-s3-i2c-master-deep-dive.md`, `bq_solder_sda-catmull.md` | L2 | Pre-retry interpretation (e.g. "v8 regardless"). Banner: "conclusions not authoritative; see `lab/STATE.md`." Reference facts are cited from them, never their conclusions. |
| `docs/research/v7-retry/decisioning.md` *(Stage B)* | L1 until its content is transcribed into STATE.md, then L2 | §4.4 |
| `v6-v7-changelist.md` | **L1**: when building or editing the IS / IS NOT table, choosing a test, or reasoning about a v6/v7 difference | §5 (suspect list) first; §3 rows by CL-ID. 26 CLs, so look up rows by ID rather than loading the table. |
| `test-workflow-audit.md` | L2 once `test-workflow-setup` lands (its §4 becomes templates and procedures); §2.3–§2.6 by phase ID | Its §2.6 verdicts are carried into STATE section 7 (§4). |
| `expert-approaches.md` | L1 at a step-back checkpoint: §5.1–§5.3 (when to redesign, ask, pay); else L2 | Its rules are already restated in the debugger role. |
| `postmortem.md` | L2 | Its §6 rules are restated in the debugger role. §2 (hypotheses scored) is input to Stage B, not to sessions. |
| `kicad-extraction-audit.md` | L2 | Its §6.1 validation fixtures are the board-model initiative's job. |
| `RESEARCHER.md`, research `README.md`, `relays/` | Not part of debug context | Research track only. |
| `circuit-context.json` (all boards) | L1 via targeted queries (`jq`, or tool output) for named components or nets | Needs a source hash (§8.2). |
| Board-model outputs *(future)*: route narratives, per-net and per-plane PNGs, diffs | L1 for the nets under test | §8.1 |
| `pcb-routing-context.json` | L2 cache for scripts; **never read into context** | §8.1 |
| `pcb-layout-context.json`, `drc-report.json`, `placement-report.json` | **Retired** (stale; topic 3 §2) | Board-model initiative decision 2. |
| `tools/pcb-context/audit-specs/v7-main-i2c.audit.md` | **Retired for numbers** | Centreline clearances are misleading (topic 3). Banner pointing at the board model. |
| `hardware/pcb-main/REVIEW-HANDOFF.md` | Not debug context | Pre-order review prompt from April. |
| `firmware/CONTEXT.md`, `hardware/CONTEXT.md`, `tools/CONTEXT.md` | L1 when the session touches that domain | |
| `docs/references/` datasheets | L1, targeted page or section | Cite page numbers in cards. |
| Memory: `project_v7_i2c_bq_debug.md` | **Retired (delete)** | §2.5 |
| Memory: `project_pcb_revision_apr2026.md` | **Retired (delete)** | §2.5 |
| Memory: `project_bq24195_iinlim_fix.md`, `feedback_*`, `user_profile.md` | Unchanged | Durable facts and preferences, not debug state. |

### 2.5 Auto-memory (input 17)

**Decision: v7 debug state stays out of auto-memory entirely.**

Memory is the worst possible place for live state. It sits outside the repo, so commits, hooks and the staleness check can't see it. Its index is in L0 for *every* session, so a stale line misleads sessions that never asked about v7. Its writes are triggered by the harness, not by a test result.

Even after today's corrections, the index line still reads "Paused at Ph25: S3 master implicated". That is an interpretation carried in L0, which is exactly what rec 18 forbids.

Recommended actions (housekeeping; not done in this session):

1. **Delete** `project_v7_i2c_bq_debug.md` and its index line. Everything it says that is still true belongs in STATE.md (baselines, boards, "don't repeat the bodge") or in the changelist.
2. **Delete** `project_pcb_revision_apr2026.md` and its index line.
   - Its v6→v7 facts are superseded by `v6-v7-changelist.md`.
   - The SPICE-symbol lesson already lives in `feedback_spice_symbols.md`.
   - Move the one durable non-v7 tip ("BQ24195 C90862 stock is chronically low, check before ordering") into `hardware/CONTEXT.md`.
   - Its "housekeeping still needed" list is stale; if any item is still live, move it to `GARDEN.md`.
3. **Discoverability without memory:** add one line to `.context/PROJECT.md` under Current Project Status: `**v7 main PCB I²C fault:** open, see lab/STATE.md.` That line may only ever say `open` or `closed`. Nothing else in it can go stale.
4. **Drift guard:**
   - The debugger role forbids writing v7 facts to memory (Appendix A).
   - The staleness check (§4.2) also greps the memory directory for `v7` / `V7R-` / `BQ.*NACK` and warns on a hit.
   - This is the mechanism; the rule alone would be an intention.

### 2.6 Rules for every tier

- **One fact, one home.** A test result lives in its card. Its current standing (supported, refuted, superseded) lives in STATE.md, as a one-line citation of the card ID. Nothing restates a result in prose anywhere else.
- **Cite IDs, not narratives.** STATE.md, the notebook and handoffs cite `V7R-NNN`, `L-PhNN`, `CL-NN`, or a file path with a hash. A reader goes down a tier by following the ID.
- **Generated content is never pasted** into a hand-written doc. Cite its path and source hash instead (§8.2). Pasted audit output was one source of the 56k bloat.

---

## 3. Entry doc design

**The entry doc is the debugger agent file, `.claude/agents/debugger.md`.**

`claude --agent debugger` loads it verbatim. No session has to remember to read it, and no relay has to restate it. It holds **only stable things**: rules, load order, routing, templates by path. It never holds state. Because it doesn't change when tests land, it can't go stale the way the resume prompt did.

If the user pivots away from the formal role (kickoff decision), the same body becomes `lab/README.md` and every kickoff relay says "read `lab/README.md`, then follow it". Nothing else in this design changes. **The design doesn't depend on (b) over (a).** It depends only on the rules living in one static file and the state in another.

Mocked-up sections (the full draft is Appendix A):

| Section | Contents | Changes when |
|---|---|---|
| Role | One paragraph: interactive bench debugging of the v7 I²C fault with the user at the bench. What it owns (`lab/`). What it never does. | Role changes |
| Start of session | The exact sequence: run the check → read STATE.md → default L1 → five-line orientation to the user → ask about bench time and board state. | Rarely |
| Test lifecycle | Card pre-registration → instruction blocks → per-arm commits → recording → STATE update in the same commit → notebook entry. | Rarely |
| Discipline rules | The PM §6 and topic 5 rules that apply at the bench, one line each, with source cited. | When a rule is added |
| Step-back checkpoint | Trigger and procedure (§4.3). | Rarely |
| Lookups | *Pointer* to STATE.md's Lookups section. The routing table itself lives in STATE, so it can name current files. | Never |
| Context pressure and handoff | §7. | Rarely |
| Boundaries | No v7 memory writes; legacy docs frozen; `.kicad_pcb` probe rules (§8.3); firmware changes only as a card's declared delta; build work goes to the Planner. | Rarely |

**Routing for sessions that aren't debugger sessions** (a Planner for a fix initiative, a general `claude`): the PROJECT.md pointer line names `lab/STATE.md`. STATE.md's own header says "if you are not a debugger session, read sections 1–4 and stop."

---

## 4. Current-state document: `lab/STATE.md`

A one-page live snapshot. It is **rewritten in place**: it states what is believed now, not how belief evolved. Evolution is recorded append-only in the notebook (§5), so in-place rewriting no longer erases history (PM §4.6). Its git history is a second record.

### 4.1 Mock-up with field definitions

````markdown
---
as_of: V7R-014            # highest card ID with status recorded|abandoned that this file reflects
updated: 2026-11-12       # date of the last edit
last_checkpoint: V7R-012  # card ID at which the last step-back checkpoint ran (§4.3)
open_cards: [V7R-015]     # status pre-registered|run; must match lab/cards/ (checked)
---

# v7 I²C fault — current state

> Debugger sessions: this is L0. Other sessions: read sections 1–4 and stop.
> Never restate a result here. Cite its card. Max ~150 lines; the check warns beyond that.

## 1. Symptom                                   (≤ 6 lines)
Observable behaviour only, in operator terms: what fails, how it is seen (serial error
code, decode), the minimal repro config. No mechanism words.

## 2. IS / IS NOT                               (KT table, ≤ 12 rows)
| Dimension | IS | IS NOT | Distinction | Evidence |
|---|---|---|---|---|
| What / Where / When / Extent | … | … | true only of IS | V7R-/L-Ph/CL- IDs |
Every candidate cause in section 3 must explain both columns (topic 5 P1).

## 3. Hypothesis map                            (one row per region, ≤ 25 rows)
| Region | Hypothesis (one line) | Status | Strength | Evidence | Last touched |
|---|---|---|---|---|---|
| master / bus / mux / slave / power / firmware / measurement / … | … |
  untested | argued | tested | measured-supported | measured-refuted | argued | not tested | IDs | ID |
Status says whether a test has touched the region; Strength says what the evidence is worth
(PM rec 6). A region with no rows is listed explicitly as "no hypothesis yet".

## 4. Facts in use                              (≤ 15 rows)
| Fact | Strength | Source |
Only facts load-bearing for section 3. Inferences go here labelled "argued"; never promote
one silently (PM §5 last row).

## 5. Tombstones                                (one line each, never deleted)
`<hypothesis> — refuted by <ID> — <strength> — notebook <date>`
Full narrative lives in the notebook or the legacy doc only.

## 6. Baselines and bench state                 (≤ 15 lines)
- Baselines: `v7-clean` = tag → commit, I²C init in one line; `v6-ref` = tag → commit.
- Boards: ID | condition | mods | role (target / sacrificial / reference / damaged).
- Flashed now: board → firmware commit + env (last known, with card ID that set it).
- Cables / fixtures in the failing config.

## 7. Measurement trust                         (≤ 10 rows; rows leave when re-measured)
| Legacy or V7R result | Verdict (trustworthy/suspect/unknown/not tested) | Load-bearing for | Pending |
Seeded from topic 4 §2.6. A row is deleted when a V7R card re-measures it; that card's
conclusion then carries the status.

## 8. Next                                      (≤ 6 lines)
- Open cards: ID, title, arm reached.
- Proposed next test: which map region it cuts, and why that region (not "the lead").
- Blocked on: build initiatives, parts, decisions.

## 9. Lookups (L1 routing)                      (≤ 15 rows)
| When you need… | Load | Section/query |
| a v6/v7 difference | docs/research/v7-retry/v6-v7-changelist.md | §5; §3 by CL-ID |
| a legacy phase | docs/debugging/v7-i2c-investigation.md | grep -n "^### Phase NN" |
| scope setup | lab/procedures/… | … |
| a net's route | <board-model output> | per net; check hash |
| …
````

**Size caps** are per section and checked by line count. They force compression: when a section hits its cap, the oldest or weakest rows move to the notebook as a dated entry, and the row becomes an ID citation.

**Inputs 10 and 16:**
- Baselines (section 6): **yes**. Every card cites one.
- The audit summary (section 7): **yes, as a shrinking table**. While legacy numbers are load-bearing, a session must see their trust level before reasoning from them. Rows leave as they're re-measured.
- IS / IS NOT (section 2): **yes, as a standing section**, so every proposed cause is checked against it in the same read.

### 4.2 Update trigger and stale detection (input 8)

**Trigger:** a card's `status` changes to `recorded` or `abandoned`. **That same commit must touch `lab/STATE.md` and set `as_of` to that card's ID.** Nothing else forces a STATE edit. Mid-run observations go to the card; session commentary goes to the notebook.

**Mechanisms** (both are needed: the hook catches it at write time, the check at read time):

1. **Pre-commit hook** (`.githooks/pre-commit`, enabled once with `git config core.hooksPath .githooks`):
   - if the staged diff changes any `lab/cards/*.md` front matter to `status: recorded|abandoned`, and either `lab/STATE.md` is not staged or its `as_of` ≠ the highest such ID → **reject**, with a message naming the card;
   - if a card staged as `recorded` has empty `Result commit` or no `lab/evidence/<ID>/` reference in its conclusion → reject.
2. **Session-start check** (`tools/lab/check_state.py`, run by the debugger as its first action, and runnable by hand). It prints a block that the session pastes to the user:
   - `as_of` vs the highest recorded/abandoned card in `lab/cards/` → **STALE** if behind;
   - `open_cards` vs the cards whose status is `pre-registered|run` → mismatch;
   - any card in `run` with no commit in the last 7 days → "possibly lost result" (the Phase 25 failure);
   - recorded cards since `last_checkpoint` ≥ 3 → **CHECKPOINT DUE**;
   - section line counts over cap → warn;
   - generated files cited in Lookups whose source hash doesn't match → warn (§8.2);
   - memory directory mentions v7 → warn (§2.5).

A STALE result blocks new work: the session reconciles STATE from the cards it is behind on, commits, then proceeds.

The hook is git-native, so it also catches a non-debugger session or a manual edit. A Claude Code hook would not: `.claude/*` is gitignored except `agents/`, and it only fires inside Claude.

### 4.3 Hypothesis-map updates and the step-back checkpoint (input 6, recs 13–14)

- **Map update:** part of the recording commit. Every recorded card updates at least the `Last touched` and `Evidence` cells of the regions it tested. That's what makes "pick the test that cuts the map" possible: untested regions are visible as stale `Last touched` cells.
- **Checkpoint trigger:** every **3** recorded cards (`last_checkpoint` vs `as_of`), and at the start of any session after a gap of more than 14 days. The check enforces both. A new card can't be pre-registered while a checkpoint is due.
- **Checkpoint procedure** (≤ 15 minutes):
  1. Re-read sections 2–3.
  2. For each region, ask: untested or only argued? Has the lead earned its place (magnitude gate, PM rec 5)?
  3. Re-derive the fix recommendation if the mechanism estimate moved (PM rec 15).
  4. Check `expert-approaches.md` §5.1–§5.3 (redesign / outside expert).
  5. Write a `checkpoint` entry in the notebook (§5).
  6. Set `last_checkpoint`.

  The output is a map edit and a notebook entry, nothing else.

### 4.4 First fill

The containers are created empty by the implementation initiative (§10). Stage B's `decisioning.md` produces the first hypothesis map, IS / IS NOT, tombstones and next test. **The first debugger session transcribes them into STATE.md in one commit** (as_of `V7R-000`, a sentinel), after which `decisioning.md` drops to L2. That keeps a single source: the map is never maintained in two places.

---

## 5. Session log / lab notebook: `lab/NOTEBOOK.md`

**Append-only, one file, L2.** New entries go at the bottom. Nothing is edited after the commit that adds it, except to fix a typo. Sessions find entries with `grep -n "V7R-014"` or by date heading.

**Relation to cards: no result is written twice.**

| Content | Lives in |
|---|---|
| Hypotheses, predictions and exclusions for one test | The card, above `--- RUN ---` |
| Raw observations, measured values, conclusion for one test | The card, below `--- RUN ---` |
| Numbers and setup for each capture | The log YAML |
| Current standing of a hypothesis | STATE.md |
| *Everything between cards:* why this test was chosen, belief changes, decisions with the user, observations not covered by any card, dead ends that never became a card, checkpoints, bench incidents | **NOTEBOOK.md** |

**Entry format** (one per session, plus one per checkpoint):

```markdown
## 2026-11-04 · s01 · <one-line summary>
- session: debugger | <relay or "direct"> · operator: user · boards: v7-B3 (v7-clean+Δ), v6-B1 (v6-ref)
- cards: V7R-012 pre-registered (a1b2c3d) → recorded (e4f5a6b); V7R-013 pre-registered (…)
- map: master/drive: untested → tested (V7R-012); measurement/V_OL: suspect → trustworthy (V7R-012)
- belief changes: was "<old>", now "<new>", because V7R-012. (Interpretation, labelled.)
- decisions: <what the user decided, and why, one line each>
- observations not in a card: <verbatim operator notes; symptom terms>
- bench state at end: <board power, probes, firmware flashed>, so the next session doesn't guess
- next: <ID of the open card, or "checkpoint due">
```

```markdown
## 2026-11-12 · checkpoint @ V7R-014
- untested regions: …
- lead challenged: <region> — earned / not earned (magnitude gate: …)
- fix recommendation: unchanged | re-derived: …
- redesign/outside-help check (expert §5.1–5.3): …
```

The "belief changes" line is the replacement for overwriting "Current working theory". STATE.md says what is believed; the notebook says when and why it changed.

---

## 6. Test cards, log and captures in the pyramid (inputs 9, 11)

### 6.1 Layout

```
lab/                               # repo root
├── STATE.md                       # L0 (§4)
├── NOTEBOOK.md                    # L2 (§5)
├── cards/V7R-NNN-<slug>.md        # committed; one per test (topic 4 §4.7)
├── log/YYYY-MM-DD_sNN.yaml        # committed; one per scope session (topic 4 §4.6)
├── evidence/V7R-NNN/              # committed; only captures a conclusion cites (topic 4 §4.5)
├── captures/V7R-NNN/              # gitignored; every renamed capture
├── inbox/                         # gitignored; raw dumps
├── procedures/                    # bench validation + known-good reference (test-workflow-setup)
└── templates/                     # card, log, instruction block (test-workflow-setup)
tools/lab/                         # check_state.py, card scaffolder, capture tool (repo convention: code in tools/)
.githooks/pre-commit               # §4.2
```

- `lab/` is at the root, not under `docs/`. It holds data (YAML, images, CSV), not just prose, and it outlives any initiative.
- The `V7R-` prefix scopes it. If a second investigation ever needs a lab, it gets its own prefix and its own STATE file; don't design for that now.

### 6.2 The ID counter

**The counter is the `lab/cards/` directory itself:** next ID = highest `V7R-NNN` among card filenames + 1.

- There's no separate counter file to drift. Allocation is the pre-registration commit that adds the file.
- Abandoned cards keep their file, and so their ID.
- The card scaffolder (if built) does the arithmetic. By hand, it's `ls lab/cards | tail -1`.
- With one user and one bench there's no concurrency to protect against. The pre-commit hook rejects a duplicate ID anyway.

Legacy phases are never renumbered into V7R. They stay `L-PhNN` (§2.4).

### 6.3 Default-load rule

At session start the debugger loads, without being asked:

- **every open card** (status `pre-registered` or `run`) in full;
- the **front matter + `## Conclusion`** of the **last two recorded** cards (`sed -n` from the heading). Their bodies stay L2;
- **today's log**, if it exists.

Every other card, log or capture is loaded only by ID, when STATE.md or the user cites it.

### 6.4 Captures and images (input 11)

- **Tier:** `captures/` and `evidence/` are **L2**.
- **When an image enters context:**
  1. At **ingest**, per topic 4 §4.9: the session opens each PNG once.
  2. For a **named audit question** ("re-read V7R-012 A1_01: is the V/div what the log says?").
  3. When **preparing an outside-review prompt** (§7.3).

  Never "to get a feel" for past results.
- **What the session writes down after reading one.** It writes into the log measurement entry, not the card and not chat:
  - the on-screen settings it can read (V/div, timebase, probe ratio if shown, BW limit, trigger);
  - the measurement-panel and cursor values;
  - any mismatch with the operator's REPORT numbers.

  Proposed as an addition to topic 4's schema; `test-workflow-setup` decides the field names:
  ```yaml
  ai_read: {capture: 2026-11-04_V7R-012_A1_01.png, settings_seen: {...}, values_seen: {...}, mismatch: none}
  ```
  After that, **the transcription is what every later session uses.** The image is re-opened only to audit the transcription.
- A mismatch is a stop condition (topic 4 §4.9). It is recorded as a raw observation in the card, not resolved silently.

---

## 7. Handoff and compaction for debug sessions (inputs 3, 15)

### 7.1 Context pressure, adapted for a user at the bench

Workers stop at ~60%. A bench session can't just stop: the board may be powered, probes placed, an A/B/A half-done. The rule:

1. **At ~50%:** tell the user, and plan to finish the current **arm** (not the whole card) or reach a **safe bench stop**: board unpowered or left in a declared state, and nothing a later session has to guess about.
2. **Commit raw data as it arrives.** After every REPORT that contains data, append the raw observations to the card below `--- RUN ---` and commit (`V7R-012: A1 raw`). This is rec 20 at its finest grain. A lost session then loses at most one report, never a result.
3. **At the safe stop:**
   - set the card's `status` (`run` if arms remain, `recorded` if complete);
   - if recorded, update STATE.md in the same commit (§4.2);
   - append the notebook session entry, including **bench state at end**;
   - commit, then stop.
4. **Never above ~70%**, per PROTOCOL Session Management.

**No continuation relay file.** STATE.md (open cards, arm reached), the open card itself and the last notebook entry *are* the handoff, which makes STATE.md the one handoff artefact (rec 17). The next session is just `claude --agent debugger`.

**Compaction:** don't rely on `/compact` or auto-compaction mid-test. A summary carries interpretation and drops numbers. If compaction happens anyway, treat anything not committed in `lab/` as unknown: re-read STATE.md and the open card before the next instruction, and re-ask the user for any number not in the card.

### 7.2 What a handoff may and may not contain

This covers STATE.md, the notebook's `next:` line, PR descriptions, and any prompt written for another session.

| May contain | May not contain |
|---|---|
| Test IDs, commits, tags, file paths with hashes | "If X happens, that supports H" (that's a prediction; it belongs in a pre-registered card only) |
| Board, firmware and bench state | Ranking language without a cited strength label: "lead", "strong", "confirmed", "only remaining", "exhausted", "regardless" |
| Raw observations, verbatim, in symptom terms | A hypothesis's narrative (cite its row or tombstone instead) |
| Strength-labelled status from STATE sections 3–5 | Guidance on how to read the next result |
| What's untested on the map | A recommendation that doesn't cite the map region it addresses |
| Interpretation, **only** when labelled `Interpretation:` and attributed to a card | Copies of STATE content (point to it instead; rec 17) |

The debugger role carries these as rules (Appendix A). The checker greps STATE.md and the last notebook entry for the banned words outside `Interpretation:` lines and warns. It's a cheap guard against the exact PM §4.6 phrasing.

### 7.3 Outside-review and fresh-perspective prompts

A prompt for an outside reviewer (an independent AI session or a forum post, PM rec 10) is **generated when needed, never maintained**:

- **Contents:** STATE sections 1, 2 and 6, plus the raw observations and evidence files of the cards in question, plus a repro.
- **Hypotheses:** the map is omitted, or included only as a list labelled "our guesses" (Raymond: "symptoms, not guesses; label a guess as one").
- **Not committed** as a standing file. The notebook records that a review was requested, what was sent (card IDs) and what came back.

---

## 8. Generated context (inputs 12–14)

### 8.1 Unit of layout context

Agreed with topic 3:

- **L1 for layout questions:** route narratives (Markdown per net: route, layers, vias, neighbours, reference plane per segment) and per-net / per-plane PNGs. A session loads the narrative for the nets under test and opens the image when geometry matters.
- **L2:** raw coordinate JSON (`pcb-routing-context.json`, the board-model cache) is a **cache for scripts**. It is never read into context. A session that needs a number it doesn't contain asks a script.
- Layout claims in cards and STATE cite the narrative or probe (PM rec 11) with its source hash.

### 8.2 Source-hash rule (input 13)

**Every generated context file carries provenance, and every reader checks it.**

- **JSON:** a top-level `_provenance` object:
  ```json
  "_provenance": {"source": "hardware/pcb-main/kicad/motion-play-main.kicad_pcb",
                  "source_sha256": "…", "generator": "tools/pcb-context/board_model.py",
                  "generator_commit": "…", "generated": "2026-11-02"}
  ```
- **Markdown:** the same fields as a front-matter block.
- **Images:** a sidecar `<name>.meta.json`, or the provenance block of the narrative that embeds them.
- **Check:** `tools/lab/check_state.py` (and a `--fresh <file>` mode any session can run) recomputes the source hash and reports **STALE** on mismatch. The debugger runs it before citing a generated file in a card.
- **Scope:** all generated context, including the existing `circuit-context.json` outputs, not only the new board model. The retrofit is a small task in the board-model initiative.
- The rule belongs in `tools/CONTEXT.md` as a standing rule (recommendation; not edited here).

### 8.3 Reading `.kicad_pcb` before the board model lands (input 14)

**Yes. Explicitly allow targeted, read-only kiutils (and `kicad-cli`) probes**, with these rules:

1. **Read-only.** Never write back. Edits still go through the existing tools.
2. **Throwaway script in the scratchpad**, not committed. Its stdout is a handful of numbers or a small table, never a dump.
3. **Raw S-expression text is never read into context.** That part of the existing rule stays.
4. **Cite the probe** in the card or notebook: what it measured, method (edge-to-edge vs centreline), and `file@commit`. Label the result `measured (probe)`. Spot-check in KiCad anything that decides a hypothesis.
5. **Sunset:** once board-model phase 1 lands, probes are for gaps in it only, and each gap becomes a board-model ticket.

Proposed replacement for the `tools/CONTEXT.md` line 5 rule (recommendation only):

> **Never read `.kicad_sch` or `.kicad_pcb` text into context, and never edit them directly.** Use the tools below. Exception: targeted read-only kiutils or `kicad-cli` probes are allowed when no tool output answers the question (e.g. zones, stackup). Run them from a scratch script, print only the numbers you need, and cite the probe and file commit.

---

## 9. Protocol fit

| Option | For | Against |
|---|---|---|
| **(a) Informal**, like this research track | No protocol change. Each relay can be tailored. | The discipline lives in relay text written by a "tired" session, which is the mechanism that decayed last time (PM §4.6). Every session's rules are only as good as the last relay. |
| **(b) Formal `debugger` role** | The rules are loaded verbatim by the harness and identical every session. It fits the protocol's "each agent owns one document type" (it owns `lab/`). Debugging a fault isn't Bugfix: that role verifies a playtest checklist and proposes code fixes; this one runs pre-registered experiments. | One PROTOCOL.md edit (roles table, a non-initiative documents entry for `lab/`, a relay-table row debugger → planner). One more role to maintain. Risk of over-prescription before the workflow has been tried. |
| **(c) Each test batch is an initiative** | Fully in-protocol, no new role. | BRIEF/PLAN/TASKS/SESSION per batch is heavy for a two-hour bench session. Continuity across batches still needs STATE.md, which isn't an initiative document. Test cards don't fit the "no orphan documents" rule. Orchestrator/Worker dispatch assumes autonomous work, but the bench needs the user present. |

**Recommendation: (b)**, as the user chose. Appendix A is a **draft** for the user to edit before first launch.

The design keeps (b) cheap to reverse:
- the role file holds only static rules;
- all state is in `lab/`;
- so pivoting to (a) means renaming the body to `lab/README.md` and pointing relays at it (§3).

**Protocol touch points** (recommendations; PROTOCOL.md is not edited here):
- **Agent Roles:** add a `Debugger` row: owns `lab/` (STATE, NOTEBOOK, cards, logs); function "runs pre-registered bench experiments with the user and keeps state current".
- **Non-Initiative Documents:** a `lab/` entry describing STATE.md (L0, update trigger) and NOTEBOOK.md (append-only).
- **Relays table:** `Debugger session → role:planner → RELAY-planner.md` (in the spawned initiative's folder) when a fix, a design change or a tool is needed.
- **Escalation:** the debugger never implements build work. A firmware change that *is* the experiment (a card's declared delta) is allowed with the user's approval and reverted on null. Anything that outlives the card goes to the Planner.

---

## 10. Does this spawn an implementation initiative?

**Yes: the scaffolding (empty containers, hook, checker, role file, retirements and cleanup), not the content.**

**Recommendation on overlap: merge it into `test-workflow-setup`** (topic 4 §6) rather than running a separate initiative.

Reasons:
- Both create `lab/` and its templates; two initiatives would race on the same directory and conventions.
- topic 4 already left the `lab/` location as a dependency on this topic.
- Its acceptance dry run (§4.2 + §4.3 on the v6 board) is the natural end-to-end test of the debugger role, STATE.md, the hook and the checker as well. One dry run validates both.
- The context work alone is small (one or two sessions), too small to justify its own initiative overhead.

The caveat: if the user wants to trial the debugger role sooner than the bench tooling can land, the Planner can sequence the context scope first within the merged initiative. That is a phasing call, left to the Planner. Sequencing against other initiatives is `decisioning.md`'s call.

### 10.1 Input for the Planner

This section is not a PLAN. It is an **addendum to `test-workflow-audit.md` §6.1**; read the two together.

**Goal (added).** A fresh `claude --agent debugger` session engages from L0 + default L1 (~13k tokens). Its state can't silently go stale, and every legacy handoff artefact is retired or frozen.

**In scope (added):**
- `lab/STATE.md` skeleton with the §4.1 sections, caps and front matter, empty of content (sentinel `as_of: V7R-000`).
- `lab/NOTEBOOK.md` seeded with one entry: "volume 0 = `docs/debugging/v7-i2c-investigation.md`, frozen; legacy IDs `L-PhNN`, `L-Ph24a/b`".
- `tools/lab/check_state.py` with the §4.2 checks, plus `--fresh` (§8.2).
- `.githooks/pre-commit` (§4.2) and a one-line setup note.
- `.claude/agents/debugger.md`, from Appendix A, **as edited by the user**.
- Recommendations for the user to apply, or approve the session applying:
  - PROTOCOL.md edits (§9);
  - the PROJECT.md pointer line (§2.5);
  - the `tools/CONTEXT.md` rule change (§8.3) and source-hash rule (§8.2);
  - retirement banners (§2.4);
  - memory cleanup (§2.5) and the stock tip moved to `hardware/CONTEXT.md`.
- Default-load support (optional, Planner's judgement): a `check_state.py --load` that prints the open cards and last two conclusions, so the session reads one output instead of several files.

**Out of scope (added):**
- Any STATE.md *content*: the map, IS / IS NOT and tombstones are Stage B's, transcribed by the first debugger session (§4.4).
- Source-hash retrofits to extractor outputs (board-model initiative).
- Editing `docs/debugging/` bodies (banners only).

**Acceptance criteria (added):**

| Check | Pass |
|---|---|
| Hook | Recording a dummy card without a STATE.md edit is rejected. With the edit, it passes. |
| Checker | On a fixture `lab/`, it reports STALE, open-card mismatch, CHECKPOINT DUE, a cap overrun, a stale hash and a memory hit, each once. |
| Budget | A fresh debugger session's L0 measures < 500 lines and ≤ ~12k tokens (count the actual files). |
| Dry run | The v6 dry run (topic 4 criterion) is run as a debugger session: card pre-registered, raw data committed per arm, recorded with STATE updated in the same commit, notebook entry written. A second fresh debugger session then states the bench state correctly from L0 + default L1 alone, without asking the user. |
| Retirement | No v7 lines in the memory index; banners on the §2.4 items; PROJECT.md pointer present. |

**Dependencies.**
- Topic 4's templates (card, log) need to exist before the hook can parse card front matter. The Planner orders this inside the initiative.
- The debugger role draft needs the user's edit pass before the dry run.

**Decisions for the Planner to put to the user (added):**
1. Hook mechanism: git `core.hooksPath` (recommended; catches every editor), or a Claude Code hook as well?
2. Section caps: hard (checker fails) or soft (warn)? Recommendation: soft, except `as_of`.
3. Legacy artefacts: banner in place (recommended; keeps cited paths valid), or move to `docs/debugging/archive/`?
4. Card filenames: `V7R-NNN-<slug>.md` (recommended), or bare `V7R-NNN.md`?

### 10.2 Draft relay for the Planner (merged initiative)

This is a draft. Stage B's `decisioning.md` decides whether and when it runs, and may supersede topic 4's §6.2 draft with this one.

````markdown
# Relay — research → planner — <date>

role:planner

## Context
Stage A of the v7 retry recommended a `test-workflow-setup` initiative (topic 4) and context scaffolding
for debug sessions (topic 6), and topic 6 recommends merging them because both build `lab/`.
<decisioning.md: one line on why this runs now.>

## Load these files
- .context/PROTOCOL.md
- docs/research/v7-retry/test-workflow-audit.md — §4.4–§4.9, §5, §6 (skip §2–§3 unless a decision needs them)
- docs/research/v7-retry/context-strategy.md — §2.4, §4, §6, §8.2, §10
- docs/research/v7-retry/decisioning.md — the section on this initiative
- .claude/agents/debugger.md if the user has already finalised it; else docs/research/v7-retry/debugger-role-draft.md

## State
Branch: n/a (cut feat/test-workflow-setup)
Build: n/a
TASKS.md current: n/a

## What was done
- Topic 4 defined card, log, filenames, capture split, instruction block, image handoff; §6.1 is Planner input.
- Topic 6 placed `lab/` at repo root, designed STATE.md / NOTEBOOK.md / hook / checker, drafted a debugger role;
  §10.1 is an addendum to topic 4 §6.1.
- User decisions (2026-10-18): formal debugger role (draft, user will edit); root lab/; one debug track that
  spawns build initiatives; no v7 state in auto-memory.

## Your task
Write BRIEF, PLAN and TASKS for one initiative covering topic 4 §6.1 plus topic 6 §10.1. Phasing is yours.
Raise the decisions listed in both sections with the user at kickoff. Do not fill STATE.md with content;
that is the first debugger session's transcription of decisioning.md.

## Open questions
- Whether the debugger role is trialled before the bench tooling lands (phasing).
- Topic 4 decisions 1–3 and topic 6 decisions 1–4.
````

---

## 11. Check against the failures

### 11.1 Each named failure → the design element that prevents it

| Failure (source) | Prevented by |
|---|---|
| Five handoff artefacts drifted apart (PM §4.6) | One live artefact (STATE.md). Legacy prompts retired with banners. Memory holds no v7 (§2.5). The PROJECT.md pointer can only say open/closed. The role file holds no state. |
| Summary sections not updated when a phase lands (PM §4.6, §5 row) | The pre-commit hook rejects a recorded card without a STATE.md `as_of` bump. The session-start check flags STALE and blocks new work (§4.2). |
| Memory note stuck at ~Ph 6 (PM §5 row) | No v7 memory; the checker warns on a v7 mention in memory (§2.5). |
| Handoffs encoded bias (PM §4.6) | §7.2 may/may-not table; predictions only in pre-registered cards and hidden from the operator (topic 4 §4.8); banned-word check; outside-review prompts generated from symptom sections (§7.3). |
| Phase numbering collided (PM §4.6) | IDs come from `lab/cards/` filenames; the hook rejects duplicates; legacy IDs frozen as `L-PhNN`, `L-Ph24a/b` (§6.2, §2.4). |
| In-place rewriting erased reasoning history (PM §4.6) | STATE.md is rewritten, but each change of belief is a "belief changes" line in the append-only notebook (§5); tombstones are never deleted; plus git history. |
| Results got lost: Phase 25, two commits in the whole investigation (PM §4.6) | Pre-registration commit; raw data committed per REPORT (§7.1); the checker flags a card left in `run` (§4.2). |
| Doc tried to be notebook and briefing; ~56k tokens (PM §4.10) | STATE.md capped at ~150 lines in L0; NOTEBOOK.md in L2, never loaded whole (§4, §5). |
| Refuted stories narrated in full (PM §4.10) | One-line tombstones in STATE; narrative only in the notebook or legacy doc (§4.1 section 5). |
| Embedded audit output (PM §4.10) | Generated content cited by path and hash, never pasted (§2.6, §8.2). |
| Duplicated "what we know" lists (PM §4.10) | One fact, one home: result in the card, standing in STATE (§2.6, §5 table). |
| 70–80k tokens of orientation (PM §4.10) | L0 ≈ 9.5k, plus default L1 ≈ 13k (§11.2). |
| No synthesis; tests optimised against the lead story (PM §4.9) | Hypothesis map in L0 with `Last touched`; checkpoint every 3 cards, enforced; "next test" must name the region it cuts (§4.1 section 8, §4.3). |
| Stale generated files unflagged (topic 3) | Provenance block plus the `--fresh` check (§8.2). |

### 11.2 Budget check

Token estimates are bytes ÷ 4. Sizes of the new files are their caps.

| L0 item | Lines | Tokens |
|---|---|---|
| CLAUDE.md + PROJECT.md (+1 pointer line) | 153 | ~2.8k |
| MEMORY.md index (after deleting two lines) | 4 | ~0.15k |
| debugger.md (cap) | 120 | ~2.0k |
| PROTOCOL.md §Session Management + §Git | 25 | ~0.4k |
| STATE.md (cap) | 150 | ~4.0k |
| **L0 total** | **~452** | **~9.4k** |
| Default L1: 1 open card (~100 lines) + 2 conclusions (~15 lines each) + today's log (~60 lines) | ~190 | ~3.5k |
| **Engaged** | | **~13k** |

That's under the < 500-line target, and about a sixth of the previous orientation cost. The largest lever is the STATE.md cap. If it creeps, the checker warns before the budget is lost.

Not counted: harness system prompt and tool definitions, which are fixed overhead either way.

---

## 12. Deferred to Stage B

| Item | Why deferred |
|---|---|
| Content of STATE sections 1–5 and 7–8 (symptom wording, IS / IS NOT, hypothesis map, facts, tombstones, measurement trust, first next test) | That's synthesis (`decisioning.md`); this topic designs containers only. |
| Whether an assumptions register (PM rec 12) is a STATE section or a separate L1 file | No topic handed it here. Default: rows in STATE section 4 labelled `argued`. Stage B may decide it needs its own file. |
| Sequencing the merged initiative against the board-model initiative and the first debug cards | User decision 2026-10-18: `decisioning.md` sequences. |

---

## Observations for other topics

- **Stage B / synthesis:**
  - Write `decisioning.md`'s hypothesis map, IS / IS NOT and tombstones in the §4.1 table shapes, so the first debugger session can transcribe them without reformatting.
  - Use legacy IDs `L-PhNN`, with `L-Ph24a` (Arduino-as-master) and `L-Ph24b` (Exp 1 glitch filter).
  - If topic 6's merge recommendation is accepted, supersede topic 4's §6.2 relay with §10.2 here.
- **Topic 4 (test workflow), for its Planner:** propose an `ai_read` block per measurement in the log schema (§6.4). The pre-commit hook needs card front matter to be machine-parseable YAML, which the §4.7 template already is.
- **Housekeeping (recommendations only, not done here):**
  - memory cleanup and the stock-tip move (§2.5);
  - the PROJECT.md pointer line;
  - banners on the retired and frozen files (§2.4);
  - the `tools/CONTEXT.md` rule change (§8.3) and source-hash rule (§8.2);
  - PROTOCOL.md role and document entries (§9).

  `hardware/pcb-main/REVIEW-HANDOFF.md` is another frozen handoff prompt from April, unrelated to the I²C debug; it could carry the same "historical" banner.
- **Process note for `RESEARCHER.md`:** the auto-memory notes had been partly corrected earlier the same day, but the index *line* still carried interpretation into L0. Check index lines, not just note bodies, when auditing memory.

---

## Appendix A — Draft `debugger` role (for the user to edit before first launch)

Status: **draft**. The user expects to edit it heavily and may pivot away from the formal role (§3, §9). It isn't installed in `.claude/agents/`; that's the implementation initiative's job after the user's edit pass.

The draft lives in its own file: **[`debugger-role-draft.md`](debugger-role-draft.md)** (next to this artifact). It's written in agent-file format, frontmatter included, so the implementation initiative can copy it to `.claude/agents/debugger.md` once the user has edited it. Edit that file, not this appendix.
