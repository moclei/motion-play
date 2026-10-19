# Test Workflow Audit: Measurement Validity and Bench Logistics

> Topic 4 of 6 in v7-retry Stage A. Produced 2026-10-18 on `research/v7-retry`.
>
> **Inputs:** post-mortem (§4.5–4.7, §6), expert-approaches (P3, P5–P8, P10), changelist (CL-25, CL-26), KiCad extraction audit (observations), investigation doc (Phases 12, 14, 20–25, "Firmware state", "Revert list"), `docs/debugging/i2c-oscilloscope-debugging.md`, the firmware at HEAD, and a Q&A with the user (§0).
>
> **Labels:** **[record]** = stated in the investigation doc; **[user]** = the user's recollection on 2026-10-18; **[code]** = read from the repo; **[own]** = this session's estimate or judgement, not externally sourced; **[verify]** = a fact to confirm on the instrument or from a datasheet before relying on it.

## 0. What the user told us (2026-10-18)

| Item | Answer |
|---|---|
| Scope | Rigol DHO804, firmware 00.01.05 (build 2026/01/20). Never connected to LAN. The user would like LAN control from the laptop. |
| Export today | USB stick in the front port; the scope's save function writes PNG (BMP/JPG also offered). The user hasn't found a CSV/WFM option, and the stick still holds some images from the April/May sessions. |
| Probes | Rigol stock probes, Sensepeek SQ-500 arms, and the SQ-10s that came with the PCBite kit. Whether ground springs are in the kit is unknown. |
| Phases 20–23 attenuation | "Pretty sure" SQ-500 switch was 10× and scope channel 10×. *Confident.* |
| Compensation | SQ-500 arms compensated on the Cal output when first used. *Confident.* |
| Ground | A wire was soldered to the GND test pad, and both probe grounds connected to it. *Confident.* Wire length was not recorded. |
| Bandwidth limit | Doesn't remember. |
| V_OL cursor technique (which feature, auto vs cursor) | Doesn't remember. |
| Anything changed between Phase 21 and Phase 23 | Doesn't remember. The user is new to scopes, so changes are possible. |
| Confidence | Low on the items flagged "doesn't remember". Confident on everything else. |
| Phase 25 | Doesn't remember whether it ran. |
| Firmware baseline | Believes it is still in the Phase 24/25 state; asked that it be double-checked (done in §2.5). |
| Boards | One working v6 (certain). One, possibly two, v7 boards believed undamaged. |
| Capture storage | Doesn't remember where (or whether) April/May captures were saved on the laptop. Leaning: captures in repo, but mostly gitignored, committing only the material ones. |
| Pain points | Holding probes (improved with practice). AI instructions were sometimes unclear. **Biggest: getting test images into the session and having the AI understand them.** |
| Scope limits on follow-up initiatives | None. |

---

## 1. Current state

How the scope workflow actually ran in Phases 20–25 (2026-04-29 → 2026-05-01):

- **Instrument:** a Rigol DHO804 arrived 2026-04-28. The scope guide (`docs/debugging/i2c-oscilloscope-debugging.md`) was written for a Hantek DSO5202P and then patched with DHO804 notes. Its step-by-step body is still Hantek-flavoured.
- **Probing:** Sensepeek PCBite with SQ-500 needle arms on BQ24195 (U5) pins 5/6, a 0.5 mm-pitch VQFN. Both grounds went to a soldered wire stub on a GND test pad. On v7 the only GND pad is TP4 (CL-26), so it was almost certainly TP4.
- **Measurement:** cursors set by eye. Results are typed into the investigation doc as prose plus a small table. No capture is cited by any phase.
- **Capture files:** none in the repo. The only scope image found on the laptop is `~/Downloads/scope_calibrate.jpg`, a **phone photo** of the screen taken 2026-04-28 with heavy glare. It shows CH1 on a 1 kHz square wave (period 1 ms at 200 µs/div, so the Cal output), and no phase references it. The user says the USB stick still has images from that period.
- **Run-to-record path:** the user ran the step, read numbers off the screen, and told the AI in chat. The AI wrote the phase entry. The firmware for the whole April–May investigation was **not committed until 2026-10-17** (`6400df9`, "WIP: v7 board firmware in-flight work"), so no phase is tied to a commit hash. **[code]**
- **Where it worked:** the non-scope phases (e.g. 12, 14) used live A/B/A toggles with pasted serial output and are the most auditable entries in the doc. **[record]**

---

## 2. Measurement-validity audit

### 2.1 Physics sanity reference **[own]**

To judge whether a reading is plausible, compare it with what a correctly driven bus should show. These are back-of-envelope figures. Topic 4 isn't proposing a mechanism here; it is asking whether the instrument can be believed.

- **Pull-up current while SDA is driven low:** R28 = 2.2 kΩ to 3.3 V gives ≈ 1.5 mA **[record]**, and the far-end 10 kΩ adds ≈ 0.33 mA, so ≈ 1.8–2 mA total.
- **ESP32-S3 output low:** the datasheet's I_OL spec is in the region of 28 mA at V_OL ≈ 0.5 V (max drive) **[verify against the ESP32-S3 datasheet]**. That implies a pull-down of roughly 15–40 Ω across the CAP_2/CAP_3 settings.
- **Expected V_OL at the master:** ≈ 2 mA × 15–40 Ω ≈ **30–80 mV**. The cable's extra 0.33 mA should add only **≈ 5–15 mV**. Ground-copper drop between the master and BQ at these currents is µV to low mV.
- **Bus spec:** UM10204 requires V_OL ≤ 0.4 V at 3 mA sink. Any healthy bus should read well under that.
- **CAP_2 → CAP_3:** at most about halves R_on, so it can change V_OL by about 2×, not by 13×. Phase 23 itself predicted ~2× (750 → 350 mV). **[record]**

### 2.2 Artefact sources and what each can do

