> **Pre-retry interpretation: conclusions not authoritative; see `lab/STATE.md`.** Reference facts may be cited from this file; its conclusions may not.

# Scope probe direct on BQ24195 SDA pin 6 — procedure plan

## Context

Phase 19's scope session captured the BQ NACK on the wire at TPIO43 (`Write:D6 A:1`), but at that probe point SDA does not visibly dip below V_IH = 1.3 V during the 9th-clock ACK window. This doesn't refute Story D-revised: TPIO43 is ~34 mm of trace away from BQ on the upstream bus, and the doc has noted all along that the wobble is predicted to be largest *at BQ's pad specifically*. The next decisive test is to capture SDA at BQ24195's actual SDA pin 6 with the failing-config cable in J6 and TCA2 selected, and look for sub-1.3 V wobble during the 9th-clock window.

BQ24195 is a VQFN-24 package, **0.5 mm pin pitch, pads 0.8 × 0.3 mm**. Hook clips cannot grip these pads — the only viable approach is to solder a thin fly-wire to pin 6 from the side and probe the wire stub.

Pin geometry (from `pcb-routing-context.json`, U5 at rotation 90°):

| Pin | Net | Position (mm) | Pad size (mm) |
|---|---|---|---|
| 5 | /I2C_SCL | (97.635, 119.604) | 0.8 × 0.3 |
| 6 | /I2C_SDA | (98.135, 119.604) | 0.8 × 0.3 |

Pins 5 and 6 are adjacent, so any solder bridge between them shorts SDA to SCL — both lines are equally critical and a bridge would brick the I2C bus. Pin 7 (CHRG_INT) is also adjacent on the perpendicular side of the package.

## Tools and materials

**What you already have / are using:**

1. **28 AWG BNTECHGO polyurethane enameled magnet wire (155°C insulation rating)** — appropriate for this job. Thicker than the 32–36 AWG ideal for 0.5 mm pitch, but workable: the wire approaches pin 6 from the side of the IC (not from above), so its 0.32 mm diameter doesn't have to fit between pins — only the tinned tip lands on the side edge of pin 6. Thermal mass is higher than thin magnet wire, so iron dwell will be 1–2 s rather than a half-second. The 155°C rating is for continuous operation, not for resisting brief soldering contact — the enamel burns off cleanly at 320–380°C iron temperature, exactly as intended for magnet wire.
2. **E/Fusing 900 Moldable Silicone Putty** — fine for *temporary* use during the scope session. Use it to anchor the magnet-wire stub 5–10 mm away from BQ pin 6 (on a non-component PCB area) so the hook clip can grip without pulling on the BQ joint. Caveat: if the putty smells of vinegar while curing, it's acetic-cure silicone which can corrode copper traces over weeks/months — don't leave it on the PCB long-term, remove cleanly after the session. For a few hours of exposure, no concern.
3. **Soldering iron** — assumed fine-tip (0.4 mm or smaller); confirm the tip is clean before going near BQ.
4. **Solder with rosin flux core** — assumed; brings its own flux to the joint.
5. **Tweezers, solder wick, IPA + brush** — assumed standard rework kit.
6. **Multimeter for continuity testing.**

**Flux application:**

- If solder has a flux core, the solder itself brings flux to the joint and that's typically sufficient for this single-pin tack. No separate flux strictly required.
- If you want extra flux: a toothpick dipped in flux paste gives much more controlled placement than tweezers (which can smear and leave residue between pins). Even better is a flux pen ($10, e.g. MG Chemicals 8341) — buy one if you'll keep doing fine-pitch work.
- Avoid the tweezers method if possible — it's hard to control the flux quantity and risks bridging.

**Magnification (essential at 0.5 mm pitch):**

- USB microscope ($30–80) — adequate, screens the view on a laptop, frees both hands. Recommended if you don't already have magnification.
- Optical loupe or magnifier headband ($20–80) — hands-free, eyes-only, good but tiring.
- Stereo microscope ($200+, AmScope SE) — gold standard if you'll do this often.

