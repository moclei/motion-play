# Expert Approaches to Bring-up and Regression Debugging

> Stage A, topic 5 of 6. Session date: 2026-10-18. Research only. **No principle here is applied to the actual v7 fault**; the "Apply to us" lines describe *process*, not hypotheses.
>
> Agreed with user: scope = *narrow class + bring-up discipline*; citation bar = **high**; post-mortem overlap handled by **cross-reference** (`PM §6.n` = recommendation n in `postmortem.md` §6).

**Source-strength tags** used throughout:
- **[P]** primary text read this session (PDF/full text extracted and quoted).
- **[S]** secondary: book summary, review or excerpt; wording not checked against the original.
- **[own]** our heuristic; no authoritative source found. Stated as ours, not cited.

---

## 1. Scope statement

How experienced engineers debug **a design that previously worked, was redesigned, and now fails with intermittent or ambiguous symptoms on a digital bus (I²C)**, plus the **first-power-on bring-up discipline** that should precede such debugging on a new board revision. Generic software-debugging advice and analog-design technique are out unless they transfer directly.

---

## 2. Principles

Eleven principles. Principles 1–5 are the *bring-up / regression* layer, where the post-mortem had the biggest gaps (block swaps, instrument trust, sequencing). Principles 6–11 are the *reasoning* layer, which mostly backs post-mortem rules with outside sources.

### P1. "Did it ever work?": the difference is the search space

**What it says.** For something that once worked, the first questions are whether it ever worked right, when it stopped, and what changed. The cause almost always lies among the *differences* between the working and the failing case. Search the change list systematically rather than the whole design.

**Why it works.** It turns an unbounded search ("what could break I²C?") into a bounded one (the finite list of v6→v7 deltas). Kepner-Tregoe formalises this. You specify where the problem **IS** and where it **IS NOT**, list the *distinctions* that are true only of the IS cases, and check each distinction against known *changes*. "The most likely cause explains every aspect of the problem." Zeller's delta debugging does the same thing algorithmically: it isolates the minimal difference between a passing and a failing case.

**Apply to us.** v6 is a ready-made IS NOT. Topic 2's `v6-v7-changelist.md` is the change list. A KT-style IS / IS NOT table (what, where, when, extent) built against it should be the first artifact of the retry, before any mechanism story. Every candidate cause must explain *both* columns.

**Sources.**
- Pease, *Troubleshooting Analog Circuits* (1991), ch. 1 "Learn to Recognize Clues", p. 4. "Did it ever work right? … When did it start working badly or stop working? What other symptoms showed up just before, just after, or at the same time as the failure?" [P]
- AHRQ, "Kepner-Tregoe Matrix", Health IT Workflow Assessment Toolkit: "Identify what is different or unusual about events where the problem exists versus where it is absent… for each distinction determine whether it relates to a known change." [P]
- B. Prigge (Kepner-Tregoe), "8D – IS or IS NOT – that is the question" (2022): distinctions "only apply to the IS"; sparse IS NOT data makes testing possible causes "less effective." [P]
- Agans, *Debugging* (2002), Rule 5 sub-rule: "determine what you changed since the last time it worked." [S]
- Zeller & Hildebrandt, "Simplifying and Isolating Failure-Inducing Input", *IEEE TSE* 28(2), 2002. [P]

### P2. Compare against a known-good unit, and swap in both directions

**What it says.** Keep working units on the bench and compare the bad unit against them. When a block is suspect, put a known-good block into the bad circuit, *and* put the suspect block into a good circuit. Swapping is cheap, and it localises the fault to a block before anyone theorises about mechanism.

**Why it works.** A two-way swap is a crucial experiment (P6). Each direction excludes half the possibilities, and the two together catch interaction faults that a one-way swap misses.

**Apply to us.** Backs **PM §6.4** ("swap tests early") and explains §4.1: Phase 3 swapped the slave side only, and the master swap came 21 phases later. For each major block (master, mux, slave, cable, power source, board), the retry's hypothesis map should record whether *both* swap directions have been done. A known-good master on the v7 bus and the S3 master on a known-good bus are distinct tests. A USB-I²C adapter is a reasonable "known-good master" substitute, but that use is [own]; no published procedure was found.

**Sources.**
- Pease (1991), ch. 2, item 16, pp. 22–23. "By comparing a bad unit to a good one, you can often identify problems." Also, from the appendix flowchart: "Swap in a known good amplifier. Swap 'bad' amplifier into a good circuit." [P]
- Agans (2002), Rule 5 sub-rule "compare it with a good one." [S]