| Source | Can it shift a DC low level by hundreds of mV? | Signature |
|---|---|---|
| **1×/10× mismatch** (probe vs scope setting) | Yes: everything scales by 10 (or 1/10). | Highs read 0.33 V or 33 V instead of 3.3 V. A decode with a 1.6 V threshold fails. |
| **Probe compensation error** | Partly. A misadjusted 10× probe produces a slow error after each edge (time constant ≈ ms). On a 5–10 µs low pulse this looks like a *near-constant offset* of a few % of the 3.3 V step, ≈ 50–150 mV for a visibly-bad comp. Not 600 mV unless grossly off. | Overshoot/rounding on the Cal square wave. |
| **Long ground lead / soldered stub** | Not a DC offset, but a loop that picks up magnetic fields. BQ24195 is a switching charger (≈ 1.5 MHz buck **[verify]**), and the probe point *is* the BQ. The pickup shows as a noise band riding on every level, so an eye-placed "floor/average/peak" spans the band. | Noise visible with the probe tip shorted to its own ground; ringing after edges. |
| **Bandwidth limit off** (default) | Widens the same noise band; doesn't move the mean. | Band narrows when BW limit = 20 MHz. |
| **Probe tip loading** (~10–15 pF per 10× passive probe **[verify SQ-500 spec]**) | No DC effect. Slows edges slightly. | Rise time changes when the probe is added/removed. |
| **Needle contact at 0.5 mm pitch** | Yes: a needle that slips onto a neighbouring pin measures a different signal entirely. The SQ-500 arms stayed on the board 2026-04-29 → 05-01 **[record]**. | Wrong decode; level patterns that don't match the bit sequence. |
| **Cursor technique** | Yes, for "average" read by eye in a noisy band, and depending on which feature (0-bit, ACK bit driven by the slave, spike on SCL edge) the cursor sits on. | Disagreement with the scope's automatic Vbase/Vlow. |
| **Channel-specific error** (CH1 vs CH2 setup) | Yes, if one channel's probe ratio, offset or probe differs. | Two signals with the same driver read very differently; swapping probes between channels moves the discrepancy. |

### 2.3 Per-result verdicts

#### Phase 20: SDA high level during the NACK window (2026-04-29)

- **Measured:** CH1 cursors at BQ pin 6. Idle high **3.29 V**, worst dip in the 9th-clock window **3.01 V** (−281 mV). Visual claims: wobble "identical in ACKed and NACKed transactions", rising edges "clean exponential". **[record]**
- **Setup recorded:** SQ-500 10×, needles on pins 5/6, shared soldered ground stub, I²C MissedAck trigger, decode showed `Write:D6 A:1`. **Not recorded:** V/div, BW limit, ground stub length, timebase. No capture saved.
- **Artefact assessment:**
  - The 3.29 V idle reading is the expected pull-up level, which rules out a ×10 attenuation error on CH1 *in this session*.
  - The decode working shows both needles were on SDA/SCL.
  - A noise band of even several hundred mV cannot close a 1.7 V gap to V_IH = 1.3 V.
- **Verdict: trustworthy (robust by margin)** for the conclusion "SDA does not fall below V_IH during the ACK window". The two visual-only claims (ACK/NACK identical, no kink) are **unknown**: there is no capture and no stated criterion.
- **Inherits:** PM §2 row 18 (Story D-revised refuted) stands. Upgrade its note from "strong *if the measurement is valid*" to "strong; margin exceeds any plausible probe artefact". The "no TCA pass-gate kink" remark stays visual-only.
- **To re-establish the visual claims:** save a deep-memory CSV of ≥ 10 transactions and overlay ACKed vs NACKed bytes. This is optional, because nothing currently rests on it.

#### Phase 21: SDA V_OL during 0-bits, cable out vs cable in (2026-04-30)

- **Measured:** CH1 cursors, three placements read by eye on a 0-bit:

  | Condition | Floor | Average | Peak |
  |---|---|---|---|
  | No cable | ~375 mV | ~650 mV | ~790 mV |
  | Cable | ~581 mV | ~750 mV | ~894 mV |

  SCL V_OL was also reported elevated, without numbers. **[record]**
- **Setup recorded:** "same Sensepeek setup as Phase 20". **Not recorded:** BW limit, V/div, which 0-bit or feature the cursors sat on, how "average" was determined, whether the probes had moved since Phase 20. No capture saved.
- **Artefact assessment:**
  1. **Magnitude:** 650 mV on a master-driven low is ~10× the §2.1 expectation and above the UM10204 0.4 V bus limit, on a bus where every device ACKed. That is the textbook "check the instrument" signal (expert-approaches P3), and the session fitted a parameter instead ("BQ effective V_IL ~800–900 mV").
  2. **Cable delta:** +100 mV from 0.33 mA implies ≈ 300 Ω of pull-down, again ~10× expectation.
  3. **Spread:** a ~400 mV floor-to-peak band on a level that should be DC-flat for microseconds is a noise-pickup signature (ground loop near a switching charger, BW limit off), not a driver property.
  4. **Both lines affected:** SCL was "also elevated", the common-mode pattern expected of a measurement artefact.
  5. The next session read the same feature 13× lower (Phase 23), and a drive-strength change cannot explain that ratio (§2.1).
- **Verdict: suspect.** Several independent red flags, no capture, and an unrecorded cursor technique. The record can't distinguish "noise band read by eye" from "attenuation/offset/contact problem" from "a real elevated level".
- **Inherits:**
  - PM row 19's Phase 21 "confirmed" (already marked invalid by the PM).
  - The "BQ effective V_IL ~800–900 mV" claim. **Withdraw it**; it must not enter the Stage B hypothesis map or assumptions register.
  - Phase 21's "cable adds ~100 mV" and "SCL also elevated".
  - Phase 21's re-reading of Phases 5–18 ("now perfectly explained").
  - Phase 22's operator note "same DC shift from cable as Phase 21".
- **To re-establish:** see §2.4, R1.

#### Phase 22: 50 kHz clock (2026-05-01)

