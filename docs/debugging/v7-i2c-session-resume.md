
This is a handoff from a previous sessio where we have been debugging a specific, reproducible fault on a custom PCB across several days and multiple sessions. This prompt resumes that work with full continuity. We are not starting over — read the documentation and pick up where the previous session stopped.

---

## Read these files, in this order, before responding

1. `docs/debugging/v7-i2c-investigation.md` — **primary**. Full history, facts, ruled-out theories, firmware state, board status, candidate fixes. The top section "Fastest possible read (start here if you're a new session)" is deliberately designed for exactly this — read it first, then scan the Phase 1–18 timeline (focus on Phases 11–18 for the most recent narrowing of the option space), then skim the rest. The "Current working theory" section reflects the post-Phase-18 framing of Stories D-revised, E (downgraded), and F (still tracked).
2. `docs/debugging/v7-i2c-fresh-perspective-prompt.md` — a sibling handoff document from before Phase 17, aimed at inviting a different perspective. The framing-challenge it offered was useful and led to Phase 17, so its specific suggestions are now mostly absorbed into the investigation doc. Read so you don't duplicate its content; don't treat it as still-active suggestions.
3. `docs/debugging/i2c-oscilloscope-debugging.md` — procedure for scoping the I2C bus. Updated post-Phase-17: the primary scope target is now the BQ-pad capture (looking for SCL-correlated SDA wobble below V_IH = 1.3 V during the 9th-clock ACK window), not the legacy VCNL-pad capture. Phase 18 reinforces the framing — the capture is taken while TCA2 is open with the failing cable connected, since the disturbance is live/ongoing rather than a transient at plug-in. New scope arriving week of 2026-04-28.
4. `.context/PROJECT.md` — project overview. Useful for context but this investigation is narrow enough you may not need it.

---

## What we're working on right now

We're debugging a reproducible fault on the v7 main PCB: **the BQ24195 at I2C address 0x6B stops ACKing its address whenever a TCA9548A channel opens with a DC-terminated cable pulled toward +3.3 V on SDA at the far end**. All observational work through Phase 18 is done — it's a 100% deterministic, live-state symptom. The mechanism is not yet definitively identified, but as of Phase 18 the option space is narrow and the only remaining cheap pre-scope discriminator is the Arduino-as-master test.

Through Phases 1–18 (see investigation doc) we've ruled out: sensor-side defects, power brownout, I2C speed, pullup strength (swept 4.7 kΩ to 47 kΩ with zero variation), RF coupling (tested radios-off), per-channel routing differences, bus physics from cable length alone, several firmware-level causes, rail-perturbation through cable loop (Phase 11), SCL involvement (Phase 12 — fault is SDA-only), polarity-symmetric mechanisms (Phase 13 — fault is +3.3 V-polarity-only on SDA), 3.3 V rail noise injection (Phase 14 — clean PSU triggers identically), stuck-state-machine recoverable in software (Phase 15 — disturbance is steady-state, not state-machine-driven), routing-asymmetry-EMI (Phase 16 — SDA and SCL are routing-symmetric, SCL is in fact more exposed to switchers), the original ESD-diode-mediated framing of Story D (Phase 17 — BQ's SDA pin is rated abs max +7 V with no conventional upper clamp at +3.3 V; the diode the original story relied on doesn't exist where the story needed it), and **any USB-C / VBUS-mediated story (Phase 18 — bench PSU on BAT_RAW with USB-C VBUS absent reproduces the fault identically)**. Phase 18 also confirmed via the per-row recovery pattern that the failure is **live / ongoing while the cable is connected**, not a latched event from plug-in: BQ recovers spontaneously between TCA2 selections within a single diagnostic-loop iteration with no software intervention. Three boards tested; Board 1 damaged by a failed bodge attempt (Phase 7), Board 2 has an unrelated assembly defect (Phase 8 — BQ dead at boot), **Board 3 is healthy and is the investigation target**.