### P3. Test the tool before trusting the number

**What it says.** Question your assumptions, starting with the instrument. Compensate probes when connecting them, use the shortest ground lead, and remember that the probe loads the circuit. Validate the setup on a known-good signal or unit before interpreting a measurement from the bad one. When a result is "nothing like the answers I expected", ask first whether the measurement was taken correctly.

**Why it works.** A long ground lead adds inductance that causes ringing on fast edges, so the artefact looks like a circuit problem. Probe-tip capacitance adds to bus capacitance, so the probe can change the thing it measures. A reference measurement on a good unit separates instrument error from circuit behaviour.

**Apply to us.** Backs **PM §6.8–6.9** and is the outside answer to §4.7, where a V_OL above spec on a *working* bus was explained away rather than treated as a check on the setup. Pease names the known-good unit as the instrument check as well as the comparison target, so P2 and P3 share one fixture. For I²C electrical questions, use a scope, not a logic analyser, which "do[es] not capture … rise times, overshoot … VoL values" (TI SCPA063 §3.1).

**Sources.**
- Tektronix, *ABCs of Probes* primer (60W-6053-8). "Always use the shortest ground lead provided with the probe." "Always compensate probes right after connecting them." And: "the loading of greatest concern is that caused by the capacitance at the probe tip." [P]
- SiTime AN10028 §3.2: "Longer ground wire increases ringing after fast signal edges." [P]
- Pease (1991), pp. 5–6: "did I take my measurements correctly? Is my technician's data really valid?" On good circuits, p. 23: "use the good circuits to make sure that your specialized test equipment is working properly." [P]
- Agans (2002), Rule 7 "Check the Plug", sub-rules "question your assumptions… test the tool." [S]
- TI SCPA063, *How to Debug I2C* (2023) §3.1, §3.6. [P]

### P4. Bring up bottom-up: power, clocks, reset, bus electrical, protocol, firmware

**What it says.** On a new board revision, verify layers in dependency order. First inspect visually and check rail impedance for shorts. Power up on a current-limited supply and measure every rail. Then check clocks and oscillators, and only then load firmware and exercise interfaces. For an I²C fault specifically, do the general checks first: schematic, SDA/SCL continuity controller to target, RESET pins biased to a defined level, solder joints. Only after that should you read protocol-level behaviour.

**Why it works.** Every upper layer assumes the ones below it. A protocol symptom caused by a marginal rail or an unbiased reset pin cannot be diagnosed at the protocol layer, however well the protocol is understood.

**Apply to us.** v7 changed the power architecture and moved the S3 onto the board. The retry should open with a short, recorded bottom-up checklist at the declared baseline (**PM §6.2**), so that later phases can cite it rather than assume it. The checklist is a gate before the hypothesis work, not a hypothesis.

**Sources.**
- R. Feranec (FEDEVEL), "9 Steps to Bring up a Freescale i.MX6 Board to Life" (2013). "Always use power supply with limiting current" and "There must not be 0 OHM", then rails, then crystals, then firmware. [P (web)]
- TI SCPA063 §2, "General Checks for Dealing With NACKs": schematic, SDA/SCL path, "bias the reset pin of all I2C target devices to a defined logic level", soldering. [P]
- Strength note: one engineer source plus one TI app note. Vendor blogs agree but are lower-tier, and no Art of Electronics section was located.

### P5. Make it fail on demand, and find the uncontrolled condition

**What it says.** Reproduce the failure deliberately. Stimulate the failure rather than simulating it. An "intermittent" failure is one whose controlling condition hasn't been found yet, so record everything and look for the signature that separates failing runs from passing ones. New hardware designs with intermittent errors are often victims of noise.

**Why it works.** You can't half-split or A/B something you can't trigger. Once the trigger is controlled, every later test becomes fast and unambiguous.

**Apply to us.** The post-mortem's §3.2 reproducer (two resistors, a cable and the diagnostic loop) already follows this principle; keep it. The outside sources add a rule: any residual intermittency (e.g. a result that varies between sessions) is itself a variable to control and record (temperature, supply source, cable position, firmware build). It is not noise to average away.

**Sources.**
- Agans (2002), Rule 2 "Make It Fail": "stimulate the failure, don't simulate the failure, find the uncontrolled condition that makes it intermittent, record everything." Also "New hardware designs with intermittent errors are often the victims of noise." [S, two independent summaries]
- Pease (1991), p. 5, "Record Amount of Funny." [P]

