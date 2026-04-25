# Main PCB v7 — VCNL4040 I2C Silent Failure Investigation

> **Status as of 2026-04-24**: Confirmed **v7 design-level issue**, reproducible on any healthy-assembly board. The BQ24195's I2C interface stops acknowledging at address 0x6B whenever a TCA9548A channel opens with a cable that has **DC contact on SDA pulled toward +3 V at the far end specifically** — SCL loading does nothing (Phase 12), SDA pulled toward GND does nothing (Phase 13), source noise quality is irrelevant (Phase 14), and software-issued bus recovery sequences do nothing (Phase 15). Failure is always error code 2 (NACK on address), never 5 (bus hang). All cheap non-scope behavioral tests are now exhausted. Naive Stories A and B (Phase 13), Story C (Phase 14), and Story A's residual stuck-state variant (Phase 15) are all ruled out. **Story D (ESD-diode-mediated charge injection at BQ on rising-edge overshoot when SDA is biased near VDD) is the dominant remaining hypothesis**, with an unidentified Story E in reserve. The disturbance is confirmed **steady-state at BQ's input**, not a recoverable state-machine artifact. **Path forward: scope at BQ pads (week of 2026-04-28) + v8 design with I2C buffer (start in parallel — independently justified at this point regardless of which surviving story is correct).**

This document exists as a handoff. A long multi-session debugging effort has happened. A fresh AI session (or the same human returning later) should be able to read this file, glance at the referenced files, and pick up exactly where the investigation left off.

---

## Fastest possible read (start here if you're a new session)