The dominant surviving hypothesis is **Story D-revised — SDA input-stage noise-margin failure at BQ**: with the cable-extended pullup attached, BQ's SDA pin sees added parasitic C from the cable + connector and capacitive crosstalk from SCL on the parallel-routed pair, which together can drag SDA at BQ's pad below V_IH = 1.3 V momentarily during the 9th-clock ACK window, causing BQ's CMOS receiver to mis-classify and NACK. Phase 18's live/ongoing observation tightens the framing — the disturbance is the steady-state crosstalk + parasitic-loading regime, not a one-shot event at the moment of plug-in. **Story F — ESP32-S3 I2C peripheral interaction** is still tracked, pending the Arduino-as-master discrimination test (which is the only thing that distinguishes Story F from Story D-revised). **Story E** (cable-mediated mechanism not captured by D-revised) is downgraded — the 2.5 cm horizontal cable geometry the operator has been testing with rules out the EMI-antenna framing.

## Where we stopped last session

The previous session ran Phase 18 (bench-PSU-from-battery-pads test) — second item on the priority list at the time. Setup: bench PSU at ~3.7 V on temp leads soldered to BAT_RAW + GND test pad, USB-C kept connected only as a data-only cable for serial (VBUS conductor severed), failing-config cable (10 kΩ from cable's SDA wire to its VCC wire) in J6, firmware on `motion-play-v7-busrec` env.

Result: 7 baseline iterations clean (no cable in J6), then the cable was plugged into J6 and 14 subsequent iterations all show `BQ:X(2)` on the TCA2 row only — identical to every USB-C-powered run. Phase 18:

- **Ruled out USB-C / VBUS state as a contributor.** The fault reproduces identically with VBUS absent. Closes the BQ USB input state machine, VBUS-dependent supply noise, USB-host-noise-via-cable-shield, and similar framings.
- **Confirmed the failure is live / ongoing, not latched.** BQ ACKs on BASE / TCA0 / TCA1 rows even after the cable has been in J6 for many iterations, then NACKs only on TCA2 rows; recovery between TCA2 selections is spontaneous (no software intervention). Rules out any "transient at plug-in" framing. Doubly closes Story A residuals (no stuck state to recover from).
- **Strengthened Story D-revised** by removing a class of confounds and tightening the framing to "ongoing crosstalk + parasitic loading while the cable is electrically connected" rather than "event at insertion."
- **Did not differentially affect Story F.** Story F was not VBUS-dependent in any of its formulations — the Arduino-as-master test is still required to discriminate it from Story D-revised.
- **Removed bench-PSU from the priority list.** It was item 2; with it complete, the Arduino-as-master test is now the uncontested top of the queue.

**Tests queued up (post-Phase-18, in priority order):**

1. **Arduino-as-master probe of BQ in failing config** — the only remaining cheap pre-scope discriminator. Discriminates Story D-revised from Story F. Blocked on a small firmware change: a `DIAG_RELEASE_I2C` build flag that boots normally through `configureBQ24195()`, then calls `Wire.end()` and reconfigures GPIO 43/44 to `INPUT` (no internal pullup), then sits in a tight print loop. ESP32 stays alive but the bus is electrically free for an external master. No reset-button hold required.
2. **Phase 11 current measurement with DMM in-line** — verify the rail-load-only test was actually loading the rail at the assumed ~330 µA magnitude.
3. **Oscilloscope capture at BQ pads** — gold standard, blocked until ~2026-04-28 (new scope arriving). Capture two waveform features in one session, with the failing cable connected and TCA2 open (Phase 18 confirmed the disturbance is live during this window, not transient at insertion): (a) SCL-correlated wobble on SDA at BQ's pad below V_IH = 1.3 V during the 9th-clock ACK window (Story D-revised's prediction, primary target); (b) rising-edge overshoot above ~3.9 V at BQ's pad (legacy from original Story D framing, sanity check). See `docs/debugging/i2c-oscilloscope-debugging.md` (updated for Phase 17) for setup and discrimination outcomes.
4. **v8 design with I2C buffer between upstream bus and BQ** — independently justified by Phase 15 + 17 + 18. Run in parallel with diagnostic work; the scope only confirms which precise mechanism, not whether the buffer fix is needed. Candidate parts: P82B96, PCA9517, LTC4311.

**Deprioritised:**