### P6. Strong inference: multiple hypotheses, crucial experiments that exclude

**What it says.** Hold several hypotheses at once. Design each experiment so that its possible outcomes *exclude* one or more of them, and run it to get a clean result. A conclusion that is not an exclusion is insecure. A single working hypothesis breeds attachment, "pressing the facts to make them fit the theory."

**Why it works.** Exclusion is logically decisive and confirmation is not. Many stories can be consistent with a result, but only one can survive an exclusion. Spreading attention across hypotheses also counters fixation on one favourite.

**Apply to us.** Backs **PM §6.1, §6.13** and diagnoses §4.1–4.3. Seven stories were each "consistent with" the constraint list, but few experiments were designed to exclude several at once. Every test card should name *which hypotheses each outcome kills*. Platt's question works as a gate: "what experiment could disprove your hypothesis?"

**Sources.**
- J. R. Platt, "Strong Inference", *Science* 146(3642):347–353 (1964). "Devising a crucial experiment … with alternative possible outcomes, each of which will … exclude one or more of the hypotheses." "Any conclusion that is not an exclusion is insecure." [P]
- T. C. Chamberlin, "The Method of Multiple Working Hypotheses" (1890; repr. *Science* 148, 1965), as quoted in Platt: "when we make a single hypothesis, we become attached to it." [P via Platt]
- R. P. Feynman, "Cargo Cult Science", *Engineering and Science* 37(7), 1974: "The first principle is that you must not fool yourself—and you are the easiest person to fool." [P]

### P7. Predict, then test, and write both down first

**What it says.** Form a hypothesis and *then* invent a test whose answers narrow the possibilities. Keep a logbook with a row per experiment: hypothesis, prediction, experiment, observation, conclusion. Never trust memory with a detail. Pease adds the counterweight: don't plan everything and test nothing ("paralysis by analysis").

**Why it works.** Writing the prediction first stops after-the-fact threshold fitting. Zeller calls debugging without a log "playing Mastermind in memory."

**Apply to us.** Backs **PM §6.1, §6.9, §6.20** almost word for word, so it adds no new rule. Zeller's five-column row is a ready-made starting point for the test card. Topic 4 defines the card; topic 6 decides how it is stored and loaded.

**Sources.**
- A. Zeller, *Why Programs Fail*, ch. 6 "Scientific Debugging", §6.5 "Keeping a Logbook". The example log uses columns Hypothesis | Prediction | Experiment | Observation | Conclusion. [P]
- Pease (1991), pp. 5–6: "always first formulate a hypothesis and then invent a reasonable test… it would be foolish… to plan everything and test nothing." [P]
- Agans (2002), Rule 6 "Keep an Audit Trail": "Never trust your memory with a detail—write it down." [S]

### P8. Change one thing at a time; back out what didn't help

**What it says.** Isolate the key factor and change one variable per test. If a change had no effect, revert it before trying the next. The shotgun approach ("relatively undirected changes… in the hope that a bug will be perturbed out of existence") "almost never works, and usually introduces more bugs."

**Why it works.** With multiple simultaneous changes, the result can't be attributed to any of them, and changes that had no effect quietly become part of a drifting baseline.

**Apply to us.** Backs **PM §6.2** and diagnoses §4.5 (the stacked 100 kHz → CAP_3 → deglitcher → bundled Exp 2+3). The outside sources add the *revert-on-null* rule explicitly: a change that didn't help comes out.

**Sources.**
- Agans (2002), Rule 5: "You've heard of the shotgun approach? Forget it. Get yourself a good rifle." [S]
- *The Jargon File*, "shotgun debugging" (catb.org). [P]

### P9. Look before you theorise, and check magnitudes against the spec

**What it says.** Observe the failure in detail before explaining it, and guess only to focus the search. Where a story depends on an electrical effect, compute whether the effect reaches the threshold before treating it as plausible. For I²C the thresholds are published: V_IL = 0.3·V_DD, V_IH = 0.7·V_DD, rise time measured 30%→70%, t_r ≤ 1000 ns / 300 ns (Sm / Fm), C_b ≤ 400 pF, and controller glitch filters suppress spikes shorter than 50 ns. Pull-up limits follow from R_p(max) = t_r / (0.8473·C_b).

**Why it works.** Qualitative consistency is cheap: any story can be told so that it fits. A number either reaches the spec threshold or it doesn't.