- **Measured:** the result is the serial log (`BQ:X(2)` every iteration). The scope part is an operator impression ("clean and consistent, same DC shift") with no numbers. **[record]**
- **Verdict:** the **null result is trustworthy** because it comes from the firmware log, not the scope. The **scope remark is unknown** and not load-bearing. PM row 3 (clock speed, moderate) is unaffected.

#### Phase 23: SDA V_OL with CAP_3 drive, cable in (2026-05-01)

- **Measured:** SDA floor **~30 mV**, peak **~77 mV**, "~50 mV average". SCL V_OL **~290–350 mV** with the same driver setting. BQ still NACKs (serial log). **[record]**
- **Setup recorded:** "Sensepeek probes still on BQ pin 6". **Not recorded:** BW limit, V/div, cursor feature, SDA high level (so attenuation can't be checked from the record). No capture saved.
- **Artefact assessment:**
  - **For:** the SDA figure is what a correctly driven bus should read (§2.1). The noise band (~47 mV) is ~8× narrower than Phase 21's on the same probe point, so the setup or the cursor technique changed between sessions. The user can't recall what changed. **[user]**
  - **Against:**
    1. The **same session** shows SCL at 290–350 mV with the *same* driver setting and pull-up value, so one of the two channels is mis-reading, or the cursors were on different features. That is an unexplained internal inconsistency.
    2. The ratio to Phase 21 (650 → 50 mV, ≈ 13×) is close enough to 10 that a CH1 attenuation change between sessions **cannot be excluded from the record**, because no high level was recorded in Phase 23. The user's confident memory of 10×/10× argues against it.
- **Verdict: unknown, leaning plausible.** The SDA number is physically reasonable, but the session isn't internally consistent and has no capture.
- **Inherits:** PM row 19's "Ph 23 refutation = strong *if the measurement is valid*". Keep the conditional and change the strength label to **measured-refuted, pending R1** in the Stage B hypothesis map. The "~13× swing" between Phases 21 and 23 stays **unresolved**: at least one of the two sessions mis-read, or the setup changed.
- **To re-establish:** see §2.4, R1 (same procedure as Phase 21). No Phase 23 capture survives, so the attenuation question can only be settled by re-measuring.

#### Phase 24 (both entries): Arduino-as-master; glitch filter

Both conclusions rest on firmware/serial-log ACK/NACK results, not on the scope. **Outside this audit's scope.** The PM already notes Phase 24's multi-variable comparison (§4.5). No scope measurement inherits from or into them.

### 2.4 Re-establishment procedures (plans, not runs)

- **R0, salvage old captures: ruled out (user, 2026-10-18).** The USB stick has no images that can be tied to Phase 23 (or reliably to 20–22), and matching them by guesswork would be worse than nothing. The §2.3 verdicts are final as far as the record goes; **R1 carries the whole weight**. Leftover stick images are not evidence for any phase.
- **R1, re-measure SDA/SCL V_OL at BQ pins 5/6 on v7:**
  1. Run the §4.2 setup-validation checklist and the §4.3 known-good reference first.
  2. Declare the baseline: the firmware commit, with `Wire.setClock`, drive capability, filters and pulls stated explicitly (§2.5).
  3. Run A/B/A: cable out → cable in → cable out, live, same capture settings. Optionally repeat as a separate test with CAP_2 vs CAP_3 as the only variable.
  4. For each arm, save the PNG, the CSV (deep memory, scope stopped) and the setup file. Read V_OL with **both** cursors on the flat part of a master-driven 0-bit (not the ACK bit, not an edge spike) **and** the scope's automatic Vbase/Vlow, gated to that bit.
  5. Repeat at TPIO43/44, on the master side of the trace, under the same settings.
  6. Swap probes between CH1 and CH2 once, to catch a channel-specific error like Phase 23's SDA/SCL disagreement.
- **R2, the visual claims from Phase 20** (only if Stage B needs them): an overlay of ACKed vs NACKed transactions from a CSV.

### 2.5 Phase 25 and the firmware baseline

- **Phase 25 ran? Unknown.** The record ends "Pending: flash + observe… Result to be filled in." **[record]** The user doesn't remember. **[user]** No serial log, capture or later doc references a result.
  - The Experiment 2+3 code *is* present at HEAD (pad filter `FUN_FILTER_EN` on GPIO 43/44, `gpio_pullup_dis`/`gpio_pulldown_dis`), with a boot line `"I2C: 100 kHz, drive CAP_3, filter(7), pad-filter, internal pulls dis [Phase 24 null + Phase 25 bundle]"`. **[code]**
  - The code was written. Whether it was flashed and what it did can't be recovered. A search of the local Cursor chat store for the boot-line text and Phase 25 identifiers found nothing.
  - **Treat Phase 25 as "not tested".** If Experiments 2/3 still matter, they get a new test ID and run individually against a declared baseline.
- **Current firmware baseline (HEAD, `firmware/src/components/sensor/SensorManager.cpp:641-685`):** **[code]**

  | Change | Phase | In doc's "Firmware state"? | In "Revert list"? |
  |---|---|---|---|
  | `Wire.setClock(100000)` (was 400 kHz) | debug, Ph 22–23 | yes | yes |
  | `GPIO_DRIVE_CAP_3` on 43/44 | 23 | no | yes |
  | `i2c_filter_enable(I2C_NUM_0, 7)` | 24 Exp 1 | no | **no** |
  | IO_MUX `FUN_FILTER_EN` on 43/44 | 25 Exp 2 | no | **no** |
  | `gpio_pullup_dis` / `gpio_pulldown_dis` on 43/44 | 25 Exp 3 | no | **no** |
  | `STARTUP_I2C_SCAN=true` on `motion-play-v7` | early | yes | yes |
  | diag loop, `selectChannelVerify`, `DIAG_NO_WIFI`, envs `-diag`/`-busrec`/`-relbus` | 6+ | partly | yes (keep) |

  - **Conclusion:** HEAD is the accumulated Phase 25 stack. It is not a clean baseline and doesn't match `4da1c67` (CL-25).
  - The investigation doc's "Firmware state" and "Revert list" sections are **stale**: they omit three of the five I²C-init changes.
  - **Recommendation** (flagged; `docs/debugging/` is out of scope here): the first implementation initiative should define two named baselines as commits, `v7-clean` (HEAD minus the five I²C-init debug changes) and `v6-ref` (`4da1c67`). Every test card then cites one of them plus a single declared delta.

### 2.6 Audit summary

| Result | Verdict | Load-bearing for | Action |
|---|---|---|---|
| Ph 20 V_IH margin (3.01 V vs 1.3 V) | **trustworthy** (by margin) | D-revised refuted | none required |
| Ph 20 visual ACK/NACK identical, no kink | unknown | nothing current | R2 if needed |
| Ph 21 V_OL ~650/750 mV, cable +100 mV | **suspect** | G-revised "confirmed" (already invalid), "effective V_IL 800–900 mV" | withdraw fitted V_IL; R1 |
| Ph 22 scope remark | unknown | nothing (null result is log-based) | none |
| Ph 23 V_OL ~50 mV (SDA) | **unknown, leaning plausible** | G-revised refuted | R1; label "pending R1" |
| Ph 23 SCL V_OL ~300 mV | **suspect** (inconsistent with SDA, same driver) | nothing | R1 channel swap |
| Phase 25 | **not tested** | nothing | re-run individually if still relevant |
| Firmware baseline | **HEAD = stacked Ph 23–25 changes** | every future test | define `v7-clean` / `v6-ref` |

---

## 3. Friction points observed

1. **Image handoff is the bottleneck** (the user's top pain). Captures went to a USB stick and never reached the repo or a chat in a durable form. The only image recovered is an unreferenced, glare-covered phone photo (`~/Downloads/scope_calibrate.jpg`). Several key cursor values exist only as numbers typed into prose. **[user] [record]**
2. **No capture is cited by any scope phase** (20–23), so none can be re-audited (PM §4.7). **[record]**
3. **Setup metadata missing:** BW limit, V/div, ground stub length, cursor feature and timebase are absent from every scope phase. "Same setup as Phase 20" was the only setup statement in Phases 21–23, and Phase 23's readings suggest it wasn't the same. **[record]**
4. **No firmware commit per test:** the whole April–May firmware state was committed in one WIP commit on 2026-10-17. **[code]**
5. **Board ID dropped:** Phases 12/14 name "Board 3"; Phases 20–23 name no board. With 1–2 surviving v7s that matters. **[record] [user]**
6. **Phase IDs not stable:** two Phase 24s; the solder-plan "Phase 19" collides with the investigation's Phase 19 (PM §4.6). Phase 25 remains "in progress" five months on. **[record]**
7. **The scope guide is a hybrid and misleads in places:** **[record]**
   - Hantek button walkthroughs sit under DHO804 notes.
   - §1.5 calls probe compensation "optional".
   - It gives ground as "any nearby GND test pad" with no length guidance.
   - It names the `busrec` env, while the phases used `diag`.
   - Its outcome table pre-interprets results for Story D-revised (PM §4.6).
8. **Operator impressions recorded as findings:** "identical in ACKed and NACKed", "clean and consistent", "same DC shift", with no capture or criterion. **[record]**
9. **Eye-averaged readings:** "average" V_OL was a cursor placed by eye in a ~400 mV band; the scope's automatic, histogram-based measurement was not used. **[record]**
10. **Unclear AI instructions:** instructions were improvised in chat. The user had to translate them into physical steps, and the AI's expectation leaked into what was asked for. **[user]**
11. **Needle probes on 0.5 mm pitch left in place across days**, with no per-session contact check (the decode is a free one). **[record]**
12. **Strengths to keep:** A/B/A live toggles with raw serial pasted verbatim (Phases 12, 14); Phase 23 wrote a numeric prediction before running. **[record]**

---

## 4. Proposals

### 4.1 Scope model and its quirks

- **Model:** Rigol DHO804, 4 ch, 70 MHz, 12-bit, 1.25 GSa/s, firmware 00.01.05. Inputs 1 MΩ ∥ 15 pF, 300 V RMS CAT I (from the front panel in the 2026-04-28 photo).
- **Probes in hand:**

  | Probe | Use | Note |
  |---|---|---|
  | Rigol stock probes | known-good references, Cal checks | |
  | Sensepeek SQ-500 | hands-free at fine pitch | **[verify]** model bandwidth and tip capacitance from the Sensepeek spec |
  | SQ-10 | likely 1× / low-bandwidth arms | **[verify]**. Not for edge or V_OL work unless confirmed 10×. |

  Look in the stock-probe accessory bags for **ground springs**. If none, buy a pair matched to the probe tip diameter.
- **Export:**
  - Today: PNG to USB.
  - CSV: should be under Storage/Save with file type "Waveform/Trace" **[verify on 00.01.05]**.
  - Also save the **setup file** (Storage → Setup **[verify]**) with every capture. It records every channel/trigger setting, which answers most of §2's "not recorded" items automatically.
  - Turn on the measurement and cursor readout panels before saving, so the numbers are burned into the PNG and an AI session can read them.
  - **Never phone-photograph the screen** (glare, perspective, unreadable small text).
- **Clock:** set the scope's date/time correctly. File timestamps are how ingest matches files to tests; R0 failed partly because old files couldn't be tied to phases.
- **Remote control (tooling opportunity):** DHO800-series scopes support SCPI over LAN (VXI-11/LXI, raw socket) and USB-TMC, per third-party tool support. Typical queries are `:DISPlay:DATA?` (screenshot) and `:WAVeform:DATA?` (samples). **[verify** exact syntax against Rigol's *DHO800/DHO900 Programming Guide*; a third-party DHO800 LAN control/MCP project exists but is unverified on hardware**]**.
  - The user wants this.
  - **Recommendation:** connect the scope to LAN in the first implementation initiative and build the §5 capture tool. It removes the USB-stick step entirely and records setup metadata by querying the scope.
- **Trigger quirks seen:** I²C MissedAck trigger and decode worked (Phase 20). Keep the decode threshold at ~1.65 V (V_DD/2), and keep decode on during V_OL work as the per-session needle-contact check.

### 4.2 Setup-validation procedure (every scope session, before any v7 number is trusted)

Run it, then record the result in the log as `validation` (§4.6). **If any step fails: stop and investigate the setup. Never adjust an interpretation, threshold or "effective" parameter to fit.**

| # | Step | Pass criterion |
|---|---|---|
| V1 | Scope date/time correct; load the saved setup file for this test type (or record defaults). | Clock within 1 min. |
| V2 | For each probe in use: confirm the probe switch position and the scope channel's Probe Ratio. | Both say 10× (or both 1×), written down per channel. |
| V3 | Compensate each probe **on the channel it will be used on**, using the Cal output, at ~200 µs/div. | Flat top, square corners, no overshoot or rounding visible at 1 V/div. Save a PNG. |
| V4 | Cal amplitude check: Vamp/Vtop on the Cal square wave. | Matches the Cal output's nominal amplitude **[verify the DHO804 Cal spec]** within ±3%. |
| V5 | **Shorted-tip noise floor:** on the powered DUT, connect probe tip and ground to the *same* ground point (TP4 on v7), at the V/div and BW-limit settings the measurement will use. | Vpp of the floor ≤ 20 mV **[own]**. If larger, the ground method is too long or loops near the charger; fix it before measuring tens-of-mV features. Save a PNG. |
| V6 | Ground method: the shortest available. On v7 this means a ground spring or ≤ 10 mm wire to TP4 **[own]**, or a closer GND-net pad if one is identified (§5). Record type and length. | Recorded. |
| V7 | Known-good level check on the DUT: the idle-high of SDA and SCL. | 3.3 V ± 5% on every channel in use. This catches ×10 errors; it's the check Phase 23 lacked. |
| V8 | Contact check for needle probes: decode on, address byte shows the expected value (e.g. `D6`). | Decode matches. Repeat after any bump or reseat, and at the start of every day. |
| V9 | Reference measurement (§4.3), at least at the start of a campaign and whenever probes, ground method or scope settings change. | Within spec. |

### 4.3 Known-good reference procedure

Purpose: prove the probe/ground/scope chain reads a healthy I²C bus as healthy, using the *same* probes, ground method and settings planned for v7 (P3; PM §6.8).

- **Reference DUT:** the surviving v6 board running **`4da1c67` firmware** (CL-25; HEAD firmware differs in shared I²C init code).
  - v6 still has TP_GND1 and +3.3 V/+5 V test pads; v7 has only TP4 for GND and no +3.3 V pad (CL-26). Use the *same ground length* on both boards, not "whatever pad is closest", or the comparison is uneven.
  - Pin/test-point names on v6 come from the v6 KiCad source; extract them before the session, not from memory.
- **Secondary reference (optional):** a bench I²C bus such as the Arduino Nano 33 IoT plus any breakout, at 100 kHz.
- **Signals and points:** SDA and SCL at the master (TPIO43/44 or v6 equivalent) and at the BQ24195 pins 5/6 (v6 also carries a BQ24195).
- **What to capture:** one address transaction to BQ, deep memory, PNG + CSV + setup file. Measure with automatic Vbase/Vlow/Vtop, gated to a master-driven 0-bit, plus cursor confirmation, and measure rise time 30%→70%.
- **"Matches spec" (UM10204, V_DD = 3.3 V):**

  | Quantity | Pass | Note |
  |---|---|---|
  | V_OL (master-driven 0-bit) | ≤ 0.4 V (spec); expect ≈ 30–80 mV **[own, §2.1]** | > 0.2 V on a working bus = investigate the setup |
  | V_IL threshold reference | 0.3 V_DD = 0.99 V | for context, not measured |
  | V_IH threshold reference | 0.7 V_DD = 2.31 V | for context |
  | Idle high | 3.3 V ± 5% | |
  | Rise time 30%→70% | ≤ 1000 ns at 100 kHz; ≤ 300 ns at 400 kHz (`4da1c67` runs 400 kHz) | |
  | Decode | expected address + ACK | |

- **Outcome rule:** if the v6 reference fails these numbers with a validated setup, the setup or the expectation is wrong. Resolve that before any v7 measurement is recorded.

### 4.4 Filename convention

```
YYYY-MM-DD_<test-id>_<arm>_<nn>.<ext>
e.g.  2026-11-04_V7R-012_A1_01.png
      2026-11-04_V7R-012_A1_01.csv
      2026-11-04_V7R-012_A1_01.stp     (scope setup file; extension per DHO804 [verify])
      2026-11-04_V7R-012_val_V5_01.png (setup-validation capture)
```

- `<test-id>` is the stable, never-reused ID from the test card (§4.7).
- `<arm>`: `A1` / `B` / `A2` for A/B/A arms, `S1`, `S2`… for plain procedure steps, or `val` for validation.
- `<nn>`: a sequence number.
- **Channel→signal mapping lives in the log entry, not the filename.** This refines the relay's starting point: one screenshot usually shows two to four channels, and duplicating the map in the name invites drift. The filename is a unique key into the log; the log says CH1 = SDA@U5.6, and so on.
- The scope writes its own default names. Renaming happens at ingest (§4.5 / §5), never on the scope.

### 4.5 Capture location

The user asked for a view: **mostly gitignored, commit only what a conclusion rests on.** Proposed:

```
lab/
├── inbox/                  # gitignored. Raw dump from USB stick or SCPI tool, scope's own names
├── captures/<test-id>/     # gitignored. Renamed per §4.4, every capture of the test
└── evidence/<test-id>/     # COMMITTED. Only captures cited in a card's result/conclusion,
                            #   plus the setup file and CSV for them (CSV decimated if > 1 MB)
```

- **Committed:** PNGs average ~100 KB, so a few per test is fine. Full deep-memory CSVs can be tens of MB, so commit them only when a conclusion depends on the samples, decimated or trimmed to the region of interest.
- **Rule:** a card's conclusion may cite only files under `evidence/`. Promoting a file is part of recording the result, done in the same commit (PM §6.20).
- **Backup** for gitignored `captures/`: the repo is on one MacBook. Add a periodic copy to cloud storage (user's choice of service). Keep the USB stick as a second copy until a capture is ingested.
- **Location in the repo** (`lab/` at root vs under `docs/research/` or an initiative folder) is **topic 6's call**, since it governs how sessions load these. Topic 4 fixes only the inbox / captures / evidence split and the promotion rule.

### 4.6 Measurement log format (YAML)

One YAML document per scope session. The setup block is written once and referenced by each measurement.

```yaml
# lab/log/2026-11-04_session-01.yaml
session_id: 2026-11-04_s01
operator: user
ai_session: <claude session id or relay name>
dut:
  board_id: v7-B3            # physical label on the board; see card
  firmware_commit: 1a2b3c4   # exact build flashed
  firmware_env: motion-play-v7-diag
  declared_baseline: v7-clean
scope:
  model: Rigol DHO804
  firmware: 00.01.05
  setup_file: 2026-11-04_V7R-012_A1_01.stp
validation:                  # §4.2; every item required
  passed: true
  V2_probe_ratio: {CH1: 10x/10x, CH2: 10x/10x}
  V3_comp_png: 2026-11-04_V7R-012_val_V3_01.png
  V5_noise_floor_mVpp: 12
  V6_ground: {method: spring, point: TP4, length_mm: 8}
  V7_idle_high_V: {CH1: 3.29, CH2: 3.30}
  V8_decode_ok: true
  notes: ""
channels:
  CH1: {probe: SQ-500 #1, ratio: 10x, signal: SDA, point: U5.6, bw_limit: 20MHz, v_div: 200mV, offset_V: -0.6, coupling: DC}
  CH2: {probe: SQ-500 #2, ratio: 10x, signal: SCL, point: U5.5, bw_limit: 20MHz, v_div: 1V, offset_V: 0, coupling: DC}
measurements:
  - test_id: V7R-012
    arm: A1
    time: "2026-11-04T10:42"
    trigger: {type: I2C, condition: address, value: 0x6B, source: CH2}
    timebase: 5us/div
    method: auto            # auto | cursor | both
    feature: "SDA, master-driven 0-bit #3 of addr byte (bit 0), flat region"
    values:
      - {name: Vbase, ch: CH1, value_mV: 48, gate: "t=+12..+18us"}
      - {name: cursor_Y, ch: CH1, value_mV: 51, cursor: "Y1 on flat region"}
    captures: [2026-11-04_V7R-012_A1_01.png, 2026-11-04_V7R-012_A1_01.csv]
    raw_observation: "BQ:X(2) every iteration; decode shows D6 N"
```

Required fields, rejected by a validator if missing: `dut.*`, `validation.passed` + `V2`/`V5`/`V6`/`V7`, every channel's `ratio`/`bw_limit`/`signal`/`point`, and per measurement `test_id`/`method`/`feature`/`values`/`captures`. Fields are snake_case. Units are in the key name (`_mV`, `_V`, `_mm`), so no session has to parse units out of strings.

### 4.7 Test card template

Topic 4 owns the card format; topic 6 decides where cards live and how they're loaded. One Markdown file per test, with a YAML header (machine-readable) and a body that follows Zeller's columns. **Everything above the `--- RUN ---` line is written and committed before the test runs.**

````markdown
---
test_id: V7R-012              # allocated from a counter; never reused, never renumbered
title: SDA V_OL at U5.6, cable out/in/out, v7-clean
status: pre-registered        # pre-registered | run | recorded | abandoned
created: 2026-11-04
prereg_commit:                # hash of the commit that added this card (filled by the commit)
baseline:
  name: v7-clean              # v7-clean | v6-ref | other (describe)
  firmware_commit: 1a2b3c4
  firmware_env: motion-play-v7-diag
  board_id: v7-B3
  hardware_config: "J6: failing-config cable (10k SDA→3V3 far end, SCL dangling). No other mods."
variable_changed: "J6 cable present vs absent"   # exactly one
structure: A/B/A              # A/B/A | A/B | single (justify)
revert_on_null: n/a           # yes | no (justify) | n/a (no firmware/hardware change)
---

# V7R-012 — <title>

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | ... | hypothesis map / card V7R-0xx |
| H2 | ... | |
| M  | Measurement artefact (always listed) | §4.2 |

## Predictions and exclusions (written before the run)
| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| V_OL(B) − V_OL(A) < 20 mV | H1 | H2 |
| V_OL(B) − V_OL(A) ≥ 20 mV and A2 ≈ A1 ± 10 mV | H2 | H1 |
| A2 ≠ A1 by > 10 mV | — (drift: result void, investigate) | M |

## Setup
- Measurement log: `lab/log/2026-11-04_session-01.yaml`. Validation must read `passed: true` before step 1.
- Channels, probes, points: per log `channels`.

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S1 | ... | ... | ... |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
### Measured values (from log; cite `lab/evidence/V7R-012/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: yes/no (commit)
- Result commit: <hash>
````

Rules:
- `test_id` uses the form `V7R-NNN`, allocated monotonically. Abandoned tests keep their ID with `status: abandoned`.
- Exactly one `variable_changed`.
- The prediction table has numeric thresholds and covers every outcome, including "void".
- `M` (measurement artefact) is always a listed hypothesis.

### 4.8 How the user receives instructions

Each physical step the AI hands the user uses this block. The AI sends **one step (or one short group) at a time** and waits for the report.

```
STEP S3 of 7 — V7R-012 arm B (cable in)
DO:      Plug the failing-config cable into J6. Do not touch the probe arms.
CHECK:   Serial shows the diagnostic loop still iterating.   ← instrument/setup expectations only
         Decode still shows D6 on screen.
CAPTURE: Press STOP, then Save (PNG + CSV + setup). Note the file names the scope shows.
REPORT:  1. Serial: paste the last 3 iterations verbatim
         2. Scope: Vbase CH1 = ___ mV, Vbase CH2 = ___ mV (from the measurement panel)
         3. File names saved: ___
         4. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: decode no longer shows D6, or anything smells/gets hot → report and wait.
```

- **CHECK lists only setup and instrument expectations,** never the expected measurement outcome. The prediction lives in the card and is not shown to the operator during the run (P10, Raymond: "symptoms, not guesses").
- The REPORT fields are pre-numbered blanks, so the user transcribes rather than interprets.
- One physical action per step where the board is powered.

### 4.9 Image handoff

The user's biggest pain point. Proposed flow:

- **Interim (USB, no tooling):**
  1. After each step, the user reports the file names the scope displayed (REPORT field 3).
  2. At the end of an arm, or at least before the session ends, the user plugs the stick into the Mac.
  3. The AI session copies the stick into `lab/inbox/`, renames per §4.4 into `lab/captures/<test-id>/`, and opens each PNG with its image reader.
  4. For each image the AI writes, *in the log*: what it reads from the on-screen labels (V/div, probe ratio if shown, measurement panel values, cursor values) and any mismatch with what the user reported.
  - Mismatch between the user's numbers and the image is a stop condition.
  - Burned-in measurement panels (§4.1) are what make step 4 reliable; the AI should not estimate voltages from trace position when a number is available.
- **Target (after the §5 tool):** the session calls the capture tool, which pulls the PNG, CSV and full settings straight into `lab/captures/<test-id>/` with the metadata already filled into the log.
- **Never:** phone photos, screenshots pasted only into chat (lost when the session ends), or numbers reported without a file.

---

## 5. Tooling opportunities (flag only; not built)

1. **SCPI capture CLI** (highest value; the user wants it). `capture --test V7R-012 --arm A1`:
   - pulls the screenshot, waveform CSV and setup over LAN;
   - queries per-channel probe ratio, BW limit, V/div, offset, timebase, trigger and active measurements;
   - names files per §4.4 and appends a pre-filled measurement entry to the session log.

   This removes the USB step and most "not recorded" gaps. Validate it against a USB-saved capture once.
2. **Validation helper:** a scripted §4.2 run (Cal amplitude, noise floor, idle-high checks) that writes the `validation` block.
3. **Test-card scaffolder:** allocates the next `V7R-NNN`, creates the card from §4.7 and commits it as pre-registered.
4. **Log/card validator:** checks required fields, that a card's `prereg_commit` predates its result commit, and that cited evidence files exist.
5. **USB ingest script** (interim): copy, timestamp-match and rename stick contents.
6. **Nearest-GND finder:** query the v7 KiCad PCB for GND-net pads (capacitor terminals, vias) closest to U5 pins 5/6. TP4 is ~12 mm from U5 centre-to-centre **[code, KiCad positions]**, which forces a long ground lead. A closer pad might give a shorter ground for V5/V6.
7. **Third-party option:** an existing DHO800 LAN/MCP project could let a session drive the scope directly. Unverified on hardware; evaluate before building item 1.

---

## 6. Does this spawn an implementation initiative?

**Yes: one initiative, suggested name `test-workflow-setup`.** It is a precondition for any new v7 bench measurement: until it lands, no v7 scope number can be trusted or audited (§2–§3). How to phase it is the Planner's call; §6.1 gives the inputs.

**The re-measurement (R1) is not part of it.** R1 is v7 debugging and needs the Stage B hypothesis map. The recommendation is that R1 become the first test cards of the Stage B debugging initiative, followed by the Phase 25 experiments only if still relevant, one per card. `decisioning.md` confirms this.

### 6.1 Input for the Planner

This section is not a PLAN. It lists what the Planner needs to settle when writing BRIEF, PLAN and TASKS.

**Goal.** Before any new v7 measurement is recorded, the bench produces captures that are validated, self-describing, filed by test ID, and readable by an AI session without manual transcription.

**In scope:**
- Two declared firmware baselines: `v7-clean` (HEAD minus the five I²C-init debug changes, §2.5) and `v6-ref` (`4da1c67`, CL-25).
- Scope on the LAN, with SCPI confirmed on firmware 00.01.05, including every §4.1 [verify] item (CSV save, setup-file save, screenshot and waveform queries, per-channel probe-ratio and BW-limit queries).
- The SCPI capture tool (§5 item 1), plus the USB ingest script (§5 item 5) as a fallback.
- Templates and layout as files: test card (§4.7), measurement log (§4.6), instruction/report block (§4.8), `lab/` capture split and `.gitignore` (§4.5), `V7R-NNN` counter.
- A DHO804-only bench procedure containing §4.2 setup validation and §4.3 known-good reference, replacing `docs/debugging/i2c-oscilloscope-debugging.md`.
- Identifying the GND pad closest to U5 (§5 item 6), and ground springs on hand.
- An acceptance dry run of §4.2 + §4.3 on the v6 board, using the new card, log, tool and instruction format end to end.

**Optional, Planner's judgement:** card scaffolder, log/card validator, validation helper (§5 items 2–4); evaluating the third-party DHO800 LAN/MCP project (§5 item 7) before building the capture tool.

**Out of scope:** any v7 measurement, R1/R2, any hypothesis work about the v7 fault, firmware changes beyond defining the two baselines.

**Acceptance criteria to carry into the PLAN:**

| Check | Pass |
|---|---|
| Baselines | Both `v7-clean` and `v6-ref` build; each one's I²C init is stated in its commit message. |
| LAN capture | A screenshot and CSV pulled over LAN match the same capture saved to USB. |
| Capture tool | One command yields files named per §4.4 and a log entry with every required §4.6 field filled from the scope's own settings. |
| Templates | A dummy card can be created, pre-registered and committed end to end. |
| Dry run | v6 on `v6-ref` reads within §4.3 spec (V_OL ≤ 0.4 V, expected ≈ 30–80 mV; idle high 3.3 V ± 5%; rise time 30→70% ≤ 300 ns at 400 kHz), and the user confirms the image handoff was workable. A v6 failure means the setup is fixed before the initiative closes. |

**Dependencies and constraints.**
- Topic 6 decides where `lab/` lives and how cards and logs are loaded. The Planner should either wait for topic 6 or leave the location as a single config value.
- The ESP32-S3 V_OL datasheet figure behind §2.1 must be checked before the §4.3 "expected ≈ 30–80 mV" goes into a procedure.
- The dry run needs the user at the bench; the Orchestrator can't verify it alone.

**Decisions for you (the user)**, to answer at Planner kickoff:
1. Launch before topic 6 and Stage B decisioning, or let `decisioning.md` sequence it?
2. Cloud backup for gitignored captures: which service, if any?
3. The capture tool: build our own, or adopt the third-party DHO800 project if it checks out?
4. Does the old scope guide get deleted, or archived with a pointer to the new procedure?

### 6.2 Draft relay for the Planner

This is a draft. Answer the decisions in §6.1 first and edit them into "Open questions", or leave them for the Planner to ask you. To launch: save the block below as `docs/initiatives/test-workflow-setup/RELAY-planner.md`, then start a session with `--agent planner`. The initiative name is a suggestion.

````markdown
# Relay — research → planner — <date>

role:planner

## Context
Topic 4 of the v7-retry research (`docs/research/v7-retry/test-workflow-audit.md`) audited past oscilloscope work on the v7 I²C fault and the bench workflow around it. Key scope readings (Phase 21, Phase 23) can't be trusted or re-audited: no setup validation, no setup metadata, no saved captures, no firmware commit per test. Getting images into AI sessions was the user's biggest pain. This initiative builds the bench workflow that every future v7 measurement depends on.

## Load these files
- .context/PROTOCOL.md
- docs/research/v7-retry/test-workflow-audit.md — **the source of truth for scope**. Read §3, §4, §5 and §6 in full; §6.1 is the planner input. §2.5 defines the firmware baselines.
- docs/research/v7-retry/v6-v7-changelist.md — CL-25 (v6 firmware `4da1c67`) and CL-26 (v7 test points: TP4 = GND only)
- docs/debugging/i2c-oscilloscope-debugging.md — the guide being replaced (skim)
- firmware/src/components/sensor/SensorManager.cpp:641-685 and platformio.ini (v7 envs) — what `v7-clean` must strip
- docs/research/v7-retry/context-strategy.md, if topic 6 is complete — where `lab/` lives

## State
Branch: n/a (the Orchestrator cuts `feat/test-workflow-setup` from main at run time)
Build: n/a at kickoff; the firmware builds at HEAD
TASKS.md current: n/a — not yet written
Initiative folder `docs/initiatives/test-workflow-setup/` holds only this relay.

## What was done
- Audited Phases 20–23: Phase 20 trustworthy (by margin); Phase 21 suspect; Phase 23 unknown, leaning plausible. No old captures can be tied to phases, so re-measurement is the only route (and is out of scope here).
- Found Phase 25 unrecorded (treated as not tested) and HEAD firmware carrying five stacked I²C debug changes, three missing from the investigation doc's revert list.
- Proposed concrete formats: setup-validation checklist (§4.2), known-good reference on v6 (§4.3), filenames (§4.4), capture layout (§4.5), YAML log (§4.6), test card (§4.7), instruction block (§4.8), image handoff (§4.9).
- Scope: Rigol DHO804, firmware 00.01.05, never networked; the user wants LAN control.

## Your task
Write BRIEF.md, PLAN.md and TASKS.md in `docs/initiatives/test-workflow-setup/`, using audit §4–§5 (what to build) and §6.1 (scope, acceptance criteria, dependencies).

- Carry the §6.1 acceptance table into the PLAN.
- Instrument facts marked [verify] in the audit must be confirmed on the scope before anything is built on them.
- Steps the user performs at the bench must use the §4.8 instruction format, and the PLAN must show where the Orchestrator waits for the user.
- Keep each phase Worker-session-sized; split with a `🔄 Handoff` if not.

This initiative builds workflow and tooling only. It must not take v7 measurements or form conclusions about the v7 I²C fault; that is Stage B's job.

## Open questions
1. Launch before topic 6 and Stage B decisioning, or let `decisioning.md` sequence it?
2. Cloud backup for gitignored captures: which service, if any?
3. Build our own capture tool, or adopt the third-party DHO800 project if it checks out?
4. Delete the old scope guide, or archive it with a pointer?
5. Where `lab/` lives, if topic 6 hasn't decided.
````

---

## Observations for other topics

- **Topic 6 (context strategy):**
  - Topic 4 defines the card (§4.7), log (§4.6) and capture split (§4.5); topic 6 decides where `lab/` lives and what a session loads by default.
  - Suggested for the current-state file: the audit summary table (§2.6) and the declared baselines.
  - The `V7R-NNN` counter needs a single home.
- **Stage B / synthesis:**
  - Withdraw "BQ effective V_IL ~800–900 mV" from all reasoning.
  - Story G-revised's refutation is "measured-refuted, pending R1".
  - The Phase 21→23 13× swing is unresolved and is a measurement question before it is a circuit question.
  - Phase 25 = not tested.
  - HEAD firmware is the stacked Phase 23–25 build.
- **Housekeeping (flagged; `docs/debugging/` not edited here):**
  - The investigation doc's "Firmware state" and "Revert list" omit three I²C-init changes (§2.5).
  - Phase 21 should carry a note pointing at this audit.
  - The scope guide should be retired or rewritten (§3 item 7).