- Cable-position scope test (operator's 2.5 cm horizontal geometry already represents worst case for cable-as-antenna).
- High-rate INA219 logging (Phases 11–18 make rail-mediated mechanisms unlikely).

---

## What to do with the investigation doc

It's a live handoff document — keep it current. When a test result comes in:
- Record the result factually in the appropriate phase section.
- Update the "Confirmed facts" list and "Ruled-out theories" table as appropriate.
- Update the Status banner at the very top if the big-picture state changes.
- Update "Candidate fixes" and "Immediate next steps" based on what's now viable.
- Keep the TL;DR in sync.

**Don't leave the doc in a stale state.** I'm worried about long-session context degradation and want the doc to always reflect current understanding. Treat it as the source of truth.

If a test confirms or rules out something, edit the doc *before* moving on to discussing next steps, so a future handoff catches it.

---

## Firmware state (debug mods currently in place)

The firmware has several debug modifications that aren't production-ready but are needed for the investigation. Full list in the "Firmware state (what's been modified)" section of the investigation doc. Highlights:

- `Wire.setClock(100000)` in `SensorManager::init()` (was 400000). Revert when fault is resolved.
- `runBusDiagnosticLoop()` in `SensorManager.cpp` runs continuously on sensor init failure. Prints `BQ:X(n)` with the actual I2C error code. Gated by fault, can stay.
- `PCA9546A::selectChannelVerify()` added — keep post-fix.
- `STARTUP_I2C_SCAN=true` in `platformio.ini` — can stay, cheap.
- `DIAG_NO_WIFI` build flag + `motion-play-v7-diag` env — inherits from `motion-play-v7` with WiFi/BT disabled. Useful for future RF-related debugging.

The "Revert list" section of the investigation doc has the precise list to clean up once the fault is fixed.

---

## How I work and what I expect from you

I'll push back when you drift from these:

- **Be direct.** Short responses to simple questions. No trailing summaries restating what you just did. I read the diff.
- **Don't over-hedge.** If evidence supports a conclusion, say it. If it doesn't, don't pretend it does.
- **Challenge me when my framing doesn't match the evidence.** A previous session almost let "why would pullups selectively fail for only BQ but not INA?" go by with hand-wavy signal-integrity language. I called it out, we re-examined, and the pullup-strength theory turned out to be wrong. Pushing back is part of the collaboration.
- **Deprioritize manufacturing-defect theories.** When something reproduces across multiple boards, "cold solder joint" and "wrong part" are unlikely explanations and should be demoted. Still consider them, but not first.
- **Don't hesitate on PCB changes due to existing enclosure designs.** The enclosure follows the PCB, not the other way around.
- **Never use Simulation_SPICE symbols for physical PCBs** — they're for simulation only and have wrong pin mappings. Probably not relevant here, but listed for completeness.
- **When I ask you to write docs, write them thoroughly.** I value having things written down for handoff.
- **Take session-degradation concern seriously.** Update doc files, use handoff files, don't rely on "you remember what we talked about."

I'm a hardware/firmware engineer building the Motion Play sensor system. I have real context for what you say — don't over-explain basic electronics or I2C. I'll ask if I want detail.

---

## Collaboration loop

Typical back-and-forth:

1. I run a test, paste the log (often with formatting glitches from the diagnostic box-drawing — don't worry about those).
2. You interpret the result, compare against theories, update the doc, propose the next test or a new analysis.
3. I decide whether to run it, or push back with a clarifying question or a different angle.
4. Loop.

Keep interpretations tight and testable. When proposing a test, state what each possible outcome would tell us. I choose which tests to run — if I skip one, respect that and move on.

Before modifying a file, check whether I've already modified it (look for a recent system reminder about file changes). I sometimes make edits between sessions — take those edits into account, don't revert them unless I explicitly ask.

---

## Immediate next step

The previous fresh-perspective prompt and its assessment have been folded into the investigation doc (Phase 10 onward) and superseded by Phases 17 and 18. The current immediate next step is **the Arduino-as-master probe of BQ in the failing config** — now the uncontested top of the priority list, since Phase 18 closed the bench-PSU sanity check. See `docs/debugging/v7-i2c-investigation.md` § "Immediate next steps" item 1 for full details.

Implementation is **ready** — the `DIAG_RELEASE_I2C` build flag exists as a sibling of `DIAG_NO_WIFI` / `BUS_RECOVERY_TEST` (env: `motion-play-v7-relbus` in `platformio.ini`). The firmware boots through `configureBQ24195()` exactly like the regular build, runs a 5-iteration diagnostic burst to confirm the BQ NACK reproduces on the ESP32 side first, then closes all TCA channels for a clean baseline, calls `Wire.end()`, reconfigures GPIO 43/44 to `INPUT` (no internal pull — on-board 2.2 kΩ R28/R29 hold the lines at idle high), prints "BUS RELEASED", and sits in a 5-second heartbeat loop. The companion Arduino sketch is `tools/arduino-sketches/v7_bq_master_probe/v7_bq_master_probe.ino`. Procedure: `pio run -e motion-play-v7-relbus -t upload`, wait for "BUS RELEASED" on serial, wire Arduino Nano ESP32's SDA/SCL/GND to TPIO43 / TPIO44 / a GND test pad on the main PCB (share GND only, do not tie 3.3 V or 5 V rails together), leave the failing-config cable in J6, flash the Arduino sketch, and read its serial output. The Arduino runs the same BASE/TCA0/TCA1/TCA2 probe pattern from its own master.

Expected outcomes:

- BQ NACKs Arduino too → Story D-revised confirmed (BQ's input is the problem regardless of master). Story F refuted.
- BQ ACKs Arduino → Story F confirmed (ESP32-S3 I2C peripheral interaction is part of the trigger). Story D-revised weakened or refuted.

Either outcome is high-information. Either way, the v8 buffer fix is correct.

A sibling test to run in any free moment that doesn't depend on the firmware change: the Phase 11 current measurement (DMM in-line with the cable's VCC wire during the rail-load-only setup, expect ~330 µA). It's a quick verification of an existing result rather than a hypothesis-discriminator, but useful to close out the loose end.

---

## Key commands and paths

- Firmware source: `firmware/src/` — main entry is `firmware/src/main.cpp`. Sensor logic is in `firmware/src/components/sensor/SensorManager.{cpp,h}`.
- Build: `pio run -e motion-play-v7 -t upload` (normal), `pio run -e motion-play-v7-diag -t upload` (WiFi/BT off), `pio run -e motion-play-v7-busrec -t upload` (bus-recovery test for Story A residual), or `pio run -e motion-play-v7-relbus -t upload` (release I2C bus to external master after confirming NACK reproduces — Arduino-as-master test).
- Serial monitor: `pio device monitor -e motion-play-v7` at 115200 baud.
- PCB circuit context: `hardware/pcb-main/kicad/circuit-context.json`.
- PCB placement context: `hardware/pcb-main/kicad/pcb-layout-context.json`. Note: **placement only, no routing/tracks**. The `tools/pcb-context/` tooling might be extendable to include routing if needed.
- Arduino external-master sketches:
  - `tools/arduino-sketches/vcnl4040_i2c_diagnose/vcnl4040_i2c_diagnose.ino` — sensor assembly health check (tests rigid + flex + VCNL standalone).
  - `tools/arduino-sketches/v7_bq_master_probe/v7_bq_master_probe.ino` — Arduino-as-master discrimination test (Story D-revised vs Story F). Pair with the `motion-play-v7-relbus` firmware build.

---

## One thing worth emphasizing

The "any DC path to 3.3 V, regardless of resistance value, triggers the fault" finding is still the most counter-intuitive result we have. A 47 kΩ pullup is ~70 µA of steady-state current, but that's enough — while floating wires with no pullup aren't. The fault is triggered by *the existence* of a DC return path, not its magnitude.

Phase 17 reframed Story D into a CMOS receiver noise-margin failure that absorbs this observation cleanly: the cable's added parasitic C (~5–10 pF, from the connector + wire) is roughly constant across the 4.7 kΩ to 47 kΩ pullup-strength range, so the gating effect on SDA's edge dynamics at BQ's pad is similarly invariant. The pullup just establishes a DC bias on the conductor; the parasitic C is what changes the receiver's dynamic noise margin. Phase 18 sharpened it further: the disturbance is ongoing while the cable is electrically connected, not a transient at plug-in (BQ recovers spontaneously between TCA2 selections within a single diagnostic-loop iteration). So the mechanism is the steady-state crosstalk + parasitic-loading regime — exactly what Story D-revised predicts, and exactly what the scope should see when it arrives. That's the current best mechanistic explanation for both the pullup-strength invariance and the live/ongoing recovery pattern, and worth holding in mind when evaluating any new test result — if a test would change cable parasitics significantly (different cable length, different connector, ferrite bead, etc.) and the fault behaviour shifts, that's strong support for Story D-revised.

Don't be shy about questioning the framing — I'd rather you say "I think we're missing something fundamental" than keep grinding. Phase 17 happened because the previous session pushed back hard on the original Story D, and it turned out the original framing was mechanistically unsupported by the BQ datasheet. Same energy welcome going forward.