**Apply to us.** This is the outside grounding for **PM §6.5** (magnitude gate). Each candidate mechanism should come with a back-of-envelope calculation against the UM10204 / SLVA689 numbers before it gets scope time. Two documented points are worth carrying into the hypothesis map *as reference facts, not hypotheses*. First, muxes "do not isolate the capacitive loading on either side" (AN10216). Second, a mismatch between controller and target deglitch filters "can contribute to one device seeing the false edge while the other does not" (SCPA069 §2).

**Sources.**
- NXP UM10204, *I²C-bus specification and user manual*, Rev. 7.0 (2021): §3.1.2, Table 10, Table 11, §7.1. [P]
- TI SLVA689A, *I2C Bus Pullup Resistor Calculation* (Arora), §2 and Table 2-1. [P]
- TI SCPA063 §3.6 and TI SCPA069, *I2C Stuck Bus: Prevention and Workarounds* (2024), §2–3. [P]
- NXP AN10216-01, *I²C Manual* (2003), p. 19. [P]
- Agans (2002), Rule 3 "Quit Thinking and Look": "guess only to focus the search." [S]

### P10. Get a fresh view, and report symptoms, not theories

**What it says.** When stuck, ask someone outside the problem. Give them the raw symptoms in chronological order, the diagnostic steps already taken, the recent changes, and a way to reproduce the problem. If you include a guess, label it as one. "It's hard to see the big picture from the bottom of a rut."

**Why it works.** The helper's value is that they don't share your framing. Handing them your theory imports your bias, and the act of trimming a report to its essentials often surfaces the answer.

**Apply to us.** Backs **PM §6.10** (outside review) and **§6.18** (handoffs carry state, not interpretation). The second is the same rule applied to a new AI session: the §4.6 resume prompt that told the next session what result would "support Story D-revised" is exactly the theory-not-symptoms failure Raymond and Agans warn against.

**Sources.**
- E. S. Raymond & R. Moen, "How To Ask Questions The Smart Way" (catb.org). "Describe the problem's symptoms, not your guesses… If you feel it's important to state your guess, clearly label it as such." Also "provide a way to reproduce the problem in a controlled environment" and "Volume is not precision." [P]
- Agans (2002), Rule 8 "Get a Fresh View": "report symptoms (not theories)." [S]
- Electrical Engineering Stack Exchange, "How do I ask a good question?": "Tell us what you found and why it didn't meet your needs." [P]

### P11. If you didn't fix it, it ain't fixed

**What it says.** A symptom that disappears without an understood cause will come back. Check that the problem is really fixed, and that *your* fix is what fixed it, before closing.

**Why it works.** Disappearance without explanation usually means an uncontrolled condition changed (see P5). Verifying the fix means toggling it A/B/A and seeing the symptom follow the fix.

**Apply to us.** Applies to any eventual fix, and to the **v8-buffer recommendation** in particular (PM §4.4, §6.15). A proposed fix has earned its place only when it is shown to remove the symptom *for a mechanism we have isolated*, ideally by A/B/A. A firmware change that makes the NACK go away without an isolated mechanism is a lead, not a fix.

**Sources.**
- Agans (2002), Rule 9: "check that it's really your fix that fixed it, know that it never just goes away by itself." [S]
- J. Ganssle, review of Agans (ganssle.com/rants): "A problem that mysteriously disappears inevitably mysteriously reappears, usually at the worst possible time." [P]
- D. Power, "11 steps to successful hardware troubleshooting", Embedded.com. If bugs "appear to go away by themselves… you can be sure that you haven't fixed the bug." [P]

---

## 3. Techniques