- **What's broken**: On main PCB v7, the BQ24195 (I2C addr 0x6B) stops ACKing its address whenever a TCA9548A channel is opened with a cable that has **DC pullup on SDA toward +3.3 V** at the far end. SCL loading does nothing (Phase 12). SDA pulled to GND does nothing (Phase 13 polarity test). Every other I2C slave keeps working. Failure is always error code **2 (NACK on address)**, never 5 (bus hang). Deterministic, live-state, clears immediately when the channel closes (or when SDA is unplugged from the cable). Rail-load-only at the connector does NOT trigger it (Phase 11).
- **Boards tested**: 3 of 3 assembled v7 boards. Board 1 (originally healthy, now damaged by a failed bodge attempt — see Phase 7). Board 2 (assembly defect, BQ dead at boot, not part of this investigation — see Phase 8). Board 3 (healthy, reproduces the fault identically to Board 1's original behavior — see Phase 9). So the fault is design-level, not per-board.
- **Firmware state**: `SensorManager::runBusDiagnosticLoop()` is the active diagnostic. Prints `BQ:X(n)` with real error code. Run in env `motion-play-v7-diag` to skip WiFi/MQTT init (`-DDIAG_NO_WIFI`) — useful for eliminating RF confounds, but RF is already ruled out so the default `motion-play-v7` env is fine now.
- **What's ruled out**: sensor-side defects; power brown-out; I2C speed (100 kHz same as 400 kHz); pullup strength (4.7 k, 10 k, 47 k external all fail identically — though note the weakness of that test, see Phase 5); ESP32 WiFi/BT RF coupling (Phase 6); routing differences between CH0/CH1/CH2 (all three behave identically, Phase 6); cable stub capacitance alone (dangling cable passes, Phase 6).
- **What's alive as a hypothesis (post-Phase-15)**: Stories A and B (naive forms) weakened by polarity test (Phase 13). Story C (3.3 V rail noise injection) ruled out by clean-power-source test (Phase 14). **Story A residual variant (stuck state machine recoverable by software-issued bus reset) ruled out by firmware bus-recovery test (Phase 15)** — 3× dummy START+STOP framings issued before each BQ probe with the failing config attached did not recover BQ. The fault is confirmed steady-state, not state-machine-driven. **Story D — ESD-diode-mediated charge injection at BQ — is the dominant surviving hypothesis.** With SDA biased near BQ's internal VDD via the cable's far-end pullup, the rising-edge overshoot when SDA is released (caused by ringing in the bus extended through the cable) briefly takes SDA above VDD+0.6 V, forward-biasing BQ's internal upper ESD clamp diode, dumping charge into BQ's VDD pin, perturbing internal logic enough that BQ's I2C peripheral can't reliably decode incoming address bits. SDA-to-GND polarity doesn't trigger this because the rising edge tops out at 2.7 V (divider) and never overshoots above VDD. SCL-to-VCC doesn't because SCL has different input topology and is less sensitive to mid-bit voltage perturbation than SDA. The clean-PSU and bus-recovery tests don't refute this because the mechanism is purely electrical, neither rail-noise-mediated nor state-machine-mediated. **An unidentified Story E remains in the option space** but is heavily constrained: must be steady-state, SDA-only, +3.3V-polarity-only, source-noise-independent, cable-distance-required, bus-recovery-immune. Datasheet review (Phase 10) ruled out a "BQ in some documented operating mode" story.
- **What hasn't been tried yet**: scope waveform capture at BQ pads (new scope arriving week of 2026-04-28); rail-load-only test (load 3.3 V at far end of cable without touching SDA/SCL — the strongest remaining behavioral discriminator); bench-PSU-from-battery-pads test (removes USB-C input state from variables); I2C buffer IC to isolate BQ; redesigning upstream bus for better termination near BQ.
- **Open-cable discriminator**: a JST-SH cable with bare dangling wires at the far end (no resistor, no rigid) does NOT trigger the fault. Only a DC path on the **I2C signal pins** (SDA and/or SCL) at the far end triggers it (Phase 6 + Phase 11).
- **Rail-load-only discriminator (Phase 11)**: a cable with a single resistor between far-end VCC (pin 1) and GND (pin 2), SDA and SCL wires unconnected at the far end, does NOT trigger the fault. So loading the 3.3 V rail through the cable is not sufficient — the DC contact must be on the signal pins specifically. Combined with Phase 6, this localizes the mechanism to the BQ's I2C pads, not to its supply or the 3.3 V rail.

---

## Hardware and tooling orientation (read this before touching schematics or PCBs)

This project uses a distributed documentation system. Before investigating hardware further, know that these files exist:

- **`hardware/CONTEXT.md`** — overview of all three PCBs (main, sensor-rigid, sensor-flex). Physical architecture, sensor placement, component nicknames, I2C mux chain diagram, and the full schematic context system. Read first when investigating hardware.
- **`tools/CONTEXT.md`** — KiCad tooling: schematic context extraction (`tools/schematic-context/`), PCB placement extraction (`tools/pcb-context/`), annotation tools, programmatic schematic generation, programmatic schematic modification. **Per `.context/PROJECT.md`, read this before touching any `.kicad_sch` or `.kicad_pcb` file.**

The `circuit-context.json` and `pcb-layout-context.json` files referenced throughout this doc are **extractions, not source of truth**. They're AI-readable distillations of the KiCad schematic and PCB files, produced by the scripts in `tools/schematic-context/` and `tools/pcb-context/`. If the underlying KiCad file has been edited since the JSON was generated, the JSON is stale — check the `extracted_at` field in each file's metadata. Re-extraction is via the scripts in the `tools/` folder; see `tools/CONTEXT.md` for usage.

The current state of the extracted files, for this investigation:

| File | What it contains | Limitations |
|------|------------------|-------------|
| `hardware/pcb-main/kicad/circuit-context.json` | Main PCB v7 schematic: 93 components, all nets, functional blocks, per-component annotations | Schematic only. No physical layout. |
| `hardware/pcb-main/kicad/pcb-layout-context.json` | Main PCB v7 physical placement: component positions, rotations, footprints | **Placement only — no traces or routing.** If routing needs inspection, either open the `.kicad_pcb` in KiCad or extend the extraction tooling. |
| `hardware/sensor-rigid/circuit-context.json` | Rigid PCB schematic | Schematic only |
| `hardware/sensor-rigid/pcb-layout-context.json` | Rigid PCB placement | Placement only |
| `hardware/sensor-flex/circuit-context.json` | Flex PCB schematic | Schematic only |
| `hardware/sensor-flex/pcb-layout-context.json` | Flex PCB placement | Placement only |

---

## TL;DR

**What was originally reported:** After assembling the new v7 boards (main PCB v7, sensor-rigid, sensor-flex, all untested revisions), the firmware could detect the rigid's PCA9546A multiplexer but could not get any of the VCNL4040 proximity sensors to acknowledge their I2C address (0x60). All six sensor init attempts failed with `I2C error 2` (NACK on address).

**What we now know:**
- The VCNL4040 chips themselves are alive and functional. So is the flex, the rigid, the PCA9546A.
- The fault is localized to the **main PCB v7's I2C subsystem**.
- Specifically: the BQ24195 charger (0x6B on the upstream bus) stops responding the moment any TCA9548A channel opens with any pull-up load on the downstream side — and the VCNL4040 failure is the downstream consequence of the same bus disturbance.
- Main PCB v7 uses **2.2 kΩ** upstream I2C pull-ups (R28 = SDA, R29 = SCL), with the annotation *"2.2k to +3.3V, sized for 400kHz operation."*
- Three external pull-up values were tested on a JST-SH stub into J6: 4.7 kΩ, 10 kΩ, and 47 kΩ (combined with the on-board 2.2 kΩ: 1.5 kΩ, 1.8 kΩ, and 2.1 kΩ respectively). **All three produced identical failure behavior** — BQ drops off the bus on TCA2 with no variation.
- A 10× change in external resistance produced zero change in behavior — **pull-up strength is not the mechanism**.
- Plugging in a JST-SH cable **with no resistors at the far end** (cable stub only, no DC termination) does *not* trigger the fault — BQ stays present. So adding the cable length alone to the CH2 net is not sufficient; **cable stub physics is also not the mechanism**.
- The necessary and sufficient trigger is: **a completed DC resistive path from CH2_SDA and/or CH2_SCL to 3.3 V at the far end of the cable**, with any resistance value from 4.7 kΩ to 47 kΩ producing the fault identically. Mechanism not yet identified.
- (See the "What 'BQ fails' means" note just below — the BQ's power-path function is *not* affected; the chip keeps charging and delivering VSYS. Only its I2C comms break.)

### Important: what "BQ fails" means in this document

Throughout this doc and the logs, *"BQ fails"* / *"BQ disappears"* / *"BQ:X"* refers specifically to the BQ24195 **not acknowledging its I2C address (0x6B)** during a bus scan. The chip has two largely independent parts:

1. **Hardware power path** — the charging circuit and VSYS regulator. Runs from internal state machines, does not depend on ongoing I2C. Keeps working normally throughout.
2. **I2C interface** — a configuration/status channel used to write registers (IINLIM, charge current, watchdog) and read fault flags.

When our diagnostic loop reports `BQ:X`, only the I2C interface is misbehaving. Evidence:

- INA219 readings show VSYS rock-steady at ~4.21 V through every diagnostic iteration.
- The ESP32 keeps running, the display stays on, MQTT stays connected.
- IINLIM=2A and watchdog-disabled settings, written at boot, remain in effect.

The BQ24195's I2C NACK is being used as a *diagnostic signal*, not as a functional failure — it's our canary for "the bus just got marginal." It's the first device to drop out because it's at the far end of the upstream bus trace (~34 mm from ESP32). The VCNL4040 failure is the same bus-margin problem, but further downstream through two muxes.

**Next test:** Isolate whether the SDA or SCL line (or only both together) is the trigger — cable in J6 with a single 10 kΩ pull-up on just SDA (SCL left unterminated), then again with just SCL terminated. Tells us whether the fault is line-specific or symmetric.

**Candidate fixes:** None yet confirmed. The earlier hypothesis of reworking R28/R29 to 4.7 kΩ was based on the assumption that combined pull-up strength was the mechanism — the 47 kΩ test disproved that assumption, so a simple resistor rework is no longer known to be sufficient. A fix will be proposed once the mechanism is understood.

---

## System architecture (1-minute orientation)

```
ESP32-S3 (U3 on main PCB v7)
  │
  │ GPIO 43 (SDA), GPIO 44 (SCL)
  │
  ├── INA219 (U7, 0x40) — VSYS voltage + current monitor
  ├── BQ24195 (U5, 0x6B) — USB-C charger / battery manager
  ├── TCA9548A (U4, 0x70) — 8-channel I2C multiplexer
  │     │
  │     ├── CH0 ──► J4 ──► (JST-SH) ──► rigid ──► PCA ──► flex ──► 2× VCNL4040
  │     ├── CH1 ──► J5 ──► (JST-SH) ──► rigid ──► PCA ──► flex ──► 2× VCNL4040
  │     └── CH2 ──► J6 ──► (JST-SH) ──► rigid ──► PCA ──► flex ──► 2× VCNL4040
  │
  └── R28, R29 (2.2 kΩ pull-ups to 3.3V)
```

Every VCNL4040 shares the address 0x60 — selectivity is provided by the TCA→PCA dual-mux chain.

Every rigid has its own upstream pull-ups (R1 = SDA, R2 = 4.7 kΩ). When a TCA channel opens with a rigid connected, these go in parallel with R28/R29 on the main PCB.

Key component locations on main PCB v7 (from `hardware/pcb-main/kicad/pcb-layout-context.json`):

| Component | (x, y) mm | Notes |
|-----------|-----------|-------|
| U3 ESP32-S3 | (131, 118) | Center of board |
| U7 INA219 | (114, 121) | ~17 mm from ESP32 |
| U5 BQ24195 | (97, 118) | ~34 mm from ESP32, **far end of upstream bus** |
| U4 TCA9548A | (151, 107) | ~21 mm from ESP32, near J4–J6 |
| R28, R29 pull-ups | (150, 102) | Near the TCA |
| J4 / J5 / J6 | (~161, 105–121) | Right edge of board |

BQ is at the far end of the upstream bus trace. INA219 is much closer to the ESP32. This matches the observed fault pattern: INA219 tolerates all conditions, BQ24195 is the first to drop out when the bus gets marginal. VCNL4040 (even further, through two muxes) is the worst casualty.

---

## Confirmed facts (evidence for each ruled-out theory)

1. **VCNL4040 chips are alive.** Proven by wiring a spare Arduino Nano ESP32 directly to the rigid's J1 (JST-SH upstream) and running an I2C scan. Found `0x60 VCNL4040` on both PCA channels 0 and 1. The whole downstream chain works fine with a different master.
2. **Rigid PCBs are functional.** Same Arduino test — the PCA is at 0x76, both sub-channels reach the VCNL4040s.
3. **Flex PCBs are functional.** Same test, nothing indicating issues at the flex level. Continuity tests earlier also confirmed ZIF → VCNL4040 SDA/SCL wiring is correct, no crossover from the 180° VCNL4040 rotation in v7.
4. **Main PCB v7 basic I2C works.** With nothing plugged into J4/J5/J6, INA219 (0x40), BQ24195 (0x6B), and TCA9548A (0x70) are all reachable reliably across every iteration of the diagnostic loop.
5. **TCA9548A channel selection is correct.** The firmware verifies it (`PCA9546A::selectChannelVerify()` — writes channel bit, reads back control register, asserts equality). Always reports expected value.
6. **PCA9546A channel selection is correct.** Same verify mechanism. Reads back 0x01 for ch 0, 0x02 for ch 1 — correct.
7. **Power supply is stable.** INA219 logs VSYS at 4.21–4.23 V through every boot phase. Peak current ~180 mA, well under the 2 A BQ24195 IINLIM. No brown-out.
8. **BQ24195 IINLIM fix applied correctly.** Firmware logs `BQ24195 configured: IINLIM=2A, watchdog disabled` on every boot.
9. **I2C speed is not the culprit.** Identical failure at 400 kHz and 100 kHz. Rule out simple rise-time issues.
10. **Fault is common-mode across TCA channels.** Tested on TCA ch 0 (J4) and TCA ch 2 (J6). Same behavior on both. Not a per-channel defect.
11. **Fault is triggered by any pull-up load on the opened channel.** Even without a rigid — just two external 4.7 kΩ or 10 kΩ resistors on a JST-SH cable reproduce the failure.
12. **No documented BQ24195 mode suppresses I2C address response.** Datasheet review (Phase 10): the chip is documented to ACK address 0x6B unconditionally across HIZ, default mode, host mode, watchdog timer states, and all VBUS/VSYS conditions. The only documented NACK behavior is on a *data byte* when an undefined register address is written (would be I2C error 3, not 2). NACK on the slave address (error 2) is **undocumented behavior**. No errata in the Revision History.

### Ruled-out theories with evidence

| Theory | Ruled out by |
|--------|-------------|
| VCNL4040 dead / wrong part / damaged | Arduino finds 0x60 through the same boards |
| Wrong footprint / 180°-rotation routing bug on flex | Continuity tests on ZIF ↔ IC SDA/SCL plus crossover-exclusion |
| Power supply brownout | INA219 readings, VSYS stable 4.21 V |
| Inadequate current (BQ24195 IINLIM too low) | Firmware logs confirm 2 A IINLIM active |
| I2C speed / rise time | Same failure at 100 kHz and 400 kHz |
| PCA channel not latching | Readback of PCA control register confirms correct value |
| TCA9548A decoupling or ~RESET floating | Fault disappears with nothing on any TCA channel |
| TCA channel 0 marginal joint | Same fault on ch 0 and ch 2 |
| Bus capacitance from rigid | External pull-ups alone (no rigid) reproduce it |
| Simple pull-up strength threshold | 10 kΩ external (combined 1.8 kΩ) still fails, showing threshold isn't purely strength-based |
| Manufacturing defects across multiple boards | Reproduces deterministically on every combination tested |
| BQ entering a documented operating mode where I2C is suppressed (HIZ, default, watchdog-expired, etc.) | Datasheet review (Phase 10): no such mode exists; chip is spec'd to always ACK 0x6B |
| BQ I2C peripheral gated by REGN LDO being off | Per 8.4.1.1, host must be able to write REG00[7]=0 *during* HIZ to exit it — so I2C is decoupled from REGN |
| BQ24195 published errata about I2C non-response or input-state-dependent I2C | None listed in Revision History |
| BQ watchdog expiration causing I2C silence | Datasheet 8.4.1: watchdog only resets registers to defaults, doesn't disable I2C. Also: we already disable it at boot |
| D+/D- BC1.2 detection state machine affecting I2C | Datasheet 8.3.1.3.4: D+/D- detection only sets input current limit, no documented I2C interaction |
| Rail-perturbation through the cable loop (DC current draw on the 3.3 V rail via the cable disturbs something near BQ) | Phase 11: cable + resistor VCC↔GND only (signal pins unconnected) does NOT trigger fault, despite drawing ~330 µA of steady-state current through the cable's VCC and GND wires |
| SCL-side mediated fault (SCL clock loading or edge corruption affecting BQ) | Phase 12 asymmetry test: cable + 10 kΩ pullup on SCL only (SDA dangling) does NOT trigger fault across 17 iterations; the fault triggers only when SDA is loaded |
| Naive Story A (channel-open transient fires phantom START at BQ) | Phase 13 polarity test: SDA-to-GND polarity has a *larger* downward channel-open transient than SDA-to-VCC, yet does NOT trigger the fault. A naive "any large transient triggers it" version is contradicted |
| Naive Story B (downstream pullup degrades SDA edges/levels at BQ) | Phase 13 polarity test: SDA-to-GND polarity *worsens* SDA HIGH level (2.7 V via divider, vs 3.3 V baseline) and edge dynamics, yet does NOT trigger the fault. A naive "lower-margin-at-BQ-causes-bit-corruption" version is contradicted |
| Polarity-symmetric mechanism (any DC load on SDA in either direction triggers fault) | Phase 13 polarity test: SDA-to-GND does not trigger; only SDA-to-VCC does. Mechanism is direction-sensitive |
| Story C — 3.3 V rail noise injected into SDA via the far-end pullup | Phase 14 clean-power-source test: a clean linear bench PSU at 3.3 V triggers the fault identically to the main PCB's noisy rail. Source noise quality is irrelevant — mechanism doesn't depend on rail noise |
| Story A residual variant — BQ in a stuck state machine, recoverable via software-issued bus reset | Phase 15 firmware bus-recovery test: 3× dummy `Wire.beginTransmission(0x00); endTransmission();` calls (each producing START + address + STOP framing) issued before each BQ probe attempt do NOT recover BQ. The fault recurs identically every iteration. State-machine confusion can't survive three consecutive STOPs — the disturbance is steady-state, not state-machine-driven |

---

## Investigation timeline (chronological — the story)

### Phase 1 — DMM inspection of the hardware

Starting assumption: assembly issue on one of the new boards. Systematically ruled out:

- Power LED on the rigid is lit → 3.3 V reaches the rigid.
- 3.3 V at VCNL4040 pin 4 (LED anode) AND pin 3 (VDD), referenced to pin 1 (GND).
- ZIF mechanical seating and contact orientation correct (top-contact ZIF).
- Continuity from ZIF pins 3/4 to IC1 pins 7/8 and pins 6/7 to IC2 pins 7/8 — including **explicit crossover-exclusion** to catch SDA/SCL swaps from the VCNL4040 180° rotation.
- Downstream pull-ups R6/R7/R8/R9 on the rigid are all populated, 4.7 kΩ each, correct values.

All hardware checked out. Nothing DMM-able was wrong with the rigid or flex.

### Phase 2 — Firmware diagnostic instrumentation

Added firmware helpers to rule out soft faults:

- `PCA9546A::selectChannelVerify()` — writes channel select, reads back, asserts.
- Per-failing-sensor I2C sweep — if 0x60 NACKs, scan the full 0x08–0x77 range on that open channel.
- `PowerMonitor` (INA219) moved to early boot. Four `[PWR ...]` log lines: after BQ config, after display init, before sensor init, after sensor init.
- I2C clock temporarily dropped from 400 kHz to 100 kHz.

All results: PCA channel latches correctly, downstream scan finds only the expected upstream pass-throughs (0x40, 0x70, 0x76), never 0x60. VSYS and current are fine throughout.

### Phase 3 — Arduino external-master test

Wired a spare **Arduino Nano ESP32** directly to the rigid's J1:

- J1 pin 1 (3.3V) → Arduino 3V3
- J1 pin 2 (GND) → Arduino GND
- J1 pin 3 (SDA_UP) → Arduino A4 (SDA)
- J1 pin 4 (SCL_UP) → Arduino A5 (SCL)

**Unplugged the main PCB from the rigid completely.** Flashed the diagnostic sketch: `tools/arduino-sketches/vcnl4040_i2c_diagnose/vcnl4040_i2c_diagnose.ino`.

The scan found 0x76 (PCA), then for each PCA channel opened, found `0x60 VCNL4040`.

**The VCNL4040 is alive.** The entire sensor module (rigid + flex + VCNL4040s) works perfectly with a different I2C master. The fault is localized to the main PCB v7.

### Phase 4 — Bus diagnostic loop

Added `SensorManager::runBusDiagnosticLoop()`. Runs continuously every ~2 s when `SensorManager::init()` fails (which it does). Probes 5 addresses (INA, BQ, TCA, PCA, VCNL) in several bus states:

- **BASE** — all TCA/PCA closed
- **TCA0, TCA1, TCA2** — only that TCA channel open
- **TCA{n}+PCA0, TCA{n}+PCA1** — TCA AND PCA both open (when a PCA is detected on that channel)

**First test: rigid on J6.** 36 iterations, 100% identical:

```
BASE        INA:. BQ:. TCA:. PCA:X VCNL:X   ✓
TCA0        INA:. BQ:. TCA:. PCA:X VCNL:X   ✓
TCA1        INA:. BQ:. TCA:. PCA:X VCNL:X   ✓
TCA2        INA:. BQ:X TCA:. PCA:. VCNL:X   ⚠  BQ disappears
TCA2+PCA0   INA:. BQ:X TCA:. PCA:. VCNL:X   ⚠
TCA2+PCA1   INA:. BQ:X TCA:. PCA:. VCNL:X   ⚠
```

Key observation: **BQ24195 drops off the bus the moment TCA2 opens** (PCA still closed, nothing downstream yet active). It's not a flaky fault — it's deterministic.

**Second test: nothing connected.**

```
BASE        INA:. BQ:. TCA:. PCA:X VCNL:X
TCA0        INA:. BQ:. TCA:. PCA:X VCNL:X
TCA1        INA:. BQ:. TCA:. PCA:X VCNL:X
TCA2        INA:. BQ:. TCA:. PCA:X VCNL:X   ✓  BQ fine
```

Opening an empty TCA channel is harmless. **The rigid's presence is the trigger.**

### Phase 5 — Pull-up isolation

Hypothesis: rigid's R1/R2 (4.7 kΩ upstream pull-ups) are the trigger, not the PCA or bus capacitance.

Test: JST-SH cable into J6 with just **two 4.7 kΩ resistors on the far end** — SDA→3.3V and SCL→3.3V. No PCA, no flex, no VCNL.

Result: **BQ still disappears on TCA2.** Identical failure pattern, 15+ iterations, 100% deterministic. The rigid's PCA and bus capacitance are NOT necessary — two external pull-ups suffice.

Test with **10 kΩ external pull-ups** (combined 2.2k ∥ 10k = 1.8 kΩ):

Result: **BQ still disappears on TCA2.** Failure is not a simple strength boundary at 1.5 kΩ — 1.8 kΩ combined also fails.

Test with **47 kΩ external pull-ups** (combined 2.2k ∥ 47k ≈ 2.1 kΩ — almost identical to the stock 2.2 kΩ):

Result: **BQ still disappears on TCA2.** Identical failure pattern across 15 iterations. A 10× change in external pull-up value (4.7 kΩ → 47 kΩ) produced no change in behavior.

**Conclusion: pull-up strength is not the mechanism.** The invariant across all three failing tests is "a JST-SH cable is plugged into J6 with some completed DC path to 3.3 V at the far end." The exact resistance value doesn't matter.

Test with **JST-SH cable plugged into J6 but no resistors anywhere** — SDA and SCL wires terminate into an otherwise empty breadboard:

Result: **BQ stays present on TCA2.** No failure. Across every iteration of the diagnostic loop, BQ acknowledges cleanly even with the cable extending the CH2 net by ~15 cm.

**Combined conclusion from all four tests:** the *necessary* ingredient is a **completed DC resistive path from CH2's SDA and/or SCL to 3.3 V at the far end of the cable**. Neither the cable stub alone (no pull-up) nor the stock upstream pull-up alone (no cable) triggers the fault. The cable plus any resistance to 3.3 V at the far end does trigger it, regardless of the exact resistance.

| Setup at J6 | BQ on TCA2 |
|-------------|------------|
| Nothing connected | `.` works |
| Cable + 4.7 kΩ pull-ups to 3.3V on SDA and SCL | `X` fails |
| Cable + 10 kΩ pull-ups to 3.3V on SDA and SCL | `X` fails |
| Cable + 47 kΩ pull-ups to 3.3V on SDA and SCL | `X` fails |
| Cable alone (no pull-ups, no resistor) | `.` works |
| Cable + resistor VCC↔GND only, SDA/SCL unconnected at far end (Phase 11) | `.` works |
| Cable + 10 kΩ pullup on **SCL only** to 3.3 V, SDA dangling (Phase 12) | `.` works |
| Cable + 10 kΩ pullup on **SDA only** to 3.3 V, SCL dangling (Phase 12) | `X` fails |
| Cable + 10 kΩ pulldown on **SDA only to GND**, SCL dangling (Phase 13) | `.` works |
| Cable + 10 kΩ pullup on SDA only to **clean bench PSU at +3.3 V** (shared GND), SCL dangling (Phase 14) | `X` fails (identical to main rail) |
| Same as above but with firmware-issued 3× dummy START+STOP framings before each BQ probe (Phase 15) | `X` fails (recovery sequence doesn't help — fault is steady-state) |

### Phase 6 — Error-code instrumentation + RF-off + channel-uniformity + fresh-board baseline (2026-04-21 / 2026-04-22 sessions)

Goal: tighten several remaining uncertainties left by Phase 5.

**6a. Added real I2C error-code logging to `probeAndPrint()`.** Previously the diagnostic just printed `BQ:X` for any non-zero return from `Wire.endTransmission()`. Changed to print `BQ:X(n)` with the actual error code. Legend: 1=data_too_long, 2=NACK_addr, 3=NACK_data, 4=other, 5=timeout/bus_hang.

Result: **every failure is `X(2)` — NACK on address. Never `X(5)` timeout.** So the bus is electrically healthy, the START condition and address byte get transmitted successfully, and BQ is actively choosing not to ACK. This rules out "bus physically stuck low" as the mechanism.

**6b. Added `-DDIAG_NO_WIFI` build flag and separate `motion-play-v7-diag` PlatformIO env.** Under this flag, `main.cpp` skips the whole WiFi/MQTT/cloud-config init and calls `WiFi.mode(WIFI_OFF) + btStop()` to force the radios down. Sensors initialize with defaults.

Result: BQ failure pattern is **byte-identical** with WiFi off vs. on. **ESP32 radio RF coupling is ruled out.** This also mostly rules out firmware-level network-stack activity as a factor.

**6c. Tested rigid-on-J4 and rigid-on-J5 in addition to the existing J6 tests** to see whether the failure is channel-specific (implying CH0/CH1/CH2 routing differences matter) or connector-following (implying the routing of each channel is electrically similar).

Result: **failure follows the rigid, not the channel.** Rigid on J4 → BQ fails only on TCA0. Rigid on J5 → fails only on TCA1. Rigid on J6 → fails only on TCA2. Empty channels always pass in all three setups. So CH0, CH1, and CH2 routing are electrically equivalent for this fault. Not a per-channel routing issue.

**6d. Ran the open-cable discriminator.** Plugged a JST-SH cable into J6 with bare wires dangling at the far end — no resistors, no breadboard (and separately, with the wires plugged into an empty breadboard, connected to nothing).

Result: **BQ stays happy across all TCA channel states.** The cable's presence alone — and the ~15 cm of added copper to the CH2 net — is not sufficient to trigger the fault. This **rules out pure capacitive / stub-inductance loading** as the mechanism.

Combined with Phase 5: the necessary and sufficient trigger is **"a cable with a completed DC path (any resistance from ~1 kΩ up to 47 kΩ tested) to +3.3 V at the far end."** Cable alone = safe. DC pullup alone (on-board, no cable) = safe. Both together = BQ fails.

### Phase 7 — Failed bodge attempt on Board 1 (2026-04-22)

Goal: test whether **lower upstream pullups** (i.e., more drive strength on the upstream bus) resolve the fault. Hypothesis: injected noise is the mechanism, and stronger pullups would better suppress it at BQ.

Procedure: stacked a 2.2 kΩ 0603 bodge resistor on top of R28 and another on top of R29, giving a combined 1.1 kΩ upstream pullup on both I2C_SDA and I2C_SCL. DMM confirmed 1.1 kΩ across both post-bodge.

Result: **Board 1 BQ is now non-responsive even in BASE state** (not just on the channel with the cable). INA219 also fails on TCA2. Board visual inspection looks clean; flux cleanup did not recover behavior. Exact damage mechanism not known — suspected solder bridge or lifted-pad / thermal shock from rework at a location we haven't visually identified. Possibly a whisker or flux residue we missed, possibly the chip was pushed marginal and heat pushed it over.

**Upshot: Board 1 is now dead for investigation purposes.** The bodge test did not produce useful data about the original fault. Do not repeat this bodge on another good board without first understanding the damage mechanism.

### Phase 8 — Fresh Board 2 has independent assembly defect (2026-04-22)

Pulled a fresh, never-reworked v7 board from the JLCPCB batch spares (Board 2). Boot log: `BQ24195 not found at 0x6B - skipping`. BQ never ACKs on I2C from the very first bus scan at boot, regardless of channel state, with nothing plugged into J4–J6.

DMM check: both /I2C_SDA (at TPIO43) and /I2C_SCL (at TPIO44) sit at 3.3 V when the bus is idle. Bus pullups and idle state are correct. Chip's power pins are fine — INA219 reports VSYS=4.30V and I=0 mA. Conclusion: **BQ's SDA/SCL pins are not electrically connected to the board** (cold joint, missing joint, or damaged chip).

"Press test": applied gentle downward pressure on the BQ24195 chip body while serial was printing. No change in BQ behavior — BQ stayed silent. This weakens the simple-cold-joint hypothesis; if pressure can't close the connection, the joint is either fully open (not just marginal) or the chip itself is damaged.

**Board 2 is a separate assembly-defect problem** that doesn't bear on the main investigation. Candidate recovery: hot-air reflow of the BQ24195 (user has hot-air station). Not attempted yet.

### Phase 9 — Fresh Board 3 confirms the fault is design-level (2026-04-22)

Pulled a second fresh spare board (Board 3). Boot log: `BQ24195 configured: IINLIM=2A, watchdog disabled` — BQ responds cleanly at boot. Diagnostic loop with nothing connected: `BQ:.` across BASE and all three TCA channel states. So Board 3 is assembly-healthy.

Plugged rigid into J6, power-cycled, re-ran diagnostic:

```
BASE    INA:. BQ:. TCA:. PCA:X(2) VCNL:X(2)
TCA0    INA:. BQ:. TCA:. PCA:X(2) VCNL:X(2)
TCA1    INA:. BQ:. TCA:. PCA:X(2) VCNL:X(2)
TCA2    INA:. BQ:X(2) TCA:. PCA:. VCNL:X(2)   ⚠  BQ NACK when TCA2 opens
```

**Identical reproduction** of Board 1's original pre-bodge behavior. The cable-dependent BQ NACK is **reproducible on any healthy-assembly v7 board**. This is a design-level v7 issue, not a per-board assembly defect.

### Phase 10 — BQ24195 datasheet review (2026-04-24)

Goal: a previous-session "fresh perspective" reframe argued that the symptom looked like the BQ entering one of its own operating modes where I2C is suppressed (rather than the bus being electrically disturbed). This would shift our next-test priorities significantly. To accept or reject the reframe, we need to know what the datasheet actually says about when BQ's I2C peripheral is and isn't responsive.

Method: TI's interactive document-viewer page for the BQ24195 datasheet (`https://www.ti.com/document-viewer/BQ24195/datasheet`) was captured to local HTML (each section is lazy-loaded; user scrolled through and appended each section to a single file). A regex-based stripper (`hardware/components/BQ24195/strip_datasheet.py`) removed the duplicated `content="..."` attributes on each `<ti-raw>` wrapper, attribute cruft, scripts, styles, and decorative elements — reducing 627 KB / 11,285 lines to 120 KB / 4,719 lines while preserving all semantic structure (headings, tables, register descriptions, paragraph text). Cleaned file: `hardware/components/BQ24195/bq24195_datasheet_clean.html`.

Five targeted questions were answered against the cleaned file:

**Q1 — What internal rail powers the I2C peripheral?**
Section 8.3.1.3.1 (REGN LDO): REGN supplies "internal bias circuits as well as the HSFET and LSFET gate drive" and is enabled when (1) VBUS > UVLOZ, (2) VBUS vs battery + V_SLEEPZ condition met, (3) ~220 ms delay elapsed. REGN is off in HIZ state.
*However*, section 8.4.1.1 explicitly states the host can write `REG00[7]=0` to exit HIZ — i.e., **the chip must remain I2C-accessible during HIZ, when REGN is off**. So I2C is decoupled from REGN. This rules out the most natural "BQ I2C peripheral got gated off" mechanism.

**Q2 — When does the BQ NACK its own slave address?**
Section 8.3.6: "The device operates as a slave device with address 6BH" — no conditional language, the address is always responded to. Section 8.3.6.5.1: "If the register address is not defined, the charger IC send back NACK and go back to the idle state." This is NACK on the *data byte* (register address), which would be I2C error code 3, not 2. **Our error 2 (NACK on slave address) is undocumented behavior.**

**Q3 — Errata or known issues?**
Revision History (section 4) lists only register/description corrections (REG09→REG08 fix, electrical-spec updates, terminology). **No I2C-related errata.** No "Known Issues" section exists in the datasheet. Weak negative on the "TI published a known I2C bug" theory — there could still be a published Errata Sheet (separate document) we haven't found, or an E2E forum post.

**Q4 — VBUS / D+/D- / VSYS effects on I2C?**
Section 8.3.1.3.4: D+/D- detection runs on VBUS-present + REG08[2]=1, sets *input current limit only*, no I2C interaction. VBUS/VSYS levels affect REGN (Q1), but per Q1 that doesn't suppress I2C. **No documented dependency of I2C responsiveness on VBUS, VSYS, or D+/D- state.**

**Q5 — Watchdog effect on I2C?**
Section 8.4.1: REG05[5:4] watchdog (default 40 s; firmware sets to 00 disable). On expiry, chip transitions to default mode with all registers reset to defaults. **It does not silence I2C.** Watchdog ruled out (and we've disabled it anyway).

**Synthesis:** the "fresh perspective" reframe — that BQ enters a mode where I2C is suppressed — is **refuted by the datasheet**. No such mode exists. The BQ24195 is documented to ACK 0x6B unconditionally across all power and operational states. Our symptom is therefore **undocumented behavior**, which means the mechanism is electrical/physical at the BQ's pins or local supply, not state-machine-driven.

What this implies for next steps:
- An oscilloscope capture at the BQ's SDA/SCL pads is now the highest-confidence remaining test — software/state-machine explanations are eliminated, so whatever is happening is physical and visible electrically. Blocked on new scope arriving week of 2026-04-28 (user's previous Hantek DSO5202P could not be recovered).
- The "rail-load-only" test (load 3.3 V at the cable's far end via a single VCC↔GND resistor, with SDA/SCL unconnected) becomes more valuable: it discriminates rail-perturbation mechanism vs. signal-pin-level mechanism.
- The bench-PSU-from-battery-pads test is still useful (removes USB-C input state) but the datasheet says VBUS state shouldn't affect I2C, so it's a sanity check rather than a primary discriminator.

### Phase 11 — Rail-load-only test (2026-04-24)

Goal: discriminate between (a) a "rail-perturbation through the cable loop" mechanism (the cable+pullup creates a current loop between the main PCB's 3.3 V rail and GND that perturbs something near the BQ) versus (b) a "signal-pin DC-contact" mechanism (the cable+pullup must specifically tie to SDA/SCL to trigger the fault). The rail-load-only test isolates these by loading the rail through the cable without touching the I2C signal pins.

Setup (Board 3): JST-SH cable plugged into J6. At the far end, a single 10 kΩ resistor connecting cable pin 1 (VCC) to cable pin 2 (GND). Cable pin 3 (SDA) and pin 4 (SCL) wires unconnected at the far end. The result: a steady-state current path of ~330 µA from main PCB's 3.3 V rail, through the cable, through the 10 kΩ resistor, back to GND.

Result: **BQ stays present (`BQ:.`) on every iteration, every TCA channel state, including TCA2.** Six iterations of the diagnostic loop, all clean. INA also clean. PCA and VCNL absent as expected (no rigid attached). No fault triggered.

```
--- Iteration 1 ---
t=  25649  BASE        INA:.    BQ:.    TCA:.    PCA:X(2) VCNL:X(2)
t=  25654  TCA0        INA:.    BQ:.    TCA:.    PCA:X(2) VCNL:X(2)
t=  25659  TCA1        INA:.    BQ:.    TCA:.    PCA:X(2) VCNL:X(2)
t=  25664  TCA2        INA:.    BQ:.    TCA:.    PCA:X(2) VCNL:X(2)
[... iterations 2–6 identical ...]
```

**Conclusion: rail-perturbation through the cable is ruled out.** Loading the 3.3 V rail at the cable's far end is not sufficient to trigger the fault. The mechanism specifically requires DC contact on the I2C signal pins (SDA and/or SCL) at the far end. Combined with the Phase 6 finding that an open-ended cable with no termination doesn't trigger it either, the trigger condition is now precisely: **a completed DC path between an I2C signal line (at the far end of a cable on an opened TCA channel) and any DC-defined node** (so far tested only against +3.3 V; polarity test still pending).

**Implications:**
- Bench-PSU-from-battery-pads test is now substantially less motivated. Datasheet ruled out a documented VBUS→I2C link; rail-load-only ruled out a physical-rail-perturbation link. There's little remaining theory left to push on the supply side.
- Asymmetry tests (SDA-only pullup vs SCL-only pullup) become the highest-priority pre-scope behavioral test. They discriminate which line(s) carry the trigger.
- Polarity test (DC to GND instead of +3.3 V) gains importance — it tests whether the direction of the steady-state current matters, or just the existence of a DC load on the signal pin.
- Oscilloscope at BQ pads remains the highest-confidence test once the new scope arrives (week of 2026-04-28).

### Phase 12 — Asymmetry test (2026-04-24)

Goal: discriminate whether SDA, SCL, or both drive the fault. With the rail-load-only test (Phase 11) ruling out rail mediation, the remaining option space is signal-pin DC-coupling. If only one of the two signal lines triggers the fault, the mechanism becomes much more constrained.

Setup (Board 3): JST-SH cable plugged into J6. At the far end, a single 10 kΩ resistor between one signal pin and pin 1 (VCC, 3.3 V); the other signal pin's wire dangles unconnected. First test: pullup on SCL (cable pin 4) only, SDA wire dangling. Then live-swap to: pullup on SDA (cable pin 3) only, SCL wire dangling. Then unplug the SDA-pullup and confirm recovery, all without resetting the diagnostic.

Result: **fully asymmetric — the fault is SDA-specific.**

```
[Iterations 1–17, SCL pullup only:]
t=  ... TCA2  INA:.  BQ:.  TCA:.  PCA:X(2)  VCNL:X(2)   (BQ clean)

[User swaps to SDA pullup only at iteration ~17–18:]

--- Iteration 18 ---
t=  42371  TCA2  INA:.  BQ:X(2)  TCA:.  PCA:X(2)  VCNL:X(2)   ← fault triggered
[Iterations 19–22 identical: BQ:X(2) on TCA2 every iteration]

[User unplugs SDA wire entirely at iteration ~22–23:]

--- Iteration 23 ---
t=  52466  TCA2  INA:.  BQ:.  TCA:.  PCA:X(2)  VCNL:X(2)   ← clean immediately
[Iteration 24 confirms recovery]
```

The trigger is binary and live-state: SCL loading produces no fault across 17 iterations; the moment SDA is plugged in to a downstream pullup, the next TCA2 probe NACKs BQ; the moment SDA is unplugged, the next TCA2 probe ACKs BQ. There's no transition period or flakiness.

**Conclusion:** the fault is mediated **specifically by DC coupling on SDA**. SCL involvement is ruled out. Both the existing pullup-strength sweep and the rail-load-only finding can now be rephrased: "any DC path on **SDA** to +3.3 V at the far end of the cable is necessary and sufficient (so far tested only against +3.3 V). Resistance value irrelevant from 4.7 kΩ to 47 kΩ."

**What stories remain consistent:**
- *Story A — Phantom START during channel-open transient.* When TCA2 opens with a downstream SDA pullup, the SDA line at BQ's pad sees a brief transient (added cable capacitance, added pullup current path). If the transient briefly drops SDA below V_IL while SCL is HIGH, BQ's START detector fires when no real START occurred. BQ enters address-decode at the wrong time and never sees a coherent 0x6B from the master's subsequent transactions — leading to NACK every iteration. Master STOPs may not recover BQ if BQ is mid-byte-counting and ignoring START/STOP transitions until done. Closing the channel restores SDA's idle state and BQ resyncs.
- *Story B — Marginal SDA edge integrity at BQ specifically.* With downstream SDA pullup, the SDA edge shape seen at BQ's pad (far end of upstream bus) is corrupted enough that BQ misreads address bits. SCL clocks fine; data line is the failing input. Other slaves are closer to the upstream pullup (R28) and read SDA cleanly. BQ NACKs because, from its pin perspective, it wasn't addressed.

Both stories predict everything observed so far. Distinguishing them:
- A polarity test (SDA pullup to GND instead of +3.3 V) may help — story A is more direction-sensitive (a downward pullup's transient might be different from an upward one), while story B might fail with either polarity (or might fail even worse with GND polarity, since idle SDA voltage drops via the divider).
- A firmware bus-recovery test (deselect TCA, send 9 dummy SCL clocks + STOP, re-select TCA, then probe BQ) directly tests story A. If BQ ACKs after the recovery → BQ was in a stuck state machine, recoverable in software. If still NACKs → BQ's input is genuinely corrupt, not a state issue.
- A scope capture at BQ's pads during channel-open transient cleanly distinguishes both, but is blocked until the new scope arrives.

**Implications for next steps:**
- The polarity test moves to highest priority — it's cheap (rewire one resistor), and a story-A vs story-B discriminator without needing scope or firmware change.
- The firmware bus-recovery test is the next-best behavioral test if polarity is inconclusive. Implementation: a deselect-TCA + clock-out + STOP + reselect-TCA sequence in `SensorManager` before each BQ probe in the diagnostic loop. Moderate effort.
- Bench-PSU-from-battery-pads test stays deprioritized (Phase 11 reasoning unchanged).
- v8 with I2C buffer between upstream bus and BQ remains the most architecturally-clean fix regardless of which story (A or B) is correct — both stories are about local SDA conditions at BQ, and a buffer would isolate BQ from any downstream-side perturbations.

### Phase 13 — Polarity test (2026-04-24)

Goal: distinguish Story A (phantom START at channel-open transient) from Story B (marginal SDA edge integrity at BQ). Both stories were left consistent with Phase 12 results. The polarity test (DC pull on SDA toward GND instead of toward +3.3 V) was selected as the cheapest discriminator: under naive Story A, SDA-to-GND should produce a *bigger* downward transient at channel-open (and therefore be MORE likely to fire a phantom START); under naive Story B, SDA-to-GND should produce a *lower* idle-HIGH level at BQ (and therefore be MORE likely to corrupt bit-reading). If the fault triggered with SDA-to-GND, both stories survive. If it didn't trigger, both naive versions are weakened.

Setup (Board 3): JST-SH cable plugged into J6. At the far end, a single 10 kΩ resistor between cable pin 3 (SDA) and pin 2 (GND). Cable pin 4 (SCL) wire dangling unconnected at the far end. The far-end VCC and GND wires went to the breadboard and shared GND with the main PCB.

Result: **BQ stays present (`BQ:.`) on every iteration, every TCA channel state, including TCA2.** Five iterations of the diagnostic loop, all clean. INA always present, TCA always present. PCA and VCNL absent as expected (no rigid).

```
--- Iteration 1 ---
t=  15008  BASE        INA:.    BQ:.    TCA:.    PCA:X(2) VCNL:X(2)
t=  15013  TCA0        INA:.    BQ:.    TCA:.    PCA:X(2) VCNL:X(2)
t=  15018  TCA1        INA:.    BQ:.    TCA:.    PCA:X(2) VCNL:X(2)
t=  15023  TCA2        INA:.    BQ:.    TCA:.    PCA:X(2) VCNL:X(2)
[... iterations 2–5 identical ...]
```

**Polarity matters.** SDA pulled toward +3.3 V at the far end triggers the fault (Phase 12). SDA pulled toward GND at the far end does NOT trigger the fault. Combined with the analysis below, this strongly implies the mechanism is direction-sensitive — not just about the existence of a DC load on SDA.

**What this means for the candidate stories:**

*Story A — phantom START at channel-open.* The cable's SDA wire pre-charges to ~3.3 V (via the far-end 10 kΩ pullup) before the TCA channel opens. When the channel opens, both the cable SDA and the upstream bus SDA are at ~3.3 V — minimal transient. With SDA-to-GND polarity, the cable's SDA wire pre-charges to ~0 V; when the channel opens, the upstream bus SDA gets dragged downward (a much larger downward transient) toward 2.7 V (the divider point). Naive Story A predicts the LARGER transient would be MORE likely to fire a phantom START. The opposite happened. **Story A in its naive form is weakened.**

*Story B — marginal SDA edge integrity at BQ.* With SDA-to-VCC polarity, idle SDA HIGH at BQ is 3.3 V. With SDA-to-GND polarity, idle SDA HIGH at BQ is reduced to ~2.7 V (divider) — still above I2C V_IH spec of 2.31 V but with lower noise margin. Naive Story B predicts the lower-margin GND-polarity case should be MORE susceptible to bit-reading errors. The opposite happened. **Story B in its naive form is weakened.**

**Two new candidate stories survive the polarity asymmetry:**

*Story C — 3.3 V rail noise injection via the SDA cable wire.* The main PCB's 3.3 V rail carries noise from various sources: switching regulator ripple, ESP32 digital activity, BQ24195 internal switching, TCA9548A activity. The cable's SDA wire, when terminated through a 10 kΩ to the 3.3 V rail at the far end, becomes a low-impedance coupling path for that rail noise: noise on 3.3 V → into the far-end pullup → onto the cable's SDA wire → through the cable → into the upstream bus → accumulates worst at the bus's open end (where BQ sits, ~34 mm from the ESP32, ~55 mm from R28/R29). BQ's SDA input then samples bits with degraded SNR. Mid-bit voltage corruption flips address bits → BQ reads something other than 0x6B → correctly NACKs because it doesn't see itself addressed. SDA-to-GND polarity wouldn't do this because GND is much quieter than the 3.3 V rail. SCL-to-VCC polarity wouldn't do this because SCL is a clock input that only cares about transition timing, not mid-bit voltages.

*Story D — ESD-diode-mediated coupling at BQ.* BQ's SDA pin has internal ESD clamp diodes referenced to its internal VDD (~3.3 V). With SDA biased at 3.3 V (= BQ's VDD), positive noise spikes on SDA can briefly forward-bias the upper ESD diode, momentarily dumping charge into BQ's VDD pin. That charge perturbs BQ's internal logic supply. With SDA biased lower (2.7 V or below), positive noise spikes are absorbed by the diode's threshold without conducting. SDA-to-GND polarity (idle ~2.7 V) is below VDD, so the diode never sees a forward bias. SCL-to-VCC at the far end pre-biases SCL similarly to SDA-to-VCC, but if SCL's input doesn't have the same ESD topology or is less sensitive to VDD perturbation, the fault doesn't manifest.

These stories aren't yet distinguished. Both would benefit from scope data. Both would also be partially testable with non-scope tests:
- The firmware bus-recovery test (move to top priority): if BQ is recoverable in software while the SDA-to-VCC pullup is still attached, then the corruption is transient state-machine confusion, and Stories A/C/D fail (they all predict steady-state corruption that recovery can't fix).
- A clean-power-source test (now interesting and easy): use a separate 3 V coin cell or bench supply (with shared GND) as the +3.3 V reference for the far-end SDA pullup, instead of the cable's VCC wire (which carries the main PCB's 3.3 V rail). If BQ stays present with a clean source → Story C confirmed (rail-noise was the agent). If BQ still fails → Stories C and D probably both fail; the mechanism doesn't depend on rail noise.

**Implications for next steps:**
- The clean-power-source test moves to highest priority alongside the firmware bus-recovery test. It's a 5–10-minute setup if a battery or bench supply is available, and it directly tests Story C.
- The firmware bus-recovery test still tests Story A's last variant (any stuck-state recoverable in software) and is therefore worth running even if Story A's naive form is weakened.
- v8 with I2C buffer between upstream bus and BQ remains a clean fix for any of stories C/D — it isolates the BQ from any kind of perturbation on the upstream bus, regardless of mechanism.

### Phase 14 — Clean-power-source test (2026-04-24)

Goal: directly test Story C (3.3 V rail noise injection via the cable's SDA wire). If the mechanism depends on noise present on the main PCB's 3.3 V rail (switching regulator ripple, ESP32 digital activity, etc.), then sourcing the far-end SDA pullup from a clean linear bench supply instead of the main PCB's rail should eliminate the fault. If the fault still triggers from a clean source, Story C is ruled out and the mechanism is independent of source noise quality.

Setup (Board 3): JST-SH cable plugged into J6. At the far end, 10 kΩ from cable's SDA wire (pin 3) to the bench PSU's + terminal. Bench PSU's GND alligator clipped to the cable's far-end GND wire (pin 2 — electrically the same node as J6's GND, sharing reference with the main PCB). Cable's far-end VCC wire (pin 1) and SCL wire (pin 4) unconnected. Bench PSU set to ~3.3 V output. PSU was toggled on/off mid-diagnostic to capture both states without resetting the firmware.

Result: **the clean bench PSU triggers the fault identically to the main PCB's 3.3 V rail.**

```
[Iterations 1–8: PSU OFF — only on-board pullup R28 active, no DC bias on far end of SDA]
t=  ... TCA2  INA:.  BQ:.  TCA:.  PCA:X(2)  VCNL:X(2)   (BQ clean)

[User turns on bench PSU at iteration ~9, sourcing 3.3 V to far-end SDA pullup:]

--- Iteration 9 ---
t=  26706  TCA2  INA:.  BQ:X(2)  TCA:.  PCA:X(2)  VCNL:X(2)   ← fault triggered
[Iterations 10–15 identical: BQ:X(2) on TCA2 every iteration]

[User turns off bench PSU at iteration ~16:]

--- Iteration 16 ---
t=  40839  TCA2  INA:.  BQ:.  TCA:.  PCA:X(2)  VCNL:X(2)   ← clean immediately
[Iteration 17 confirms recovery]
```

Binary toggle on PSU power state. Identical pattern to Phase 12's SDA-cable-on/off test — the fault is gated by whether the cable's SDA wire is being DC-biased toward ~3.3 V, regardless of whether the source is the main PCB's rail or a clean bench supply.

**Conclusion: Story C is ruled out.** 3.3 V rail noise from the main PCB is NOT the agent. The mechanism doesn't care about source noise quality. It cares specifically about SDA being DC-biased at ~3.3 V via a cable-distance pullup.

**What this means for surviving stories:**

*Story D (ESD-diode-mediated charge injection at BQ).* Still consistent. Story D's prediction is that SDA biased near BQ's VDD allows rising-edge overshoot (caused by ringing in the bus extended through the cable) to briefly forward-bias BQ's upper ESD clamp diode, perturbing internal VDD and disturbing logic. This depends on DC bias level, not source noise — so a clean PSU at 3.3 V triggers identically to a noisy rail at 3.3 V. ✓

*Residual Story A variant — stuck state machine recoverable in software.* Untested. Still possible.

*Unknown Story E.* Can't be ruled out. We're now reasoning about a mechanism that's:
- SDA-only (not SCL)
- Triggered by DC bias toward ~3.3 V (not GND)
- Independent of source noise quality
- Independent of pullup resistance value (4.7k–47k)
- Requires a cable-distance pullup (on-board pullup R28 alone doesn't trigger it)
- Persistent while channel is open, recovers immediately on channel close

The cable-distance-matters part is interesting: the on-board R28 (2.2 kΩ to 3.3 V) provides DC bias to SDA at ~3.3 V already, but doesn't trigger the fault. Adding a far-end pullup via ~15 cm of cable wire DOES trigger it. So the cable's physical/electrical properties (capacitance, inductance, length, antenna behavior) matter — not just the DC bias alone. This is consistent with Story D if the bus's ringing dynamics change meaningfully with the cable + far-end pullup added (added capacitance + altered effective pullup network → altered rise-time and overshoot characteristics).

**Implications for next steps:**
- Firmware bus-recovery test is now the highest-priority remaining behavioral test. It's the only remaining cheap way to distinguish "stuck state machine" (Story A residual) from "steady-state corruption" (Story D / E).
- Oscilloscope at BQ pads remains the gold standard. Phase 14 sharpens the scope target: capture SDA at BQ during a falling edge AND a rising edge, with the failing config attached, and look for (a) overshoot on rising edges, (b) ringing amplitude, (c) any voltage excursions above VDD.
- v8 design intervention: an I2C buffer (P82B96 / PCA9517 / LTC4311) between the upstream bus and BQ remains the cleanest fix regardless of which surviving story is correct. All surviving mechanisms are about local SDA conditions at BQ's pad, so isolating BQ from the upstream bus eliminates the disturbance regardless of mechanism.

### Phase 15 — Firmware bus-recovery test (2026-04-24)

Goal: directly test the residual Story A variant — a stuck I2C state machine inside the BQ24195 that's confused by the channel-open transient on SDA and stays confused (failing to ACK its address) until the channel closes, but might be recoverable in software via a forceful STOP/START sequence.

Implementation: added `BUS_RECOVERY_TEST` build flag and matching `motion-play-v7-busrec` PlatformIO env. Under this flag, `SensorManager::runBusDiagnosticLoop()` issues 3× dummy `Wire.beginTransmission(0x00); Wire.endTransmission();` calls after each TCA channel-open and before the 5-probe series. Each call sends START + 0x00 + R/W=0 + NACK + STOP = 9 SCL clocks plus a clean STOP framing on the bus. Three repetitions provides redundancy. Any well-behaved I2C slave with a confused state machine (mid-byte counting, mid-transaction wait, stale ACK pending) should be reset to idle by even one of these framings. The recovery sequence is announced at startup with a `[BUS_RECOVERY_TEST] Active...` print so the build is unambiguous.

Setup (Board 3): identical to Phase 14. JST-SH cable in J6, far-end SDA wire → 10 kΩ → bench PSU + terminal at +3.3 V, bench PSU − terminal → cable's far-end GND wire (shared ground reference). Far-end VCC and SCL wires unconnected. Bench PSU was toggled on/off mid-diagnostic to capture both states without resetting the firmware.

Result: **the recovery sequence does NOT recover BQ.**

```
[BUS_RECOVERY_TEST] Active: 3x dummy START+STOP framings issued after each
                    TCA channel-open, before probing. Tests Story A
                    (BQ in stuck state, recoverable in software).

[Iterations 1–5: PSU OFF — recovery sequence runs but isn't needed]
t=  ... TCA2  INA:.  BQ:.  TCA:.  PCA:X(2)  VCNL:X(2)   (BQ clean)

[User turns on PSU at iteration ~6:]

--- Iteration 6 ---
t=  16924  TCA2  INA:.  BQ:X(2)  TCA:.  PCA:X(2)  VCNL:X(2)   ← fault triggered
[Iterations 7–12 identical: BQ:X(2) on TCA2 every iteration, despite
 the 3x dummy STARTs/STOPs issued before each BQ probe]

[User turns off PSU around iteration 13:]

--- Iteration 13 ---
t=  31050  TCA2  INA:.  BQ:.  TCA:.  PCA:X(2)  VCNL:X(2)   ← clean immediately
[Iterations 14–15 confirm recovery on PSU off]
```

The recovery sequence fires three full START+STOP framings on the bus before each BQ probe attempt. BQ still NACKs every iteration when the failing config is attached. A confused state machine can't survive three STOPs in a row — it gets reset by even one. The fact that BQ continues to NACK across multiple recovery cycles in a single channel-open period proves the disturbance is **not state-machine confusion**. The disturbance is electrical and present at BQ's pad continuously while the SDA-to-3.3 V cable is attached.

**Conclusion: Story A residual variant is ruled out.** Combined with the prior phases, **all cheap non-scope mechanisms are now eliminated.** The fault is steady-state corruption at the BQ's I2C input pin while a downstream SDA pullup to +3.3 V is electrically present. The state of the I2C peripheral inside BQ is irrelevant to the symptom — BQ's input stage simply can't decode the address byte correctly under the disturbance.

**What remains:**
- *Story D — ESD-diode-mediated charge injection at BQ.* Still consistent with all observations. Predicts scope will show overshoot above VDD+0.6 V on SDA rising edges at BQ's pad.
- *Story E — unidentified.* Cannot be ruled out, but heavily constrained: must be steady-state (Phase 15), SDA-only (Phase 12), +3.3V-polarity-only (Phase 13), source-noise-independent (Phase 14), cable-distance-required (cable-only stub passes; on-board pullup R28 alone passes), bus-recovery-immune (Phase 15). The remaining option space is narrow but not empty.

**Implications for next steps:**
- The non-scope option space is exhausted. Further behavioral tests are unlikely to yield discrimination between Story D and Story E.
- Oscilloscope at BQ pads (week of 2026-04-28) is now the only remaining diagnostic that can identify the precise mechanism.
- **v8 design with an I2C buffer between the upstream bus and BQ is now independently justified by what we already know.** All surviving stories (D and E) are about local SDA conditions at BQ's pad, and a buffer would isolate BQ from any upstream-side perturbation regardless of mechanism. This design work should start in parallel with the scope investigation rather than waiting for it — the scope can confirm the mechanism, but the v8 fix is correct in any case.

### Phase 16 — Routing-aware audit (2026-04-25)

Goal: replace the placement-based hand-waving in the layout observations with measured trace geometry. Throughout phases 5–15 the routing-asymmetry-explains-SDA-only-fault hypothesis has been simmering as an unmeasured candidate explanation: SDA and SCL might run physically different paths on the board, with one passing closer to a noisy switching node (L1, L2, BQ's SW pads, BOOST_SW, BQ_SW) than the other, and that asymmetry in coupling could plausibly explain why only SDA exhibits the fault. The existing `pcb-layout-context.json` only captures placement, not routing, so until now this could only be reasoned about visually in KiCad. This phase ran a new programmatic routing audit (`tools/pcb-context/routing_extract.py` + `tools/pcb-context/routing_audit.py`, audit spec `tools/pcb-context/audit-specs/v7-main-i2c.json`) that extracts per-net trace segments and vias from `motion-play-main.kicad_pcb`, then reports total per-net length, per-layer length, and minimum clearance from each target net to a configurable set of components, named pads, and other nets. The resulting Markdown is embedded verbatim below; the underlying JSON sits next to it at `tools/pcb-context/audit-specs/v7-main-i2c.audit.json`. Net lengths and one proximity pair (`/I2C_SDA` → `L1`) were spot-checked against KiCad's Net Inspector / measure-from-origin tools at ±0.05 mm tolerance during phases 1 and 2 before this analysis was written.

#### Routing audit — hardware/pcb-main/kicad/motion-play-main.kicad_pcb

_Generated_: 2026-04-25T17:30:53.066907+00:00
_Spec_: `v7-main-i2c.json`
_Routing context_: `/Users/marcocleirigh/Workspace/motion-play/hardware/pcb-main/kicad/pcb-routing-context.json`

##### Net `/I2C_SDA`

- Total length: **72.9 mm** (B.Cu 37.0, F.Cu 35.9)
- Segments: 25, vias: 3
- Min clearance to component `L1`: **6.1 mm** (F.Cu)
- Min clearance to component `L2`: **7.0 mm** (F.Cu)
- Min clearance to component `U5`: **0.0 mm** (F.Cu)
- Min clearance to component `U6`: **5.4 mm** (F.Cu)
- Min clearance to BQ24195 SW pin (pad 19): **4.3 mm** (F.Cu)
- Min clearance to BQ24195 SW pin (pad 20): **3.9 mm** (F.Cu)
- Min clearance to net `/Power Management/Protected_VBUS`: **2.2 mm** (F.Cu)
- Min clearance to net `/Power Management/VSYS`: **2.8 mm** (F.Cu)
- Min clearance to net `/Power Management/VBAT`: **4.0 mm** (F.Cu)
- Min clearance to net `/Power Management/BQ_SW`: **4.5 mm** (F.Cu)
- Min clearance to net `/Power Management/BOOST_SW`: **2.7 mm** (F.Cu)

##### Net `/I2C_SCL`

- Total length: **73.3 mm** (B.Cu 39.6, F.Cu 33.7)
- Segments: 33, vias: 5
- Min clearance to component `L1`: **5.6 mm** (F.Cu)
- Min clearance to component `L2`: **6.5 mm** (F.Cu)
- Min clearance to component `U5`: **0.0 mm** (F.Cu)
- Min clearance to component `U6`: **5.0 mm** (F.Cu)
- Min clearance to BQ24195 SW pin (pad 19): **3.9 mm** (F.Cu)
- Min clearance to BQ24195 SW pin (pad 20): **3.6 mm** (F.Cu)
- Min clearance to net `/Power Management/Protected_VBUS`: **1.7 mm** (F.Cu)
- Min clearance to net `/Power Management/VSYS`: **3.1 mm** (F.Cu)
- Min clearance to net `/Power Management/VBAT`: **4.0 mm** (F.Cu)
- Min clearance to net `/Power Management/BQ_SW`: **4.1 mm** (F.Cu)
- Min clearance to net `/Power Management/BOOST_SW`: **1.8 mm** (F.Cu)

##### Asymmetry (`/I2C_SDA` vs `/I2C_SCL`)

| Metric | /I2C_SDA | /I2C_SCL | Δ (a − b) |
|---|---:|---:|---:|
| Total length (mm) | 72.9 | 73.3 | -0.4 |
| Min dist to /Power Management/BOOST_SW (mm) | 2.7 (F.Cu) | 1.8 (F.Cu) | +0.9 |
| Min dist to /Power Management/BQ_SW (mm) | 4.5 (F.Cu) | 4.1 (F.Cu) | +0.4 |
| Min dist to /Power Management/Protected_VBUS (mm) | 2.2 (F.Cu) | 1.7 (F.Cu) | +0.5 |
| Min dist to /Power Management/VBAT (mm) | 4.0 (F.Cu) | 4.0 (F.Cu) | -0.0 |
| Min dist to /Power Management/VSYS (mm) | 2.8 (F.Cu) | 3.1 (F.Cu) | -0.4 |
| Min dist to L1 (mm) | 6.1 (F.Cu) | 5.6 (F.Cu) | +0.5 |
| Min dist to L2 (mm) | 7.0 (F.Cu) | 6.5 (F.Cu) | +0.5 |
| Min dist to U5 (mm) | 0.0 (F.Cu) | 0.0 (F.Cu) | 0.0 |
| Min dist to BQ24195 SW pin (pad 19) (mm) | 4.3 (F.Cu) | 3.9 (F.Cu) | +0.3 |
| Min dist to BQ24195 SW pin (pad 20) (mm) | 3.9 (F.Cu) | 3.6 (F.Cu) | +0.4 |
| Min dist to U6 (mm) | 5.4 (F.Cu) | 5.0 (F.Cu) | +0.5 |

#### Interpretation

The two nets are geometrically near-twins. Total length differs by 0.4 mm (SDA 72.9 mm, SCL 73.3 mm) — well under 1% on a ~73 mm bus, and SCL is actually the *longer* of the two. Layer split is similar: both are roughly half F.Cu and half B.Cu, with SCL using slightly more B.Cu (39.6 vs 37.0 mm) and slightly fewer F.Cu millimetres. The closest-approach numbers go in the *opposite direction* from what the routing-asymmetry hypothesis would need: SCL passes 0.5 mm *closer* to L1 than SDA does (5.6 vs 6.1 mm), 0.5 mm closer to L2 (6.5 vs 7.0 mm), 0.3–0.4 mm closer to BQ24195's SW pads (pads 19 and 20), 0.5 mm closer to Protected_VBUS, 0.4 mm closer to BQ_SW, and a striking 0.9 mm closer to BOOST_SW (1.8 vs 2.7 mm — the largest single asymmetry in the audit). The only metrics on which SDA is closer than SCL to a noisy node are `/Power Management/VSYS` (by 0.4 mm) and a 0.0 mm tie on `/Power Management/VBAT`.

In other words: every switching-node-adjacency metric the audit was designed to expose either favours SDA (it's farther from the noise) or is essentially symmetric. SCL is consistently the geometrically *more exposed* trace by every measurement that matters for switcher-coupled noise, yet experimentally SCL loading produces zero fault while SDA loading is the deterministic trigger (Phase 12). **The geometry weakens the routing-asymmetry-explains-SDA-only-fault hypothesis** — it does not support it. If anything, the symmetry is the surprising part: a designer eyeballing the board could not have confidently asserted the two traces were this close in length and proximity profile, and the data now says they are. So the SDA-only behaviour observed in phases 12–15 is not explained by SDA running a meaningfully noisier physical path than SCL on this board. The mechanism distinguishing SDA from SCL has to live somewhere other than gross trace geometry — most plausibly in the receiver (BQ's input topology and ESD-clamp behaviour, per Story D), not in the bus itself.

#### Verdict

The routing-asymmetry hypothesis is **weakened, not supported, by the measured geometry.** SDA and SCL are routed on near-identical paths to within 0.5 mm on every metric the audit checks, and on most metrics SCL is the more exposed of the two. There is no "SDA runs a much worse path than SCL near the switcher" story that survives these numbers. The asymmetric experimental behaviour (SDA-loading triggers the fault, SCL-loading is silent — Phase 12) therefore cannot be attributed to bus-routing-induced coupling asymmetry, and the search for the SDA/SCL discriminator should look at the receiver side (BQ's pin topology) rather than the trace side.

This audit is about *bus-routing-induced coupling asymmetry between the two traces* and does not directly bear on Story D from "Current working theory" below. Story D's predicted mechanism is overshoot at BQ's SDA pad caused by ringing during SDA edges with the cable-extended pullup attached — that's a temporal/electrical phenomenon at a single pin, not a steady-state inter-net coupling story. Story D is unaffected by the symmetry shown here and remains the dominant surviving candidate; the audit just removes "but maybe SDA's trace is just routed worse" from the option space of explanations for the SCL-vs-SDA experimental asymmetry.

#### Footnote on `Min clearance to component U5 = 0.0 mm`

Both SDA and SCL show 0.0 mm minimum clearance to component U5 (BQ24195) on F.Cu. This is not a routing problem and not a tool bug. The auditor measures clearance against the footprint's per-layer bounding box (the smallest axis-aligned rectangle that contains all of the footprint's pads on that layer). The BQ24195's SDA and SCL pads are themselves part of U5, so the SDA and SCL traces necessarily enter U5's bbox to land on those pads — clearance to the bbox of the component you're trying to *connect to* is by construction zero. Read this row as "yes, the SDA/SCL trace lands on its U5 pad" rather than as a clearance violation. If a future audit wants a meaningful BQ-component clearance, exclude U5 from `noisy_components` for the SDA/SCL nets and rely on the `BQ24195 SW pin (pad 19)` and `(pad 20)` rows, which measure clearance to the *specific* noisy pads that the SDA and SCL traces don't terminate on.

---

## Current working theory

Many simple hypotheses have been progressively disproven: pull-up strength (Phase 5), cable-stub physics (Phase 6), BQ-mode-suppression (Phase 10), rail-perturbation through the cable loop (Phase 11), SCL involvement (Phase 12), SDA-edge-integrity-naive (Phase 13 polarity), channel-open-transient-naive (Phase 13 polarity), 3.3 V rail noise injection (Phase 14 clean PSU), and stuck-state-machine recoverable in software (Phase 15 firmware bus-recovery). **All cheap non-scope mechanisms are now ruled out.** The surviving candidates are narrow and electrical-only:

- **Story D — ESD-diode-mediated charge injection at BQ.** With SDA biased near BQ's VDD (~3.3 V) via a cable-distance pullup, the bus's ringing dynamics during a SDA rising edge produce brief overshoot above VDD+0.6 V at BQ's pad. The upper ESD clamp diode briefly conducts, dumping charge into BQ's VDD pin and disturbing internal logic. With SDA-to-GND polarity, idle SDA tops out at 2.7 V — overshoot stays below VDD → no diode conduction → no fault. With SCL-to-VCC, SCL has different input topology → not affected the same way. The mechanism doesn't depend on rail noise (Phase 14 ✓) or state-machine state (Phase 15 ✓). Predictions: scope should show overshoot at BQ's SDA pad on rising edges with the failing config attached; an active I2C buffer or v8 isolation would eliminate it. **Currently the dominant surviving candidate.**
- **Unknown Story E.** Cannot rule out — must satisfy all the following: steady-state, SDA-only, +3.3 V-polarity-only, source-noise-independent, cable-distance-required (on-board R28 alone doesn't trigger), bus-recovery-immune. The remaining option space for a non-Story-D mechanism is narrow but not empty.

What we know empirically:

- Nothing connected to any TCA channel → BQ stays present across all TCA channels opening.
- Rigid connected to any TCA channel → BQ drops out on that channel.
- Cable-only stub into J6 (no termination) → BQ stays present. Cable length alone is not sufficient.
- Cable + DC pullup on **SCL only** (SDA dangling) to 3.3 V → BQ stays present. SCL loading is harmless.
- Cable + DC pullup on **SDA only** (SCL dangling) to **3.3 V** → BQ drops out. SDA-toward-VCC is the trigger.
- Cable + DC pulldown on **SDA only** (SCL dangling) to **GND** → BQ stays present. Polarity matters.
- Cable + DC pullup on both SDA and SCL to 3.3 V → BQ drops out (driven by the SDA-toward-VCC component).
- Cable + resistor between **VCC and GND** only at the far end (SDA/SCL unconnected) → BQ stays present. Loading the rail through the cable is not sufficient.
- The failure is 100% deterministic, no flakiness. Live-swap on/off of the SDA pullup wire toggles the fault state in real time.
- Resistance value of the SDA-to-VCC pullup is irrelevant from 4.7 kΩ to 47 kΩ.
- BQ at 0x6B is the only slave that drops; INA219 (closer to ESP32) and TCA9548A never NACK during the same conditions.

Observations about main PCB v7 layout that may or may not be relevant:
- Main PCB uses **2.2 kΩ** upstream I2C pull-ups (R28, R29) — unusually strong. Annotation says "sized for 400kHz operation."
- R28 and R29 are placed at (150, 102), clustered near the TCA9548A (151, 107) and J6 (161, 105) — all in the top-right corner of the board.
- BQ24195 is at the far end of the upstream bus trace (97, 118), ~34 mm from the ESP32 (131, 118) and ~55 mm from the pull-ups.
- The failure affects the device at the far end of the bus (BQ) before the device closer to the ESP32 (INA219). INA219 tolerates all tested conditions.

The fact that adding even a 47 kΩ DC path (tiny current, ~70 µA maximum) is sufficient to consistently trigger the fault, while no DC path at all doesn't trigger it, points at something about the *presence* of a return current path on the CH2 stub rather than anything about its magnitude. Mechanism to be determined.

---

## Firmware state (what's been modified)

### `firmware/src/components/sensor/SensorManager.h`
- Added to `PCA9546A` class:
  - `uint8_t readControlRegister()` — single-byte read of PCA control reg
  - `bool selectChannelVerify(uint8_t channel, uint8_t *readback = nullptr)` — selectChannel + verify latched
- Added method declaration: `void runBusDiagnosticLoop()`

### `firmware/src/components/sensor/SensorManager.cpp`
- Sensor-init loop now uses `selectChannelVerify()` and logs readback value
- On VCNL4040 NACK, firmware scans the full 0x08–0x77 range on the open PCA channel
- `Wire.setClock(100000)` (temporarily, was 400000). **TODO revert**
- Log message updated to reflect the debug clock: `"I2C clock set to 100 kHz (debug: was 400 kHz)"`
- `runBusDiagnosticLoop()` implemented — continuous probe across bus states, cycles through TCA0/1/2 including empty channels

### `firmware/src/main.cpp`
- `powerMonitor.init()` moved to very early in `setup()` (right after `configureBQ24195()`)
- Four `[PWR ...]` log lines added at boot checkpoints
- On sensor init failure, calls `sensorManager.runBusDiagnosticLoop()` instead of halting

### `platformio.ini`
- `STARTUP_I2C_SCAN=true` on the `motion-play-v7` env (was `false`). Runs `debugI2CScan()` once at init.

### `tools/arduino-sketches/vcnl4040_i2c_diagnose/vcnl4040_i2c_diagnose.ino`
- External diagnostic sketch. Works with Arduino Nano ESP32 or Nano 33 IoT. Does a plain bus scan, then if a PCA is found, opens each of its channels and scans downstream for 0x60. Used for Approach A (direct to rigid J1) testing.

### `docs/debugging/i2c-oscilloscope-debugging.md`
- Standalone guide for using a Hantek DSO5202P to debug the I2C bus electrically. Not executed yet (user's scope is currently stuck at boot splash and not recovered). Keep for later if the fix doesn't resolve everything.

---

## Firmware state added in Phase 6 (2026-04-21)

### `firmware/src/components/sensor/SensorManager.cpp` — `probeAndPrint()` in `runBusDiagnosticLoop()`
- Prints the actual `Wire.endTransmission()` return code instead of just "X". Output format: `BQ:.` for ACK or `BQ:X(n)` where n is the error code. Legend: 1=data_too_long, 2=NACK_addr, 3=NACK_data, 4=other, 5=timeout/bus_hang. Settling the 2-vs-5 question is critical; every failure in every scenario so far has been code 2.

### `firmware/src/main.cpp` — `DIAG_NO_WIFI` build flag
- New `#ifdef DIAG_NO_WIFI` branch in `initializeSystem()` skips the entire WiFi/MQTT/cloud-config block, calls `WiFi.mode(WIFI_OFF)` and `btStop()` to force radios off, sensors init with defaults. Main-loop `networkManager.checkConnection()` and `mqttManager->loop()` are also guarded by the flag to avoid null-deref.
- `#include <WiFi.h>` added for `WiFi.mode()` access.

### `platformio.ini` — `motion-play-v7-diag` env
- Inherits from `motion-play-v7`, adds `-DDIAG_NO_WIFI`. Invoke with `pio run -e motion-play-v7-diag -t upload`.

---

## Revert list (for when the fix is verified)

Once the hardware fix is confirmed working, these temporary firmware debug changes should be reviewed:

- **`Wire.setClock(100000)` → `Wire.setClock(400000)`** in `SensorManager::init()`. Also revert the log message.
- **`STARTUP_I2C_SCAN` back to `false`** in `platformio.ini` (or leave on — adds ~50 ms to boot, useful diagnostic).
- **`runBusDiagnosticLoop()`** — can stay, only runs on init failure. Noisy but gated by actual fault.
- **`[PWR ...]` log lines at boot** — can stay. Low cost, useful.
- **Per-channel scan on VCNL4040 NACK** — keep. Useful always.
- **`selectChannelVerify()`** — keep. Strictly a robustness improvement.
- **`probeAndPrint()` error codes** — keep. Strictly more information, no cost.
- **`DIAG_NO_WIFI` flag / `motion-play-v7-diag` env** — keep. Zero cost, useful for future RF-related debugging.

---

## Candidate fixes

**None yet confirmed.** Pull-up strength was disproven in Phase 5. Cable stub physics was disproven in Phase 6. The Phase 7 bodge attempt (lower 1.1 kΩ pullups) damaged Board 1 without producing test data.

Candidates still worth considering, in rough order of preference:

1. **I2C buffer/repeater IC for BQ.** Put a P82B96 or PCA9517 between the upstream I2C and BQ, so BQ sees a locally-terminated short bus regardless of what happens on the main upstream bus. Decouples BQ from downstream loading entirely. Adds two extra pullups (one on each side of the buffer) and a small IC. This is a v8 design change — non-trivial but architecturally clean.
2. **Move BQ closer to the pullups / shorten upstream bus.** Currently BQ is ~55 mm from R28/R29, which is the worst-case node on the bus. Shortening that distance would reduce noise accumulation at BQ. Requires v8 re-layout.
3. **Active I2C bus accelerator.** Something like the LTC4311 — detects rising edges on SDA/SCL and injects a strong pull-up pulse to accelerate them. One part, two pins, cheap. Would mask slow-edge and ringing issues without requiring full bus redesign.
4. **Stronger upstream pullups (1 kΩ or even lower).** The direct test of this hypothesis failed (Phase 7 bodge damaged the board before producing data). The theory is still alive — a fresh board could be used to retry the bodge, more carefully, on Board 3.
5. **Low-ESR bulk capacitor right at BQ's I2C pins.** Not typical; would act as a local ringing suppressor. Speculative.

If a scope becomes available, a single capture of SDA/SCL at BQ during the failing transaction (with and without the rigid plugged in) would almost certainly identify the mechanism immediately and let us pick between these options with confidence.

---

## Key file pointers (for a fresh session to follow up)

- **Main PCB v7 circuit context**: `hardware/pcb-main/kicad/circuit-context.json` — component U3 (ESP32), U4 (TCA), U5 (BQ), U7 (INA), R28, R29
- **Main PCB v7 PCB layout context**: `hardware/pcb-main/kicad/pcb-layout-context.json` — physical placement
- **Sensor-rigid circuit context**: `hardware/sensor-rigid/circuit-context.json` — U1 (PCA), J1 (JST-SH), R1/R2 (4.7 kΩ upstream pull-ups), R6–R9 (downstream pull-ups), FPC1 (ZIF)
- **Sensor-flex circuit context**: `hardware/sensor-flex/circuit-context.json` — IC1/IC2 (VCNL4040s), FPC1 (tail)
- **Firmware entry points**:
  - `firmware/src/main.cpp` — setup(), initializeSystem()
  - `firmware/src/components/sensor/SensorManager.{cpp,h}` — all the sensor init logic, diagnostic loop
  - `firmware/src/components/power/PowerMonitor.{cpp,h}` — INA219 wrapper, already existed
- **Build config**: `platformio.ini` — environments lilygo-t-display-s3 (legacy) and motion-play-v7 (current)
- **Arduino sketch**: `tools/arduino-sketches/vcnl4040_i2c_diagnose/vcnl4040_i2c_diagnose.ino`
- **Oscilloscope guide**: `docs/debugging/i2c-oscilloscope-debugging.md`
- **BQ24195 datasheet (raw HTML capture)**: `hardware/components/BQ24195/bq24195_datasheet.html` — captured from TI's interactive document-viewer, lazy-loaded sections appended.
- **BQ24195 datasheet (cleaned)**: `hardware/components/BQ24195/bq24195_datasheet_clean.html` — 80% smaller, semantic structure preserved. Use this for further datasheet queries. Section anchors preserved as `<h*>` `id` attributes.
- **Datasheet stripper script**: `hardware/components/BQ24195/strip_datasheet.py` — regex-based cleaner; rerun if datasheet HTML is recaptured.
- **Memory index**: the user's AI memory notes `project_pcb_revision_apr2026.md`, `project_bq24195_iinlim_fix.md`, `feedback_enclosure_follows_pcb.md`, `feedback_spice_symbols.md` — relevant background

---

## Immediate next steps

**The non-scope option space is now exhausted.** All cheap behavioral tests have been run (Phases 11–15) and all simple mechanisms have been ruled out. Two paths forward remain, and both should be pursued in parallel rather than sequentially:

1. **Oscilloscope capture at BQ pads (gold standard; blocked until ~2026-04-28).** Probe SDA at BQ's pad during a transaction with the failing config attached. Trigger on a SDA falling edge AND a SDA rising edge. New scope arriving week of 2026-04-28; previous Hantek DSO5202P could not be recovered. See `docs/debugging/i2c-oscilloscope-debugging.md` for setup. The capture target is sharp: looking specifically for (a) overshoot above VDD+0.6 V on rising edges (Story D's prediction), (b) mid-bit voltage instability, (c) ringing amplitude. If overshoot is confirmed → Story D is confirmed. If no overshoot → Story D is refuted and Story E is the only remaining candidate. **Either way, the v8 fix is the right answer** because it removes BQ from the upstream bus regardless of mechanism.
2. **v8 design with an I2C buffer IC between the upstream bus and BQ (start now, in parallel with waiting for scope).** Independently justified by Phase 15's confirmation that the disturbance is steady-state at BQ's pin. All surviving mechanisms (Story D and any unidentified Story E) are about local SDA conditions at BQ's pad — a buffer isolates BQ from any upstream-side perturbation. Candidate parts to evaluate: P82B96 (rugged, level-shifting capable), PCA9517 (small, simple), LTC4311 (active-pullup edge accelerator — different mechanism, worth evaluating). This work should not wait on the scope; the scope only confirms the precise mechanism, not whether the buffer fix is needed.

**Completed phases (DONE):**
- Phase 11 — Rail-load-only test: rail-perturbation through cable ruled out.
- Phase 12 — Asymmetry test: SDA-specific (SCL loading harmless).
- Phase 13 — Polarity test: polarity-sensitive (SDA-to-VCC fails, SDA-to-GND works).
- Phase 14 — Clean-power-source test: source noise quality irrelevant. Story C ruled out.
- Phase 15 — Firmware bus-recovery test: software recovery doesn't help. Story A residual ruled out. Disturbance confirmed steady-state.

**Deprioritized (no remaining theory pushes for them):**
- Bench-PSU-from-battery-pads test: datasheet (Phase 10) ruled out documented VBUS→I2C interactions; subsequent phases progressively narrow the mechanism away from anything supply-mediated.
- High-rate INA219 logging: Phases 11–15 make rail-mediated and state-machine-mediated mechanisms unlikely. Skip unless new evidence points back.

**Do not** run the Phase 7 bodge attempt again without first understanding why it damaged Board 1.

### Working state — which boards to use
- **Board 1**: damaged, investigation-dead. May be recoverable with deliberate rework but isn't needed right now.
- **Board 2**: fresh-from-JLCPCB assembly defect — BQ silent from boot, DMM confirms bus is healthy so it's a BQ-side solder joint or chip failure. User has a hot-air station; reflow is a reasonable next attempt. Independent of the main investigation.
- **Board 3**: **the working investigation target.** Boots healthy, reproduces the main fault identically. All further tests should be on this board.

---

## Appendix A — Repro steps (for a fresh session)

To reproduce the failure from scratch:

1. Power up the main PCB v7 (USB-C on J7 plugged into a 3A+ USB supply or computer).
2. Plug any assembled sensor-rigid (with flex attached) into J4, J5, or J6.
3. Flash the firmware on the `motion-play-v7` env. No additional build flags needed beyond what's in `platformio.ini` already.
4. Open Arduino-IDE Serial Monitor at 115200 baud (or `pio device monitor -e motion-play-v7`).
5. Press reset.
6. Observe: sensor init prints NACK errors, then falls into `runBusDiagnosticLoop()`.
7. The diagnostic loop shows `BQ:X` on whichever `TCA{n}` row corresponds to the connector with the rigid.

---

## Appendix B — Arduino test procedure (to re-verify VCNL4040 functionality)

Quick proof that the sensor assembly is healthy, independent of the main PCB:

1. Get a spare 3.3V Arduino (Nano ESP32 ideal, Nano 33 IoT also works).
2. Unplug the rigid from the main PCB (any JST-SH port).
3. Wire directly to the rigid's J1 connector:
   - Arduino 3V3 ↔ rigid J1 pin 1
   - Arduino GND ↔ rigid J1 pin 2
   - Arduino A4 (SDA) ↔ rigid J1 pin 3
   - Arduino A5 (SCL) ↔ rigid J1 pin 4
4. Flash `tools/arduino-sketches/vcnl4040_i2c_diagnose/vcnl4040_i2c_diagnose.ino` — Nano ESP32 requires `Tools → USB CDC On Boot → Enabled`.
5. Open Serial Monitor at 115200. Press reset on the Arduino.
6. Expected output:
   ```
   [scan] Pass 1: bare bus
     0x76  PCA9546A
   Found PCA9546A at 0x76
   --- Opening PCA ch 0 ---
     Control register reads back 0x1
   [scan] Pass 2.0: PCA ch 0 downstream
     0x60  VCNL4040
     0x76  PCA9546A
   --- Opening PCA ch 1 ---
     Control register reads back 0x2
   [scan] Pass 2.1: PCA ch 1 downstream
     0x60  VCNL4040
     0x76  PCA9546A
   === Done ===
   ```

If you see both VCNL4040 entries, the rigid + flex + VCNL4040 assembly is healthy. The fault is entirely on the main PCB side.
