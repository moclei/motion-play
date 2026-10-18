# v7 Debug Post-Mortem — Methodology Audit

> Stage A, topic 1 of 6. Session date: 2026-10-18. Scope: **how** the prior v7 I2C investigation was run, not what the fault is. No new hardware hypotheses are formed here; where a past result is questioned, it is questioned as a matter of method (was the test valid, was the conclusion warranted), not as a proposal for what is really going on.
>
> Inputs: `docs/debugging/v7-i2c-investigation.md` (primary), `v7-i2c-session-resume.md`, `v7-i2c-fresh-perspective-prompt.md`, `i2c-oscilloscope-debugging.md`, `docs/explorations/esp32-s3-i2c-master-deep-dive.md`, `docs/explorations/bq_solder_sda-catmull.md`, git history, user memory note `project_v7_i2c_bq_debug.md`. Findings were sanity-checked with the user before finalizing; the user's own retrospective concerns are folded in (§4.7–4.10).

---

## 1. Session timeline summary

The investigation ran roughly **2026-04-21 → 2026-05-02** (Phases 1–5 are undated and probably predate that), across an estimated **10–12 working sessions** and **25 numbered phases** (two of them both labelled "Phase 24"). It moved through four broad stages: (a) **localisation** (Phases 1–9) — DMM checks, firmware instrumentation, an Arduino on the rigid proving the sensor side healthy, the bus diagnostic loop, the pull-up/cable discriminators, and confirmation on a second healthy board that the fault is design-level (with Board 1 lost to a bodge along the way); (b) **behavioural narrowing** (Phases 10–19) — datasheet review, a burst of six A/B behavioural tests on a single day (04-24) that pinned the trigger to "SDA, pulled toward +3.3 V, via cable, live while connected", a routing audit, a datasheet drill, a VBUS test, and a literature search, while Story D → D-revised was carried as the lead hypothesis; (c) **scope phase** (Phases 20–23) — direct probing at BQ pin 6 refuted the V_IH story, a V_OL story was proposed and declared confirmed, then refuted two phases later; (d) **master-side turn** (Phase 24–25) — the Arduino-as-master test showed a SAMD21 master gets ACKed on the same wire, moving the mechanism to the ESP32-S3 master; a firmware experiment plan was written and the first two experiments run (Exp 1 null; Phase 25's result was never recorded and the user does not remember whether it ran). The project was then set aside for ~5½ months.

Git provides almost no sequencing: only two commits carry the `v7-i2c-debug` prefix (Phases 17 and 18, both 04-26). The investigation doc first appears in git at Phase 16 (already 840 lines). Phases 19–25 and both exploration docs landed in one WIP commit on 2026-10-17, bundled with unrelated mechanical/firmware changes.

---

## 2. Hypotheses chased — scored

Legend — **Falsifiable?** was the hypothesis stated so a result could refute it, before the test. **Pre-committed?** were pass/fail outcomes written down before running. **One variable?** did the test change only the variable under study. **Conclusion strength:** *strong* = positive evidence against/for; *moderate* = clean test but narrow or with a caveat; *weak* = absence of evidence, argument, or invalid test.

| # | Hypothesis | Phase | Falsifiable? | Pre-committed? | One variable? | Conclusion strength | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Sensor-side defect (VCNL/PCA/flex) | 3 | Yes | Implicit | Yes (master + topology swapped together, but in the "exonerate" direction) | **Strong** | Clean exoneration. |
| 2 | Pull-up strength / rise time | 2, 5 | Yes | No | Yes | **Weak→moderate** | 4.7k/10k/47k external only moved the *combined* pull-up 1.5k→2.1k. Doc and memory both flag the test as weak, but the "ruled out" table still lists it as settled. |
| 3 | I2C clock speed | 2, 22 | Yes | Phase 22 yes | Yes | Moderate | Two separate null tests. |
| 4 | ESP32 RF coupling | 6b | Yes | Implicit | No (flag also skips WiFi/MQTT init) | Moderate | Null result, so the confound doesn't matter much. |
| 5 | Per-channel routing defect | 6c | Yes | Implicit | Yes | **Strong** | Fault follows the cable. |
| 6 | Cable stub capacitance alone | 5, 6d | Yes | Implicit | Yes | **Strong** for "stub alone insufficient" | |
| 7 | Lower pull-ups suppress injected noise (bodge) | 7 | Yes | No | Yes | **None** — test destroyed Board 1, no data | Irreversible rework on what was then the only known-good board. |
| 8 | BQ in a documented I2C-suppressing mode | 10 | Partly | Yes (5 written questions) | n/a (datasheet) | **Weak** (absence of documentation) | Correctly labelled "undocumented behaviour" rather than "impossible". Later made moot by Phase 24. |
| 9 | Rail perturbation through cable loop | 11 | Yes | Yes | Yes | Moderate | Assumed ~330 µA was never measured; the queued DMM verification never happened. |
| 10 | SDA vs SCL asymmetry | 12 | Yes | Yes | Yes, **A/B/A live swap** | **Strong** | Model test. |
| 11 | Story A naive (phantom START) / Story B naive (edge degradation) | 13 | Yes | **Yes — predictions for both written beforehand** | Yes | Moderate ("weakened", honestly labelled) | Model test. |
| 12 | Story C (rail noise injection) | 14 | Yes | Yes | Yes, A/B/A via PSU toggle | **Strong** | |
| 13 | Story A residual (stuck state machine) | 15 | Yes | Yes | Yes | Strong for the narrow claim | Conclusion text then overreached: "all cheap non-scope mechanisms are now eliminated." |
| 14 | Routing-asymmetry EMI | 16 | Yes | Implicit | n/a (measurement) | Moderate–strong | Tool spot-checked against KiCad. Table entry overreached: "mechanism is internal to BQ's SDA input stage" — later contradicted by Phase 24. |
| 15 | Story D original (ESD-diode injection) | 17 | Yes | n/a | n/a (datasheet) | Moderate | Inference ("almost certainly a snapback structure") stated as fact downstream. Credit: we refuted our own lead story. |
| 16 | Cable-as-EMI-antenna (Story E variant) | 17 | — | — | — | **Weak** (argument from geometry, not tested) | Recorded in the "ruled out with evidence" table. |
| 17 | USB-C / VBUS state | 18 | Yes | Yes | No (power source + busrec firmware) | Moderate | Null result, so confounds are tolerable. Good bonus observation (live vs latched). |
| 18 | Story D-revised (V_IH violation via crosstalk) | 17→20 | Yes | **Yes (1.3 V threshold)** | Yes | Strong *if the measurement is valid* | Promoted to "dominant" for ~4 phases without a magnitude check. Requiring a 3.3 V line to drop below 1.3 V from crosstalk was implausible before measuring. |
| 19 | Story G-revised (V_IL violation via V_OL rise) | 21→23 | Yes | **No** in Ph 21 (threshold fitted after the fact); **yes** in Ph 23 (~350 mV predicted) | Yes | Ph 21 "confirmed" = **invalid**; Ph 23 refutation = strong *if the measurement is valid* | Ph 21 inferred "effective V_IL ~800–900 mV" to fit the data, then declared confirmation. See §4.2 and §4.7. |
| 20 | Story F (S3 master) vs Story H (BQ input) | 24 | Yes | **Yes** (both outcomes written in Ph 17–23) | **No** — different MCU, clock, drive, timing, library | **Strong** for "master-dependent"; uninformative about *which* master property | No side-by-side waveform capture of the two masters, though probes were already on pin 6. |
| 21 | Exp 1: I2C controller deglitcher | 24 | Yes | Yes (deep-dive §4 table) | Added on top of an accumulated stack (100 kHz, CAP_3) | Moderate (null) | |
| 22 | Exp 2+3: pad filter + explicit pull disable | 25 | Yes | Yes | **No — bundled two** | **Unknown** — result never recorded | User doesn't remember whether it ran. |

**Summary:** falsifiability and pre-committed criteria were **good from Phase 11 onward** and poor before. Single-variable discipline was strong for the behavioural tests (11–15) and degraded in the scope/firmware stage (22–25). Conclusion *strength* was usually labelled honestly in each phase's results paragraph. The problem was the *summary* text (tables, status banner, "what remains" lists), which repeatedly claimed more than the result supported.

---

## 3. What we did well — keep these

1. **A/B/A live toggles.** Phases 12, 14, 15, 18 swapped the variable on and off while the diagnostic loop kept running (wire in/out, PSU on/off). Same board, same firmware, same moment — this is the gold standard and gave our most trustworthy results.
2. **A deterministic, cheap, repeatable reproducer.** Two resistors + a JST-SH cable + the `runBusDiagnosticLoop()` table. Reducing the trigger to a minimal fixture early (Phase 5) made every later test fast.
3. **Instrumentation before hypotheses.** Error-code logging (2 vs 5), channel readback verification, early power logging, build-flag-gated diagnostic envs (`-diag`, `-busrec`, `-relbus`). Each one closed a class of question permanently.
4. **Predictions written before tests** (Phases 13, 14, 15, 20, 22, 23, 24, deep-dive §4). When this was done, the results were unambiguous.
5. **Reproduction on a second healthy board** (Phase 9) — moved "assembly defect" off the table correctly and early.
6. **Willingness to refute our own lead story.** Phase 17's datasheet drill killed the original Story D; Phase 20 and 23 killed D-revised and G-revised by direct measurement rather than rationalising.
7. **Building tools instead of eyeballing.** Datasheet capture + stripper (Phase 10), routing extractor/auditor with KiCad spot-checks (Phase 16). Reusable and verified.
8. **Getting the probe to the right place.** Moving from TPIO43 to BQ pin 6 via Sensepeek (Phase 20) rather than inferring pad behaviour from 34 mm away.
9. **Explicit "fresh perspective" requests.** The user recognised tunnelling risk and asked for a framing challenge mid-investigation. It did produce Phase 17.
10. **Writing things down.** The investigation doc is detailed enough that this post-mortem was possible at all.

---

## 4. What went wrong, methodologically

### 4.1 Frame lock: "BQ is the canary at the far end of a marginal bus"

Phase 4 interpreted BQ's NACK as a bus-margin symptom because BQ is the physically furthest slave. That framing was written into the TL;DR, the architecture section, and the "what BQ fails means" note. It was never tested (the INA-vs-BQ difference was never probed on its own). It steered every subsequent story — A, B, C, D, D-revised, E, G — toward **the receiver and the bus**. The master was never treated as a variable until Phase 17, and not tested until Phase 24. The Phase 3 Arduino test swapped the *slave side* to exonerate the sensors; the inverse swap (a different master on the main bus) is a standard early bring-up move and would likely have redirected the investigation ~20 phases earlier. Its blocker (needing a way to release the bus from the ESP32) was a small firmware flag.

### 4.2 Conclusions outran evidence in the summary layers

Individual results paragraphs were usually careful. The summary layers were not:
- Phase 15: "all cheap non-scope mechanisms are now eliminated" / "non-scope option space is exhausted" — the cheap, non-scope Arduino test was decisive nine phases later.
- Phase 16 ruled-out table: "mechanism is internal to BQ's SDA input stage."
- Phase 21: "Story G-revised is the mechanism… confirmed by direct measurement," resting on an *effective threshold inferred from the same data* (post-hoc curve fitting).
- "Ruled out with evidence" table includes arguments (cable-as-antenna, ESD snapback inference) alongside measurements, with no strength marker.

Readers (including new sessions) consume the summary layers, so the overreach compounded.

### 4.3 No magnitude/plausibility gate before promoting a story

Stories were promoted to "dominant" based on whether they were *qualitatively consistent* with the constraint list, not whether the numbers worked. D-revised needed SCL crosstalk to drag a 3.3 V line below 1.3 V on a 2.2 kΩ-pulled bus — a back-of-envelope estimate would have ranked it low before scope time was spent on it. The constraint list grew so long (SDA-only, polarity-only, source-independent, resistance-invariant, live, recovery-immune…) that *any* story that ticked every box qualitatively looked strong, even though none had a quantitative mechanism.

### 4.4 The fix recommendation was immune to evidence

"v8 with an I2C buffer remains the architectural answer regardless" appears in nearly every phase, re-justified against whichever story was leading (A/B, then C/D, then D-revised/E/F, then F/H). After Phase 24 put the mechanism in the master, the claim was carried forward unchanged and not re-derived. A recommendation that survives every possible result isn't being tested by any of them. That may still be the right call, but it was never earned.

### 4.5 Multi-variable drift in the late stage

From Phase 22 on, firmware changes accumulated instead of being reverted: 100 kHz clock → CAP_3 drive → deglitcher on → (Phase 25) pad filter + pull disables bundled together. Keeping the filter on was argued explicitly ("removing it would conflate two changes"), which is reasonable locally. But the result was a moving baseline that was never re-measured from clean. Phase 24's master comparison changed MCU, library, clock, drive and timing at once, so it localised the fault to "the master" without narrowing *what about* the master, and no comparative waveform of the two masters was captured.

### 4.6 Session discontinuity and handoff decay

- **Multiple handoff artefacts drifted apart:** the investigation doc, the resume prompt (frozen at post-Phase-18), the fresh-perspective prompt (pre-Phase-17), the scope guide (post-Phase-17), and the memory note (still naming "noise antenna" as the top hypothesis). Each was a snapshot; none was retired when superseded.
- **The main doc is stale in its own summary sections:** the status banner is at Phase 25, but "Fastest read → What hasn't been tried yet", TL;DR "Next test", and "Candidate fixes #2" still treat Arduino-as-master as pending.
- **Handoffs encoded bias, not just state.** The resume prompt told the next session that any parasitic-sensitive result is "strong support for Story D-revised" and that the scope would see "exactly what Story D-revised predicts." The scope guide's outcome table inverted Story F's logic and, in another branch, forgot F existed.
- **Phase numbering collided:** the solder-plan doc's "Phase 19 scope session" is not the investigation doc's Phase 19 (a literature search); there are two Phase 24s.
- **In-place rewriting erased reasoning history.** "Current working theory" was overwritten each time, so how a belief evolved is only recoverable by reading every phase in order.
- **Results got lost.** Phase 25's outcome is unrecorded and unremembered. Infrequent commits (two in the whole investigation) meant there was no checkpoint to recover from.

### 4.7 Measurement validity was never independently checked *(user concern)*

The user flags inexperience with the oscilloscope and with electronics generally as a real doubt about whether tests were performed and interpreted correctly. The record supports that concern as a **process gap**: there was no step anywhere that validated the measurement setup itself before trusting the number.
- **Phase 21 baseline anomaly.** With *no cable* (BQ ACKing), V_OL at BQ pin 6 was measured at ~650 mV average / ~790 mV peak — well above BQ's 0.4 V V_IL(max) and its V_OL spec, on a bus where every slave was working. Rather than treating that as a red flag about the measurement (probe ground lead length, 10× setting, bandwidth limit, cursor placement, which feature was being measured), the session explained it away by inventing a higher "effective V_IL." Phase 23 then got ~50 mV under a different drive setting. Both numbers fed refutations. If the measurement setup was off, Phases 21 and 23 (and possibly 20) are less solid than the doc says.
- No known-good reference measurement (e.g., the same probe on a T-Display/v6 board's bus, or on a bench-known signal) was taken to calibrate the setup.
- Scope configuration, probe ground method and screenshots are only partially recorded, so results can't be re-audited after the fact.

### 4.8 Circuit/layout understanding was taken on trust *(user concern)*

The user is unsure whether traces, component circuitry and proximity were being understood correctly. Methodologically:
- Early reasoning about layout (Phases 4–15) used **placement-only** extractions — positions, no traces — but made claims about bus geometry ("far end of the upstream bus", "~55 mm from the pull-ups") that depend on routing. Phase 16 added routing data, but the earlier framing it was supposed to check (the far-end canary story) was never revisited.
- Component behaviour was frequently inferred from general knowledge and accepted as fact downstream (TCA pass-gate pinch-off implications in Phase 19, ESD snapback in Phase 17, "BQ has unusually strict input thresholds" in Phase 21). Where these inferences conflicted with each other or with measurements, the conflict wasn't flagged.
- The extraction tooling's correctness (circuit-context, pcb-layout-context) was never itself audited — that is topic 3's job, but it means every layout-based argument here carries an unquantified risk.

### 4.9 No bigger-picture synthesis *(user concern)*

The doc is organised as a chronological log plus a list of ruled-out items. There was no single, maintained view of: what the full hypothesis space was (master / bus / slave / mux / power / firmware), which regions had actually been tested vs argued away, and what the evidence *strength* was per region. Each session optimised the next test against the current lead story rather than against the whole space. That is how the master side stayed unexplored for so long while the receiver side got tested from five angles. "Story" labels (A–H, plus -revised variants) piled up without a map of how they related.

### 4.10 Context budget was consumed by orientation *(user concern)*

The investigation doc is ~1,190 lines / ~56k tokens on its own. A fresh session following the resume prompt's load list (investigation doc + fresh-perspective prompt + scope guide + PROJECT.md) loaded roughly 70–80k tokens of history before it could do anything, and much of that was superseded reasoning (refuted stories still narrated in full, embedded audit output, duplicated "what we know" lists, stale summary sections). There was no compact, authoritative current-state file separate from the historical log. The doc tried to be both the lab notebook and the briefing, and grew too big to be either well.

---

## 5. Patterns that recurred across sessions

| Pattern | Occurrences |
|---|---|
| **Lead story declared dominant/confirmed, then refuted within 1–3 phases** | Story D (Ph 13–14 → refuted 17); D-revised (17 → 20); G-revised ("confirmed" 21 → refuted 23); "mechanism internal to BQ input stage" (15–16 → contradicted 24). |
| **"Option space exhausted" / "only remaining test" claims** | Ph 15 ("non-scope option space exhausted"), Ph 18 ("only remaining cheap pre-scope test"), Ph 23 ("uncontested top priority"), deep-dive §7 ("only with a sub-ns scope… v8 regardless"). |
| **v8 buffer reasserted as correct regardless of mechanism** | Ph 12, 13, 14, 15, 17, 18, 19, 22, 23, 24, scope guide, resume prompt. |
| **Test identified as decisive, then deferred for several phases** | Arduino-as-master: named at Ph 17, top priority at 18, 19, 22, 23; run at 24. Phase 11 current measurement: queued at 18, never run. Bench-PSU: deferred at 10, run at 18. |
| **Summary sections not updated when a phase lands** | TL;DR "Next test" (stuck at post-18), Fastest-read "What hasn't been tried" (stuck at post-23), Candidate fixes #2 (stuck pre-24), memory note (stuck at ~Ph 6). |
| **Post-hoc parameter fitting to keep a story alive** | Ph 14 (cable-distance "consistent with D if ringing changes"), Ph 17 (D reframed rather than dropped), Ph 21 (effective V_IL inferred). |
| **Accepting an inference as a measured fact in later phases** | ESD snapback, TCA pinch-off, BQ "unusually strict" thresholds, "~5–10 pF" cable C (never measured). |

---

## 6. Recommendations for the retry

Concrete process rules. Those marked **→6** feed directly into topic 6 (context strategy).

### Experimental discipline
1. **Pre-register every test.** Before running: hypothesis, the variable changed, the expected result under each live hypothesis, and what each outcome will lead us to conclude. Write it in the log *before* the run; record the result next to it. No retroactive thresholds.
2. **One variable per test, against a clean baseline.** Revert to a declared baseline firmware/hardware config between experiments unless there's an explicit, written reason to stack. Re-measure the baseline at the start of each session.
3. **Prefer A/B/A live toggles** wherever possible — they were our best tool.
4. **Swap tests early.** In bring-up, swap each major block (master, slave, mux, power source, cable, board) against a known-good substitute before forming mechanism stories. Treat "master" as a variable from day one.
5. **Magnitude gate before promotion.** No hypothesis becomes "lead" until a back-of-envelope estimate shows the effect size can plausibly reach the threshold.
6. **Label conclusion strength explicitly** in every summary: *measured-refuted / measured-supported / argued / not tested*. Arguments never go in a "ruled out with evidence" table.
7. **No irreversible actions on the only good unit.** Rework/bodges go on a sacrificial board first, or wait until a second known-good unit exists.

### Measurement validity *(user concern)*
8. **Validate the instrument before trusting the number.** For each new scope setup: measure a known-good reference (a working v6/T-Display bus, or the cable-out baseline) and check it against datasheet expectations. A baseline that violates spec on a working bus is a stop-and-investigate signal, not a parameter to fit.
9. **Record setup with every measurement:** probe, attenuation, ground method/length, bandwidth limit, trigger, timebase, cursor positions, and a saved screenshot/CSV committed to the repo.
10. **Use outside review for interpretation-critical measurements.** When a single scope reading decides a hypothesis, get a second look (an independent AI session with only the raw captures, or a forum/expert) before recording it as refutation.

### Circuit/layout understanding *(user concern)*
11. **Ground layout claims in routing data, not placement**, and cite the source (tool output or KiCad measurement) inline. Any argument from physical geometry carries a citation or is marked "argued".
12. **Keep a component-behaviour assumptions register:** each inferred behaviour (pass-gate, ESD structure, input thresholds) gets one line with its source and confidence, so conflicts become visible.

### Synthesis and big picture *(user concern)*
13. **Maintain a hypothesis map, not just a log.** A single-page view of the whole fault space by subsystem (master / bus / mux / slave / power / firmware / measurement), each region marked tested / argued / untested, with evidence strength. Update it after every test. Pick the next test to cut the *map*, not to probe the current favourite.
14. **Periodic "step back" checkpoint** every N tests (say 3–4) or at each session start: re-read the map, ask what region is untested, and whether the lead story has earned its place.
15. **Re-derive the fix recommendation** whenever the mechanism estimate moves. Never write "regardless."

### Context and continuity *(user concern)* **→6**
16. **Split the briefing from the notebook.** A short (≤ ~3–5k tokens), authoritative *current-state* file — facts with strength labels, hypothesis map, baseline config, next test — is all a new session loads by default. The chronological lab notebook is append-only and loaded only for targeted lookups.
17. **One handoff artefact, retired when superseded.** No parallel resume/fresh-perspective/memory snapshots that drift; if a snapshot is needed, it points at the current-state file rather than restating it.
18. **Handoffs carry state, not interpretation.** No "if X happens, that supports our story" guidance in resume prompts.
19. **Refuted hypotheses get one-line tombstones** in the current-state file (what, refuted by which test, strength), with full narrative only in the notebook.
20. **Commit after every test result**, with a stable, never-reused test ID (no "Phase 24" twice). An unrecorded result (Phase 25) should be impossible.

---

## Observations for other topics

- **Topic 2 (v6→v7 changelist):** the master changed from T-Display-S3 module to ESP32-S3 on-board, and the I2C pins/pull-ups/topology changed. Given Phase 24, the changelist should explicitly cover the master-side differences (pins 43/44, drive, pull-ups, firmware env/library versions), not just board-level circuitry.
- **Topic 3 (KiCad extraction audit):** early layout reasoning relied on placement-only JSON; the routing extractor was spot-checked but not systematically validated. §4.8 depends on this audit.
- **Topic 4 (test/scope workflow audit):** the Phase 21 baseline V_OL anomaly (~650 mV on a working bus, above the 0.4 V spec) and the Phase 21→23 ~13× swing are the first things to scrutinise. Also: whether Phase 25 ran, and what the current firmware baseline actually is (accumulated debug changes in `SensorManager.cpp`).
- **Topic 5 (expert approaches):** compare our sequencing against standard bring-up practice, specifically block-swap-first and instrument calibration.
- **Topic 6 (context strategy):** recommendations 16–20 above; the ~56k-token investigation doc is the concrete anti-pattern to design against.
- **Housekeeping (not done here, out of scope):** the memory note `project_v7_i2c_bq_debug.md` is materially stale (names a refuted top hypothesis) and will mislead future sessions until updated or retired.