**Highly recommended for sustained scope work (not required for this single session):**

- **Sensepeek PCBite, $200–400** (`sensepeek.com`). Magnetic base + flexible arms with very fine spring-loaded probe tips that land directly on small SMD pads. Eliminates the "solder fly-wires every time you want to probe" workflow entirely. Overkill for one measurement, but genuinely transformative if you continue doing scope-on-PCB work. Cheaper Aliexpress clones exist (~$50) with mixed reviews.
- **PCB vise / third hand** ($20–50) — holds the board at a comfortable angle for soldering.

## Procedure

### Phase A — Practice on Board 1 (the damaged/investigation-dead board)

This is risk-free skill-building. Board 1 is already dead; further damage is fine. The goal is to validate the technique before applying it to Board 3.

1. **Power off, USB unplugged, no failing cable connected.**
2. **Identify Board 1's BQ24195 (U5).** Same physical layout as Board 3 — top-right quadrant of the BQ area, the QFN-24 package. Pin 1 is marked with a dot or notch on the IC.
3. **Confirm pin 5 and 6 orientation** with the PCB silkscreen / a multimeter (continuity from pin 6 to TPIO43 should beep; pin 5 to TPIO44 should beep). Even on damaged Board 1 this should still be intact unless the BQ chip itself was lifted in Phase 7.
4. **Cut a ~5 cm length of magnet wire.** Tin one end with a small drop of solder — the heat will burn off the enamel and tin the copper. The tinned tip should be no more than 1 mm long.
5. **Apply a small dab of flux** to BQ pin 6 on Board 1.
6. **Approach pin 6 with the tinned wire tip from the side** (perpendicular to the IC, parallel to the pin's long axis). Don't try to land the wire on top of the pad — go in from the edge of the package where the pin emerges.
7. **Tack the wire to the pin** with a brief touch of the iron — no more than 1–2 seconds. The flux on the pin and the tinned wire tip will fuse into a small joint at the pin's edge.
8. **Inspect under magnification.** Check for bridges to pin 5 (SCL) or pin 7 (CHRG_INT). If you see a bridge, use solder wick to remove and try again. If the joint looks clean and only on pin 6, success.
9. **Continuity-test the joint:** DMM in continuity mode, one probe on the wire stub's far end, other probe on TPIO43 (SDA test point). If it beeps, the joint conducts and pin 6 is electrically reachable through the stub.
10. **Tug-test the joint:** gently pull on the wire stub. If it stays attached, the joint is mechanically sound. If it pops off, redo with slightly more solder.
11. **Repeat steps 4–10 a few times until you can do it cleanly on the first try.** Each attempt teaches the right iron temperature, dwell time, flux amount, and approach angle.

### Phase B — Apply to Board 3

Once Phase A is comfortable:

1. **Power off Board 3, unplug USB, remove failing-config cable from J6.** No power, no signals.
2. **Repeat Phase A steps 4–10 on Board 3's U5 pin 6.** This time it matters: a bridge to pin 5 will short SDA to SCL on the working investigation board. Do not rush.
3. **Continuity-test the new joint:** DMM probe on the new wire stub's far end, other probe on TPIO43. Should beep.
4. **Optional but recommended: also continuity-test pin 5 to pin 6 with the wire stub installed.** They should NOT be shorted (no beep). If they beep, you have a bridge — clean and redo.
5. **Visually inspect under magnification one more time** before powering up.

### Phase C — Scope capture at BQ pin 6

1. **Power on Board 3, no failing cable yet.** Confirm the firmware boots normally and the diagnostic loop runs.
2. **Move CH1 probe** from TPIO43 to the new wire stub at BQ pin 6. CH2 stays at TPIO44 (SCL). Both ground clips stay at the same GND test pad.
3. **Restore scope settings** (per the recap from earlier: CH1 = 1 V/div DC, CH2 = 1 V/div DC offset −3 V, timebase 100 µs/div, trigger I2C Address & Data on 0x70 / Write / Data 4, threshold 1.6 V, decode I2C with format Hex, R/W with).
4. **Plug in the failing-config cable** to J6 (10 kΩ between cable's SDA wire and a +3.3 V source, SCL wire dangling).
5. **Confirm in serial** that BQ:X(2) reproduces on TCA2 rows.
6. **Press Single. Capture the BQ NACK.** Verify decoded annotation reads `Write:D6 A:1`. Save as `phase19_failing_BQ_pin6_NACK.png`.
7. **Vertical zoom on SDA**: change CH1 vertical scale from 1 V/div to **500 mV/div** (or 200 mV/div if needed), position SDA's zero off-screen so the high-level region (~1 V to 4 V) fills the visible window. Press Single again. Save as `phase19_failing_BQ_pin6_NACK_vzoomed.png`.
8. **Cursor-measure SDA's minimum voltage during the 9th-clock ACK window** (where the `A:1` indicator is). On DHO804: `Cursor` → type `Y` → position cursors on SDA's lowest excursion during the 9th clock. Note the minimum voltage in millivolts.

### Phase D — Comparison capture (clean baseline at BQ pin 6)

1. Unplug failing-config cable from J6. Verify in serial that BQ:. on every row.
2. Press Single. Capture the clean transaction (will trigger on the same TCA channel-2 select, but BQ ACKs this time → `Write:D6 A:0`). Save as `phase19_clean_BQ_pin6_ACK.png`.
3. Vertical zoom too if useful. Save as `phase19_clean_BQ_pin6_ACK_vzoomed.png`.

## What to look for

The diagnostic signal is the **comparison between Phase C and Phase D**:

- **SDA minimum voltage during the 9th-clock window dips below V_IH = 1.3 V in Phase C but stays solidly above 1.3 V in Phase D**: Story D-revised confirmed at BQ's pad. The mechanism is CMOS receiver noise-margin failure caused by the cable + crosstalk + TCA pass-gate dynamics. v8 buffer fix is justified.
- **No visible difference between Phase C and Phase D at BQ's pad either**: Story D-revised refuted at the pad. Mechanism must be either purely internal to BQ's input stage (Story E variant) or master-side (Story F). Next move becomes the Arduino-as-master test.
- **Wobble visible in Phase C but doesn't cross 1.3 V**: partially supportive but inconclusive. Note the magnitude and run the Arduino-as-master test next.

## Files to update after the capture

- `docs/debugging/v7-i2c-investigation.md` — add Phase 20 capturing the BQ-pin-6 scope result. Include: probe-point change procedure, captured screenshots referenced, observed waveform features, cursor-measured SDA minimum, interpretation against Story D-revised.
- Status banner at top of the investigation doc.
- Decision on whether the Arduino-as-master test is now needed (depends on the Phase 20 result).

## Verification

End-to-end success criteria for this session:

- Phase A practice produces a clean wire-stub joint on Board 1's pin 6, validated by DMM continuity to TPIO43 with no bridge to pin 5.
- Phase B installs the same joint on Board 3 without bridges.
- Phase C captures `Write:D6 A:1` on the scope at the new probe point, with the failing-config cable in J6 and TCA2 selected.
- Phase D captures `Write:D6 A:0` at the same probe point, with the cable removed.
- Two pairs of screenshots saved (zoomed and unzoomed, clean and failing).
- Cursor-measured SDA minimum during the 9th-clock window in failing config noted in millivolts.
- Plain English summary of whether the wobble crosses V_IH = 1.3 V or not, and what that implies for Story D-revised.

## Critical safety notes

- **Never solder with the board powered.** Always power off and unplug USB before touching the iron to the IC.
- **Always remove the failing-config cable before soldering** — eliminates a stray-voltage path.
- **Always continuity-test before powering back on** — the most common rework mistake (bridge between adjacent pins) is detectable with a DMM in 30 seconds.
- **If the iron tip is dirty, clean it on the brass sponge before going near BQ pin 6.** A dirty tip leaves residue that can bridge.
- **If you're tired or rushed, stop and resume later.** Fine-pitch rework on the only working investigation board is not the place to push through fatigue.