| Technique | Verdict | Backing | Notes for our class of problem |
|---|---|---|---|
| **Golden-board A/B** | **Adopt** | Pease ch. 2 & flowchart [P]; Agans R5 [S] | The v6 board (and any T-Display rig) serves as both the comparison unit *and* the instrument reference (P2, P3). Do the swap in both directions. |
| **IS / IS NOT table (Kepner-Tregoe)** | **Adopt** | AHRQ KT matrix [P]; KT/Prigge [P] | Not in the relay's candidate list, but it is the most directly applicable method found for working-then-broken problems. Build it against the topic 2 changelist. |
| **Signal-chain partitioning** (power → clock → reset → bus electrical → protocol → firmware) | **Adopt for bring-up** | Feranec [P]; TI SCPA063 §2 [P] | Use it as a one-time gate per board/baseline (P4), not as the main fault search. |
| **Half-splitting / binary isolation** | **Adopt with caveat** | Pease pp. 5–6 (128 resistors in ~7 trials) [P]; HP *Bench Briefs* Mar–Apr 1974 [P] | HP: it applies most readily where "the circuit under test is a linear path". A shared I²C bus is *not* linear, because every device sits on the same two nets. Split by *function or segment* (mux channels, master vs. slave, cable vs. no cable), not by position along a wire. |
| **Minimum reproducing subset** | **Adopt** | NXP AN10216 slide 55 [P]; Agans R4 [S] | AN10216 describes the I²C version: disable all mux channels, then re-enable them one by one "until the bus hangs again". Depopulating components is an application of the same idea [own]. Use a sacrificial board (PM §6.7). |
| **Written falsification criteria** | **Adopt** | Platt [P] | Each test lists the hypotheses each outcome excludes (P6). |
| **Pre-registered predictions / test card** | **Adopt** | Zeller §6.5 [P]; Pease [P] | Use Zeller's five-column logbook row (P7). Topic 4 owns the format; topic 6 owns storage and loading. |
| **Scope before logic analyser for electrical questions** | **Adopt** | TI SCPA063 §3.1 [P]; Tektronix ABCs [P] | Use a logic analyser for protocol sequencing and a scope for levels, edges and V_OL. Validate probe setup first (P3). |
| **Shotgunning** | **Reject as a default** | Jargon File [P]; Agans R5 [S] | [own] exception: cheap, *recorded*, reversible swaps that are then re-tested one at a time. That is parallel triage, not undirected change. No authoritative source endorses even this, so use it sparingly. |

---

## 4. Anti-patterns

| Anti-pattern | Why it fails | Source | Post-mortem instance |
|---|---|---|---|
| **Reasoning from absence of evidence** (non-exclusion conclusions) | "Any conclusion that is not an exclusion is insecure and must be rechecked." | Platt 1964 [P] | "Non-scope option space exhausted" (Ph 15); datasheet silence as evidence (Ph 10) |
| **Single-hypothesis attachment / confirmation** | It leads to pressing facts to fit the theory. | Chamberlin via Platt [P]; Feynman [P] | Lead story declared dominant and then refuted 4× (PM §5) |
| **Fitting parameters after the fact** | Same mechanism as above: the theory gets tuned to the data. | Chamberlin via Platt [P]; Zeller (predict before experiment) [P] | Ph 21 inferred "effective V_IL" |
| **Changing several variables at once / shotgunning** | The result can't be attributed to any one change. | Agans R5 [S]; Jargon File [P] | Ph 22–25 stacked changes; Ph 25 bundled two |
| **Theorising instead of looking** | Guesses should only focus the search. | Agans R3 [S] | Placement-only geometry arguments (PM §4.8) |
| **Chasing an intermittent without controlling conditions** | Intermittency means an uncontrolled condition. | Agans R2 [S] | Ph 21 → 23 ~13× V_OL swing, setup not recorded |
| **Trusting an unvalidated instrument** | Probe artefacts look like circuit behaviour. | Tektronix ABCs [P]; Pease [P] | Ph 21 baseline above spec on a working bus |
| **Declaring victory when the symptom vanishes** | It will reappear. | Agans R9 [S]; Ganssle [P]; Power [P] | Risk for any upcoming firmware experiment |
| **Trusting memory / unrecorded results** | Details are lost. | Agans R6 [S]; Zeller §6.5 [P]; Pease [P] | Ph 25 result lost |
| **Sunk-cost continuation** | Prior investment raises estimated chance of success and the urge to continue. | Arkes & Blumer, "The psychology of sunk cost", *OBHDP* 35:124–140 (1985) [S, abstract-level] | "v8 regardless" carried unchanged across phases (PM §4.4) |

Not included, for lack of a verified source this session: Kahneman's anchoring and confirmation framing, and NASA or aviation root-cause guidance.

---

## 5. Decision frameworks

The honest finding first: **no authoritative source was found that gives an explicit rule for when to stop debugging and respin a board.** Only vendor blogs turned up, and they boil down to "rework for assembly defects, respin for design errors". The heuristics below are therefore **[own]**, built on sourced principles, and labelled as such so the synthesis session can weigh them.

### 5.1 When to stop debugging and redesign [own]

Respin when **all three** of these hold:
1. **The mechanism is isolated** to a design-level difference. It reproduces on more than one board (PM §3.5) and has been excluded by test (P6), not just argued.
2. **The fix has been verified** on the current board by an A/B/A bodge or firmware toggle (P11). A respin is a fix, so it must earn its place the same way (PM §6.15).
3. **The remaining unknowns are cheaper to resolve on the new board** than on this one.

Also consider respinning, *as a deliberate parallel track*, when the hypothesis map shows the remaining untested regions all require tests that are irreversible or need instruments we don't have. When doing so, record explicitly that the respin is not evidence about the mechanism.

**Timebox [own]:** set a test budget per hypothesis-map region before starting (e.g. N test cards). On exhausting it, run the PM §6.14 step-back checkpoint *before* continuing. Sunk-cost research (Arkes & Blumer) is the reason for deciding the budget in advance rather than mid-stream.

### 5.2 When to ask a forum or an outside expert

- **Trigger [own]:** (a) a single interpretation-critical measurement will decide a hypothesis (PM §6.10), or (b) two step-back checkpoints in a row haven't changed the hypothesis map.
- **What to post** (Raymond [P]; EE.SE [P]; Agans R8 [S]):
  - the raw symptoms, in chronological order
  - the diagnostic steps already taken and their results
  - the recent changes (the v6→v7 changelist)
  - a minimal reproducer
  - the schematic and the relevant layout
  - guesses labelled as guesses, or left out
- **Add the measurement setup** (probe, attenuation, ground method, bandwidth limit) with every capture [own; no source found requiring it, but it follows directly from P3].
- **Keep it short:** "Volume is not precision" (Raymond). Trimming the report is itself a debugging step.

### 5.3 When to pay a consultant [own]

No credible source found. A suggested threshold is to escalate when §5.2 has been tried and either the fix decision is blocked on a measurement we can't make or validate ourselves, or the cost of another failed respin exceeds the consultant cost.

---

## 6. Reading list

The few worth actually reading, in priority order:

1. **D. J. Agans, *Debugging: The 9 Indispensable Rules…*** (AMACOM, 2002). Short, hardware-aware, and the backbone of most principles here.
2. **R. A. Pease, *Troubleshooting Analog Circuits*** (Newnes, 1991), ch. 1–2. The "did it ever work", good-unit and instrument-trust material is directly applicable despite the analog title.
3. **TI SCPA063, *How to Debug I2C*** (2023). The most practical I²C-specific checklist found. Pair it with **TI SCPA069, *I2C Stuck Bus*** (2024) for noise and false-edge mechanisms.
4. **NXP UM10204, *I²C-bus specification*** Rev. 7.0, §3.1, §7, Tables 10–11. The numbers for every magnitude gate.
5. **J. R. Platt, "Strong Inference"**, *Science* 1964. Seven pages, and the clearest statement of why exclusion beats consistency.
6. **A. Zeller, *Why Programs Fail*, ch. 6.** The logbook template and scientific-debugging loop.
7. **Tektronix, *ABCs of Probes*.** Read the ground-lead, loading and compensation sections before the next scope session.
8. **E. S. Raymond, "How To Ask Questions The Smart Way".** Read before any forum post *or* any AI handoff.

---

## Observations for other topics

- **Topic 4 (test/scope workflow audit):** P3's sources (Tektronix ABCs, Pease) give an outside basis for the instrument-validation step. Re-check scope findings against ground-lead length and probe loading first. TI SCPA063 §3.6 defines rise time as 30%→70%.
- **Topic 4 (test workflow), test card:** Zeller's five-column logbook row is the suggested starting point for the test-card format, extended with the fields from P6 (outcomes → hypotheses excluded) and P8 (declared baseline, revert-on-null).
- **Topic 6 (context strategy):** decide how test cards and the log are stored and loaded (topic 4 owns their format). Raymond's "symptoms, not guesses" is a ready-made rule for handoff prompts (PM §6.18). The IS / IS NOT table (P1) is a candidate standing section of the current-state file.
- **Synthesis (Stage B), not a hypothesis:** the external record includes a documented ESP32-S3 I²C *master* misbehaviour (espressif/esp-idf #8543: SCL clocking after STOP on IDF release/v4.4, fixed 2022; the ESP32 original was unaffected). Espressif docs also give glitch-filter (`glitch_ignore_cnt`, typical 7) and pull-up guidance. These are reference facts for the hypothesis map. Their relevance to v7 is unassessed; the ESP32-S3 errata page could not be checked this session.
- **Unverified leads** (excluded from the principles above): ADI AN-686 *Implementing an I²C Reset* (fetch failed; UM10204 §3.1.16 covers the nine-clock bus clear); Agans sub-rule wording (secondary only); Kahneman; NASA RCA guidance.
