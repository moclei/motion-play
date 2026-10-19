> **FROZEN 2026-10. Historical only. Current state: `lab/STATE.md`.** This is the legacy notebook (volume 0). Its summary sections (Fastest read, TL;DR, Current working theory, Candidate fixes, Firmware state, Revert list, Immediate next steps) and the status line below are not current. Look up a phase by heading (`grep -n "^### Phase"`) and cite it as `L-PhNN` (`L-Ph24a` = Arduino-as-master, `L-Ph24b` = Exp 1 glitch filter).

# Main PCB v7 — VCNL4040 I2C Silent Failure Investigation

> **Status as of 2026-05-02 (post Phase 24 — Story F confirmed; Experiment 1 null; Phase 25 in flight)**: Arduino-as-master test (Phase 24) **confirms Story F**: BQ ACKs a SAMD21 (Nano 33 IoT) master cleanly on the same wire where it NACKs the ESP32-S3 master, in the same failing-config cable load. Mechanism is unambiguously in the ESP32-S3 master peripheral itself — not in BQ's input, not in the bus, not in cable parasitics independent of the master. Story H (BQ-side input feature) refuted. Threshold stories at the BQ pad already refuted (D-revised by Phase 20, G-revised by Phase 23). Phase 24 Experiment 1 (`i2c_filter_enable(I2C_NUM_0, 7)` — turn on the I2C controller's digital deglitcher that the legacy IDF v4.4 driver leaves off by default) returned a null result: BQ NACK pattern on TCA2 byte-identical to baseline. Refutes "sub-µs glitches at the I2C controller's input" as the missing knob; the master is emitting something on the *output* side, or the disturbance is at a path the I2C controller's filter doesn't sit on. **Phase 25 in flight**: bundles Experiment 2 (pad-level `IO_MUX_FUN_FILTER_EN` on GPIO 43/44 — independent ~25 ns physical filter at the pad input) and Experiment 3 (explicit `gpio_pullup_dis` / `gpio_pulldown_dis`). Full ESP32-S3 master peripheral audit and ranked experiment plan in [`docs/explorations/esp32-s3-i2c-master-deep-dive.md`](../explorations/esp32-s3-i2c-master-deep-dive.md). v8 with I2C buffer remains the architectural answer regardless.

This document exists as a handoff. A long multi-session debugging effort has happened. A fresh AI session (or the same human returning later) should be able to read this file, glance at the referenced files, and pick up exactly where the investigation left off.

---

## Fastest possible read (start here if you're a new session)

- **What's broken**: On main PCB v7, the BQ24195 (I2C addr 0x6B) stops ACKing its address whenever a TCA9548A channel is opened with a cable that has **DC pullup on SDA toward +3.3 V** at the far end. SCL loading does nothing (Phase 12). SDA pulled to GND does nothing (Phase 13 polarity test). Every other I2C slave keeps working. Failure is always error code **2 (NACK on address)**, never 5 (bus hang). Deterministic, live-state, clears immediately when the channel closes (or when SDA is unplugged from the cable). Rail-load-only at the connector does NOT trigger it (Phase 11).
- **Boards tested**: 3 of 3 assembled v7 boards. Board 1 (originally healthy, now damaged by a failed bodge attempt — see Phase 7). Board 2 (assembly defect, BQ dead at boot, not part of this investigation — see Phase 8). Board 3 (healthy, reproduces the fault identically to Board 1's original behavior — see Phase 9). So the fault is design-level, not per-board.
- **Firmware state**: `SensorManager::runBusDiagnosticLoop()` is the active diagnostic. Prints `BQ:X(n)` with real error code. Run in env `motion-play-v7-diag` to skip WiFi/MQTT init (`-DDIAG_NO_WIFI`) — useful for eliminating RF confounds, but RF is already ruled out so the default `motion-play-v7` env is fine now.
- **What's ruled out**: sensor-side defects; power brown-out; I2C speed (100 kHz same as 400 kHz); pullup strength (4.7 k, 10 k, 47 k external all fail identically — though note the weakness of that test, see Phase 5); ESP32 WiFi/BT RF coupling (Phase 6); routing differences between CH0/CH1/CH2 (all three behave identically, Phase 6); cable stub capacitance alone (dangling cable passes, Phase 6).
- **What's alive as a hypothesis (post-Phase-23)**: Both threshold stories at the BQ pad are **refuted by direct measurement**. Story D-revised (V_IH violation) refuted by Phase 20 — SDA worst dip 3.01 V, ~1.7 V above V_IH = 1.3 V. Story G-revised (V_IL violation) refuted by Phase 23 — bumping ESP32-S3 drive to `GPIO_DRIVE_CAP_3` dropped V_OL at BQ pin 6 to ~50 mV (peak 77, floor 30, with cable in), yet BQ still NACKs. The mechanism is not at SDA's voltage levels. Surviving option space is narrower but unidentified: (1) **Story F — ESP32-S3 I2C peripheral interaction**: S3's I2C goes through GPIO matrix (no IOMUX direct path), and community reports document subtle output glitches and "S3 touchier than ESP32 on same bus" patterns — the cable + S3 master combination may emit a transaction the analyzer accepts as 0xD6 but BQ's stricter input rejects. (2) **Story H — BQ-side input feature** (Schmitt deglitcher, START detector, etc.) interacting with cable parasitics in some way not captured by the simple V_IL/V_IH model. (3) **Some timing-related effect** we haven't directly captured. Phase 22 (50 kHz null) rules out clock-rate-dependent dynamics; the issue is invariant to clock speed. Earlier phases ruled out: Stories A/B/C residuals (Phases 13/14/15/18), USB-C/VBUS state (Phase 18), routing-asymmetry-EMI (Phase 16), the original ESD-diode framing of Story D (Phase 17 datasheet drill), cable-as-EMI-antenna (Phase 17/19 — 2.5 cm cable too short), documented BQ operating modes (Phase 10).
- **What hasn't been tried yet**: **Arduino-as-master probe in failing config — highest-priority remaining test.** Discriminates Story F (ESP32-S3 master peripheral quirk) from Story H (BQ-side input issue regardless of master). Infrastructure ready (`motion-play-v7-relbus` env, `tools/arduino-sketches/v7_bq_master_probe/`). Cheap pre-test: scope-capture START condition at BQ pin 6 with cable in vs out, look for SCL droop during SDA's fall or other anomalies. v8 with I2C buffer remains the architectural answer regardless of which surviving story turns out to be right.
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

**Next test (post-Phase-18):** Arduino-as-master probe of BQ in the failing config — now the uncontested top of the priority list (Phase 18's bench-PSU result ruled out USB-C / VBUS state as a contributor and removed the only other pre-scope test from the queue). Discriminates Story D-revised (BQ's input stage is the problem regardless of master) from Story F (ESP32-S3 I2C peripheral interaction is part of the trigger). Blocked on a small firmware change (`DIAG_RELEASE_I2C` build flag) that releases the bus from the ESP32 without holding reset down. See "Immediate next steps" for full priority list (Arduino → Phase 11 current → scope at BQ pads → v8 buffer in parallel).

**Candidate fixes:** v8 design with an I2C buffer IC (P82B96 / PCA9517 / LTC4311) between the upstream bus and BQ is now the leading candidate, independently justified by Phases 15 and 17 — the disturbance is steady-state at BQ's pin and lives in the receiver's input stage, so isolating BQ from any upstream-side perturbation eliminates the fault regardless of which surviving story (D-revised, E, or F) turns out to be the precise mechanism. Earlier-considered resistor rework on R28/R29 was disproven as sufficient by the 47 kΩ test in Phase 5. The Phase 7 bodge attempt damaged Board 1 without producing test data; do not repeat without first understanding the damage mechanism.

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
| Routing-asymmetry-EMI hypothesis (SDA traces nearer switching nodes than SCL traces, explaining SDA-only fault) | Phase 16 routing audit: SDA and SCL trace lengths within 0.4 mm (72.9 vs 73.3 mm), and SCL is consistently *closer* than SDA to every measured noise source — L1 (0.5 mm closer), L2 (0.5 mm closer), BQ SW pads 19/20 (0.3–0.4 mm closer), BOOST_SW (0.9 mm closer), BQ_SW (0.4 mm closer), Protected_VBUS (0.5 mm closer). If routing-EMI mattered, SCL should be the failing line. It isn't. Mechanism is internal to BQ's SDA input stage, not in PCB routing |
| Original Story D framing — ESD-diode-mediated charge injection at BQ on rising-edge overshoot above VDD+0.6 V | Phase 17 datasheet drill: BQ24195's SDA pin is rated abs max +7 V (datasheet line 480–483), characterised at V_PULL-UP = 1.8 V with V_IH(min) = 1.3 V (line 1595–1632). There is no conventional upper ESD clamp diode at +3.3 V; the upper protection is almost certainly a snapback structure that doesn't conduct until ~6 V — well above any voltage the bus could reach in normal or ringing operation on a 3.3 V system. The diode the original story relied on does not exist where the story needed it. Story D is reframed as a CMOS receiver noise-margin story (Story D-revised) — see "Current working theory" |
| Cable-as-EMI-antenna framing of Story E (cable picks up switcher noise and injects it onto SDA) | Operator clarification (Phase 17 era): all failing-config testing has used ~2.5 cm cables held horizontally away from the board. A wire of that length at that distance from L1/L2/U5/U6 cannot couple meaningfully at switcher fundamentals (1.5–2.2 MHz); the LC self-resonance of a stub of that parasitic profile is in the hundreds of MHz, well above any switcher harmonic with appreciable energy. The EMI-antenna framing is therefore implausible. The residual "cable parasitics altering bus dynamics independently of crosstalk" variant collapses largely into Story D-revised |
| USB-C / VBUS state contributes to the BQ NACK (BQ input state machine, VBUS-dependent supply noise pathway, USB host noise via cable shield, etc.) | Phase 18 bench-PSU-from-battery-pads test: with USB-C VBUS completely absent (data-only USB-C cable for serial only, board powered from bench PSU at ~3.7 V on BAT_RAW), the BQ NACK reproduces identically — `BQ:X(2)` on the TCA2 row only, persistent across 14 post-cable iterations, same as USB-C-powered runs. USB-C / VBUS state is not part of the trigger |
| Transient-at-plug-in framings (any story where the cable's act of being plugged in fires a one-shot event that latches BQ off) | Phase 18 per-row recovery pattern: BQ recovers spontaneously between TCA2 selections within a single iteration of the diagnostic loop, with no software intervention. BASE / TCA0 / TCA1 rows are clean immediately after a TCA2 row's NACK. Any story requiring a latched state from a plug-in transient is contradicted; the failure mechanism requires *ongoing* electrical contact of the cable's SDA wire to the main bus, not a one-shot event at the moment of contact |

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

### Phase 17 — BQ24195 SDA pin protection drill (2026-04-25)

Goal: Story D as written through Phase 14 hinges on the assumption that BQ's SDA pin has a conventional upper ESD clamp diode referenced to its internal VDD (~3.3 V), which would forward-bias on rising-edge overshoot above VDD+0.6 V and inject charge into BQ's logic supply. This phase drills into the cleaned BQ24195 datasheet (`hardware/components/BQ24195/bq24195_datasheet_clean.html`) to determine what the SDA pin's protection topology and reference rail actually are — i.e., whether the upper clamp is at +3.3 V, somewhere else, or absent in the conventional sense.

Two datasheet sections answer this directly:

**Absolute maximum ratings (datasheet line 480–483, section 7.1):**

> SDA, SCL, INT, OTG, ILIM, REGN, TS1, TS2, ~CE, D+, D– — minimum −0.3 V, **maximum +7 V**.

The lower bound `-0.3 V` matches the standard "GND clamp diode forward voltage" — there is a conventional ESD clamp from the pin to GND, and below ~−0.3 V it conducts and either limits the input or causes damage at extended operation. The upper bound `+7 V` is the salient finding: SDA tolerates DC up to +7 V with no damage, on a chip whose internal VDD is ~3.3 V (REGN is 4.5–5.0 V, but it's not the I2C reference rail — see Q1 of Phase 10 — and the ESD/abs-max group covers REGN itself in the same row, so the SDA tolerance can't be a REGN-clamped rail story either).

**I2C electrical characterisation (datasheet line 1595–1632, section 7.5):**

> I2C INTERFACE (SDA, SCL, INT) — V_IH(min) **1.3 V** at V_PULL-UP = 1.8 V; V_IL(max) 0.4 V; V_OL(max) 0.4 V at I_sink = 5 mA; high-level leakage 1 µA at V_PULL-UP = 1.8 V.

TI explicitly characterise the I2C input thresholds with V_PULL-UP = 1.8 V as the spec point. Together with the +7 V abs-max, this is unambiguous: BQ24195's I2C pins are designed for level-mixed operation, intended to work with pull-ups anywhere from 1.8 V to ~5 V. **There is no conventional upper ESD clamp diode at +3.3 V on SDA.** Whatever protection sits above the operating range is almost certainly a snapback structure (or a higher-rail-referenced clamp) that doesn't conduct until ~6 V or higher — well above any voltage the bus could reach in normal or even ringing operation on a 3.3 V system.

**What this means for Story D as previously written:**

Story D's original mechanism — "rising-edge overshoot above VDD+0.6 V briefly forward-biases BQ's upper ESD clamp diode, dumping charge into VDD and disturbing internal logic" — is **mechanistically unsupported**. The diode the story relies on does not exist in the form the story assumes. For overshoot to engage the actual upper protection structure on this pin, SDA would need to swing to roughly +6 V or higher — implausible on a 3.3 V bus with conventional pull-ups, and if it did happen the chip would also be at risk of permanent damage (which it isn't — the fault is recoverable instantly when the cable is removed).

**What this finding does *not* rule out:**

The fault's polarity asymmetry — SDA pulled toward +3.3 V at the far end fails, SDA pulled toward GND does not — is, if anything, **better explained** by this datasheet result than by the original ESD-diode framing. The pin has a real, conventional lower clamp diode at GND that absorbs negative-going disturbances cleanly (a feature, not a fault). It does *not* have an equivalent upper clamp at VDD/+3.3 V. So GND-side disturbances get absorbed by the lower clamp and never make it into the receiver's input stage; +3.3 V-side disturbances ride straight through unclamped to the input stage. That's exactly the polarity asymmetry observed in Phase 13.

The remaining live explanation lives in the **CMOS receiver itself**, not in the ESD network. With the cable-extended pullup attached, BQ's SDA pin sees:

- Slightly faster rising edges, because the cable's far-end pullup parallels R28 (modest for a 47 kΩ far-end pullup, larger for a 4.7 kΩ — but the failure is invariant across that range, so per-pulse current isn't the gating variable).
- Steady-state added parasitic capacitance from the cable + connector (~5–10 pF), which is constant regardless of far-end resistor value and therefore consistent with the pullup-strength-irrelevant observation.
- Capacitive crosstalk from SCL on the parallel-routed F.Cu/B.Cu pair (Phase 16 noted SDA and SCL travel near-parallel from U5 past U7 to ESP32 and onward to TCA — operator-confirmed in this session).

The combination — small added C on SDA, with SCL transitions injecting crosstalk pulses — can plausibly drag SDA's voltage at BQ's pad below V_IH = 1.3 V momentarily during the 9th-clock ACK window, causing BQ's input to mis-classify the address byte and NACK. This is classic CMOS noise-margin failure at the receiver, not ESD diode mediation. It satisfies every constraint that previously narrowed Story D and Story E both: steady-state, SDA-only, +3.3 V-polarity-only, source-noise-independent, cable-distance-required, bus-recovery-immune, pullup-strength-invariant.

The story is therefore **reframed** in "Current working theory" below — Story D is no longer the "ESD-diode-mediated charge injection" hypothesis; it is now the "SDA input-stage noise-margin failure at BQ" hypothesis. The mechanism is still a single pin at a single chip, still requires the cable, still predicts an active I2C buffer between the upstream bus and BQ would eliminate the fault. The scope-target prediction, however, changes — see "Implications for next steps" at the bottom of this section, and the new "Scope targets in the post-Phase-17 v7 I2C investigation" section at the top of `docs/debugging/i2c-oscilloscope-debugging.md`.

**Implications for next steps:**

- The scope target gains a second waveform feature to look for: in addition to "rising-edge overshoot at BQ's SDA pad" (the previous Story D prediction, now demoted because the diode it would engage doesn't exist at +3.3 V), capture **SDA at BQ's pad during the 9th-clock ACK window with the failing config attached** and look for SCL-correlated wobble that drops SDA below ~1.3 V momentarily. Both targets are in the same setup; the scope session captures both at once.
- A new tracked hypothesis enters the option space: **ESP32-S3 I2C peripheral interaction** — until an external master (Arduino) probes BQ in the failing config, we can't formally separate "BQ's input stage is the problem regardless of master" from "ESP32's I2C drive characteristics interact badly with the cable-modified bus." Story D-revised predicts Arduino master also fails. The peripheral-interaction hypothesis predicts Arduino master succeeds. This is the highest-information pre-scope test that remains.
- The Arduino-as-master test was previously blocked on "how do I hold the ESP32 in reset for the duration?" The cleanest answer is a firmware build flag `DIAG_RELEASE_I2C` that runs the normal init through `configureBQ24195()` and any baseline diagnostics, then calls `Wire.end()` and reconfigures GPIO 43/44 to `INPUT` (no internal pullup), then sits in a tight print loop. ESP32 stays alive (so +3.3 V, BQ config, etc. remain stable) but the bus is electrically free for an external master. No physical reset-button hold required. This flag is queued as a separate firmware change before the test runs.
- The bench-PSU-from-battery-pads test (Phase 10's deferred sanity check) becomes mildly more interesting as a discriminator on whether USB-C input state contributes — the procedure is straightforward (solder temporary leads to BAT_RAW + a GND test pad, set bench PSU to ~3.7 V, USB-C disconnected; Q2 PMOS handles polarity correctly). Stays at moderate priority.
- Cable-position scope test (moving the cable physically away from the board to discriminate against a cable-as-EMI-antenna mechanism) is **deprioritised**. The operator confirmed the failing config has been tested with a 2.5 cm cable held horizontally away from the board — a geometry that's already a worst case for cable-as-antenna mechanisms. Switcher fundamentals at 1.5–2.2 MHz cannot couple meaningfully into a 2.5 cm wire that distance from the inductors; switcher harmonics with appreciable energy are well below the LC self-resonance of a stub of that length and parasitic profile. Story E in its "cable as EMI antenna" framing is therefore weakened independently of the BQ datasheet drill.

---

### Phase 18 — Bench-PSU-from-battery-pads test (2026-04-26)

Goal: Discriminate whether the BQ NACK depends on USB-C / VBUS state. Phase 17 deferred this as a moderate-priority sanity check with two possible outcomes — if BQ continues to NACK with USB-C disconnected, USB-C / VBUS state is not part of the trigger; if BQ stays present (or behaves differently), VBUS state contributes (which would partially refute Stories D-revised and F and reopen a supply-mediated story line).

**Setup:**

- Bench PSU at ~3.7 V (mid-charge 18650 simulation), current limit 500 mA, alligator clips on temporary leads soldered to BAT_RAW (+) and a GND test pad.
- USB-C: data-only cable (VBUS conductor severed), so ESP32-S3 USB CDC carries serial but BQ's VBUS pin sees no input.
- Failing-config cable in J6: 10 kΩ between the cable's SDA wire and the cable's VCC wire (Phase 12 / 13 standard config), routed to TCA channel 2.
- Firmware: `motion-play-v7-busrec` env (`BUS_RECOVERY_TEST=1`, 3× dummy `Wire.beginTransmission(0x00); endTransmission();` framings prepended to each TCA channel-open before probing).
- Q2 PMOS gate biased toward GND via R34 — FET turns on for forward polarity through the battery pads, providing the same VSYS path as a real cell would.

**Procedure:**

1. PSU off, polarity verified, alligator clips on BAT_RAW + GND leads.
2. PSU on at ~3.7 V; board boots from the battery side (USB-C data-only cable already in place for serial).
3. `pio device monitor -e motion-play-v7-busrec`.
4. Run diagnostic loop for 7 iterations with no cable in J6 (baseline).
5. Plug failing-config cable into J6 between iterations 7 and 8.
6. Continue running the diagnostic loop through iteration 21.

**Results:**

Iterations 1–7 (no cable, bench-PSU only): all probes pass exactly as expected. BQ ACKs on every row. Baseline clean, confirming the bench-PSU + data-only-USB-C setup is electrically healthy.

Iterations 8–21 (failing cable in J6): identical failure pattern to all USB-C-powered runs — `BQ:X(2)` appears only on the **TCA2 row**, persistent across all 14 iterations. Per-row pattern within each post-cable iteration:

- **BASE** row: BQ ACKs (all TCA channels closed, cable's SDA wire electrically isolated from the main bus).
- **TCA0** row: BQ ACKs (channel 0 open, but cable not on channel 0 — SDA wire still isolated).
- **TCA1** row: BQ ACKs (same — cable not on channel 1).
- **TCA2** row: BQ NACKs with error 2 (channel 2 open, cable's SDA wire electrically merged with the main bus).

The `BUS_RECOVERY_TEST` framings (3× dummy START + address + STOP) prepended to every TCA channel-open before probing did not rescue BQ on any of the TCA2 rows. Consistent with Phase 15.

**Interpretation:**

**1. USB-C / VBUS state is ruled out as a contributor.** The BQ NACK reproduces identically with VBUS completely absent from the BQ. This closes a class of stories that depended on USB-C input state:

- BQ24195's USB input state machine (PG / VBUS_GD / DPM / boost-mode quirks) interacting with I2C.
- Any supply-noise pathway requiring VBUS to be present.
- "USB-C plugged in → BQ in some specific charging state → I2C input bias shifts" framings.
- "Host computer's USB hub injects noise via the cable shield onto the board's I2C bus" framings.

The failure is local to BQ + main I2C bus + the cable's SDA wire, with no dependence on what's happening at VBUS.

**2. The failure is live / ongoing, not latched at the moment of plug-in.** The per-row recovery pattern is diagnostic gold and worth highlighting for a property no previous phase had directly demonstrated:

- If the cable's act of being plugged in had triggered a one-shot event (charge injection, ESD-like transient, latching that re-tilts the input bias), BQ would stay NACKed on *all* rows after that event, including BASE / TCA0 / TCA1. It does not.
- BQ recovers within microseconds-to-milliseconds of TCA2 closing — every iteration's BASE row is clean.
- BQ breaks again immediately when TCA2 reopens.

This means the failure mechanism requires **ongoing electrical contact** of the cable's SDA wire to the main SDA bus. Whatever is wrong is being driven continuously by the cable's DC + AC parasitics, not by a transient at the moment of plug-in. The mechanism is "live" in the sense that it operates only while TCA channel 2 is the open channel; it neither precedes the opening nor outlives the closing.

**What this further refines:**

- **Story D-revised gains specificity.** It is not "ESD event on cable insertion" or "transient that re-biases the BQ input on contact." It is "while the cable is electrically connected, BQ's SDA receiver is sitting in a noise-margin failure regime driven by ongoing crosstalk and/or parasitic loading." Cleaner, more falsifiable, and more directly aligned with what a scope capture at the BQ pad will reveal once the scope arrives.
- **Story A's residuals are doubly closed.** `BUS_RECOVERY_TEST` framings were already firing on every probe pass and do not rescue BQ (Phase 15). Combined with the live/ongoing observation (there is no stuck state to recover from — BQ recovers spontaneously when TCA2 closes, with no software intervention), Story A has nothing left.
- **Story F (ESP32-S3 I2C peripheral interaction) is not differentially affected.** Story F was not VBUS-state-dependent in any of its formulations, so it is neither weakened nor strengthened by Phase 18. It still requires the Arduino-as-master test for discrimination from Story D-revised.

**Implications for next steps:**

- Phase 18 is complete; the bench-PSU-from-battery-pads test moves out of the pre-scope priority list and into completed phases.
- The Arduino-as-master test is now the **only** remaining cheap, pre-scope test that meaningfully discriminates surviving hypotheses, and is therefore the uncontested top of the priority list. Still blocked on the `DIAG_RELEASE_I2C` firmware flag.
- The "live / ongoing" framing reinforces the existing scope-capture targets at BQ's SDA pad — the scope session should focus on capturing BQ's SDA pad **while the failing cable is electrically connected (TCA2 open)**, looking for SCL-correlated wobble below V_IH = 1.3 V on the 9th-clock ACK window. There is no need to capture transient events at the moment of cable insertion — those are not the mechanism. The capture targets in `docs/debugging/i2c-oscilloscope-debugging.md` already match this framing.
- All surviving stories continue to point at v8 with an I2C buffer between the upstream bus and BQ as the right design intervention; Phase 18 does not change that.

---

### Phase 19 — ESP32-S3 / TCA9548A literature search (2026-04-28)

Goal: zoom out from the rabbit-hole of fine electrical hypotheses and ask a question none of the prior phases formally addressed — are there documented quirks, errata, or community-known issues with the ESP32-S3 I2C peripheral or the TCA9548A multiplexer that could explain or partially explain the v7 fault signature ("SDA pulled toward +3.3 V at the far end of any cable plugged into J4–J6 causes BQ24195 to NACK its address at 0x6B; SCL loading does nothing; SDA-to-GND does nothing; resistance value is irrelevant from 4.7 kΩ to 47 kΩ; live/ongoing while connected, recovers immediately when removed")? Story F (ESP32-S3 I2C peripheral interaction) had been carrying this question implicitly without ever being investigated. The TCA side had never been investigated at all.

**Method:** targeted web research across ESP-IDF GitHub issue tracker, arduino-esp32 issues, ESP32 community forums, TI's TCA9548A datasheet, and TI E2E support forums.

**Findings — ESP32-S3 side:**

1. **TX FIFO leak after NACK — ESP-IDF #14343 (IDFGH-13437).** When the S3 master receives a NACK on a *data byte*, the queued byte is not flushed from the TX FIFO, and the *next* transaction sends the stale byte instead of the new address byte. **Probably not our bug** — this would manifest as the master sending wrong addresses on subsequent probes; our log shows the post-BQ-NACK probes (TCA, PCA, VCNL on the same row) all behaving as expected. But it confirms the S3 has documented I2C-peripheral quirks that don't exist on the original ESP32.

2. **Generic "S3 less reliable than ESP32 on the same bus" reports.** ESP-IDF #11397 (IDFGH-10122), ESP-IDF #8741 (IDFGH-7138), and several esp32.com forum threads from 2024–2025 describe sensors that work cleanly on the original ESP32 but produce intermittent NACKs when the same code is run on an S3 across the same bus. No single root cause; the cluster reads as "the S3 I2C peripheral is touchier under marginal bus conditions." This is the literature signature most consistent with Story F: it doesn't predict our exact behaviour, but it's the kind of thing that could partially explain why a CMOS-receiver-noise-margin issue at BQ shows up under our specific master and might not show up under another.

3. **Arduino-ESP32 3.2.0 I2C regression.** Issues #11351 (BMI160 / ICM-20948) and #11496 describe a regression introduced in arduino-esp32 3.2.0 that broke I2C with several common sensors that worked under 3.1.3. Worth a 5-minute check against the version pinned in `platformio.ini` and a downgrade-to-3.1.3 sanity test if applicable. Not predicted to fix the underlying electrical signature, but a free disambiguator.

4. **Clock-stretching cap at 20 ms on S3.** ESP-IDF #14667 (IDFGH-13819). Not relevant — BQ24195 doesn't clock-stretch by default and we've never observed clock-stretch behaviour on this bus.

5. **Internal-pullup quirks.** Arduino-ESP32 #4887. The S3's internal pullups don't fully disable through `pinMode(INPUT)` alone; explicit `gpio_pullup_dis()` / `gpio_pulldown_dis()` calls are needed. **Bears on the Arduino-as-master test only**, where the `DIAG_RELEASE_I2C` flag re-configures GPIO 43/44 to INPUT before the Arduino takes over the bus. The release path should call the explicit disable functions to avoid leaving a residual ~50 kΩ pull on either line that would bias the Arduino's view of the bus. Worth confirming in the firmware before the Arduino-as-master test runs.

**Findings — TCA9548A side:**

1. **Pass-gate level-translator topology — fundamental design feature, not a bug, but with implications we hadn't formally accounted for.** Per the TI TCA9548A datasheet and a [TI E2E thread on level translation](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/542188/tca9548a-level-translation), the TCA's per-channel switches are **NMOS pass-FETs**, not CMOS analog switches. The Vcc pin is the gate of every pass-FET. When the source/drain voltage rises above approximately Vcc − Vt (≈ 1.9 V at Vcc = 3.3 V), the FET pinches off and the upstream and downstream sides decouple. Below that voltage, the FET conducts bidirectionally. **Implications for our setup:**
   - When the TCA channel is open and SDA is sitting HIGH at idle (~3.3 V on both sides), the FET is **pinched off** and the two sides are electrically decoupled. Each side floats to its own pullup. The cable's far-end pullup does *not* directly drive BQ's pad through the FET in this regime.
   - When SDA is being pulled LOW by the master, the FET is fully on and the cable's parasitic capacitance (~5–10 pF) is effectively in parallel with the upstream bus capacitance.
   - During the **rising edge** of SDA (master releasing the line), the upstream bus rises toward 3.3 V via R28 (2.2 kΩ). As long as the voltage is below ~1.9 V, the FET is still conducting and the upstream is electrically merged with the cable's parasitic C; once it crosses ~1.9 V the FET pinches off and the upstream finishes its rise to 3.3 V on its own pullup alone. **The rising edge therefore has a non-linear shape: slow up to ~1.9 V (loaded by cable C), then accelerates above that point (decoupled, on-board pullup only).** This is a mechanism specific to the TCA-with-cable-and-far-end-pullup configuration. It does not exist with on-board pullups alone (R28 only) and does not exist with the cable removed.
   - This is consistent with Story D-revised but **sharpens it**: the receiver-side noise-margin failure at BQ doesn't depend solely on SCL-to-SDA capacitive crosstalk on the on-board trace pair — it also has a contribution from the cable's added C dragging down the rising-edge ramp through the FET's bidirectional region. Both mechanisms predict the same scope target (SDA wobble below V_IH = 1.3 V at BQ's pad during the 9th-clock ACK window); the literature search just adds a second pathway to the story.

2. **TI E2E thread describing the inverse of our symptom — [PCA9548A: downstream device only detected when downstream pullup is removed](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/1635473/pca9548a-down-stream-with-out-pull-up-only-working/6306200).** A user reports a downstream slave failing detection when both upstream and downstream pullups are present, and detection succeeding when the downstream pullup is removed. TI's response attributes the failure to the pass-gate's Vpass limit preventing the downstream side from being driven properly. Same physics (pass-gate Vpass limit, level-translator topology), opposite victim (their downstream slave fails; our upstream BQ fails). Note: in their case the upstream master is the one the chip is supposed to communicate with, and the pass-gate quirk affects what the slave sees. In our case the master and the failing slave are both upstream, and the cable's far-end pullup creates a configuration TI's framing didn't directly anticipate.

3. **TCA9548A low-frequency channel-switching reliability — TI E2E #1107817.** Some channel-switching reliability issues at SCL frequencies below 100 kHz. Not our issue (we tested 100 kHz and 400 kHz with identical failure).

4. **No published TCA9548A errata** in the datasheet's Revision History describing upstream-slave NACK from downstream-pullup conditions. The pass-gate Vpass behaviour is documented, intentional behaviour, not a bug — but it has the side effect described above on rising-edge shape.

**Synthesis:**

There is **no clean, single, well-documented errata or known issue on either chip that exactly predicts our v7 fault signature.** Several adjacent findings exist on each side, none decisive:

- The S3's I2C peripheral is documented to be touchier than the original ESP32 but no single bug matches our pattern. Story F's plausibility is increased modestly — the kind of marginal-bus-condition NACK that the S3 community sees on the same bus where the original ESP32 worked is the right shape of bug to map onto our observation, even if not the exact mechanism.
- The TCA9548A's pass-gate Vpass behaviour is well-documented level-translator physics. It adds a specific contributing mechanism to Story D-revised (non-linear rising-edge shape through the FET below ~1.9 V), tightening but not changing the dominant story.
- Neither chip has a published errata that says "this device is known to NACK its own address under [specific bus loading condition]." Our symptom remains undocumented behaviour from the BQ24195 side specifically (Phase 10 already established that), and now also from the ESP32-S3 and TCA9548A sides.

**Implications for next steps:**

- **Strengthens the case for the Arduino-as-master test sooner rather than later.** Story F was the only surviving non-receiver-side story going into Phase 19, and the literature search confirms there's no smoking-gun bug to either side that would resolve the question without empirical disambiguation. The Arduino-as-master test remains the cleanest discriminator: if Arduino master also NACKs BQ in the failing config, Story F is refuted and Story D-revised is confirmed; if Arduino master ACKs BQ where the ESP32 NACKs, Story F is confirmed and Story D-revised is at least partially weakened.
- **Two cheap, free sanity checks added to the queue, both independent of the scope work:**
  1. Check `platformio.ini` for the arduino-esp32 framework version. If it's 3.2.x, downgrade to 3.1.3 and re-run the failing config. 5-minute test, no cost. Disambiguates against the 3.2.0 I2C regression cluster.
  2. In the `DIAG_RELEASE_I2C` release path, confirm that GPIO 43/44 reconfiguration calls explicit `gpio_pullup_dis()` / `gpio_pulldown_dis()` (not just `pinMode(INPUT)`). Required to ensure the bus is electrically clean for the Arduino master.
- **Scope target unchanged.** Phase 19 doesn't introduce a new scope target. The Story D-revised primary target (SCL-correlated wobble on SDA at BQ's pad below V_IH = 1.3 V during the 9th-clock ACK window) is still the right thing to capture; Phase 19 just adds a second mechanism (TCA pass-gate non-linear ramp) that can produce the same observable.
- **v8 buffer fix unchanged.** All surviving stories — Story D-revised, Story E, Story F — are receiver-side or master-side problems that an I2C buffer between the upstream bus and BQ would isolate from. Phase 19 doesn't reshuffle this.

**Sources captured for traceability:**

- [ESP-IDF #14343 — S3 master TX FIFO not reset after NACK (IDFGH-13437)](https://github.com/espressif/esp-idf/issues/14343)
- [ESP-IDF #11397 — S3 vs ESP32 I2C instability (IDFGH-10122)](https://github.com/espressif/esp-idf/issues/11397)
- [ESP-IDF #8741 — S3 I2C communication failures (IDFGH-7138)](https://github.com/espressif/esp-idf/issues/8741)
- [Arduino-ESP32 #11351 — BMI160 / ICM-20948 broken in 3.2.0](https://github.com/espressif/arduino-esp32/issues/11351)
- [Arduino-ESP32 #11496 — I2C regression 3.1.3 → 3.2.0](https://github.com/espressif/arduino-esp32/issues/11496)
- [ESP-IDF #14667 — S3 clock stretching capped at 20 ms (IDFGH-13819)](https://github.com/espressif/esp-idf/issues/14667)
- [Arduino-ESP32 #4887 — internal pullups not cleanly disabled](https://github.com/espressif/arduino-esp32/issues/4887)
- [TI TCA9548A datasheet](https://www.ti.com/lit/ds/symlink/tca9548a.pdf)
- [TI E2E — TCA9548A level translation (#542188)](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/542188/tca9548a-level-translation)
- [TI E2E — PCA9548A downstream pullup prevents detection (#1635473)](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/1635473/pca9548a-down-stream-with-out-pull-up-only-working/6306200)
- [TI E2E — TCA9548A low-frequency channel switching (#1107817)](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/1107817/tca9548a-tca9548a-no-channel-switching-with-i2c-frequency-100khz)

---

### Phase 20 — Direct scope at BQ pin 6 via Sensepeek SQ-500 (2026-04-29)

Goal: capture SDA at BQ24195's actual pin 6 (not at TPIO43 ~34 mm of trace away), looking for the high-level wobble during the 9th-clock ACK window that Story D-revised predicted (SDA dragged below V_IH = 1.3 V by SCL crosstalk + cable parasitics, BQ's CMOS receiver mis-classifying the address byte).

Setup: Sensepeek PCBite + SQ-500 BNC-terminated 10× scope probe arms — spring-loaded needles landed directly on BQ pin 6 (SDA, CH1) and pin 5 (SCL, CH2) with no soldering on the chip. Both probe grounds via a soldered wire stub on the board's GND test pad. Rigol DHO804 trigger configured as I2C MissedAck. Confirmed `Write:D6 A:1` decoded annotation at the trigger marker — direct corroboration on the wire that BQ NACKs its address (rules out a class of "ESP32 misperceives the bus" stories).

Result: cursor measurement of SDA during the 9th-clock NACK window with the failing-config cable in J6:

| Cursor | Voltage |
|---|---|
| Y1 (idle high) | 3.29 V |
| Y2 (worst dip during 9th-clock window) | 3.01 V |
| ΔY | -281 mV |

SDA's worst excursion during the NACK window is 3.01 V — ~1.7 V above V_IH = 1.3 V. The wobble is real (~280 mV peak-to-peak, correlated with SCL transitions, classic capacitive crosstalk) but does not approach the noise-margin threshold. Visually, the wobble looks **identical in ACKed and NACKed transactions within the same captured window**. Rising edges show clean exponential shape — no non-linear "kink" at ~1.9 V that Phase 19's TCA pass-gate prediction would have produced.

**Conclusion: Story D-revised refuted at the receiver pad.** The 280 mV wobble is normal SCL-to-SDA capacitive crosstalk that exists on every I2C transaction regardless of whether the slave ACKs. It is not the mechanism. Phase 21 shifts the diagnostic from V_IH (high-level threshold during ACK window) to V_OL (low-level threshold during data-bit transmission).

### Phase 21 — V_OL measurement at BQ pin 6 (2026-04-30)

Goal: with Story D-revised refuted, test whether SDA's *low* level during 0-bits of the address byte exceeds BQ's V_IL threshold. If so, BQ would mis-classify 0-bits as 1s, fail to see 0xD6 (its own address with R/W=0), and correctly NACK because it doesn't think it's being addressed.

Method: same Sensepeek setup as Phase 20. Address byte 0xD6 = 11010110 — three 0-bits at positions 5, 3, and 0. Cursor-measured SDA voltage during a 0-bit (master actively pulling SDA low) in two conditions: failing cable in J6, and cable removed.

Results:

| Condition | Floor (lowest) | Average | Peak (highest) |
|---|---|---|---|
| No cable (BQ ACKs) | ~375 mV | ~650 mV | ~790 mV |
| Failing cable (BQ NACKs) | ~581 mV | ~750 mV | ~894 mV |
| Cable adds | +206 mV | +100 mV | +104 mV |

Three observations:

1. **SDA's V_OL is elevated by the cable**, ~100 mV at the central level and ~104 mV at the peak excursion. Direct, repeatable cursor measurement at BQ's pin.
2. **V_OL is already above BQ's datasheet V_IL(max) = 0.4 V even in the clean baseline** — peak excursion 790 mV, average 650 mV. Yet BQ ACKs cleanly without the cable. **BQ's effective in-practice V_IL is ~800–900 mV**, well above the worst-case datasheet number. Real silicon has more margin than the spec guarantees.
3. **SCL's V_OL is also elevated when the failing cable is plugged in**, despite the cable's SCL wire dangling unconnected. Likely capacitive crosstalk from SDA, or shared driver-side coupling inside the ESP32-S3 I2C peripheral. Doesn't affect the failure mechanism (BQ samples on SCL rising edges, not on SCL low level), but tells us the V_OL elevation isn't strictly per-pin.

**Mechanism (Story G-revised, confirmed by direct measurement):**

The failing cable's 10 kΩ pullup at the far end injects ~330 µA into the SDA bus when TCA channel 2 is open. This current must flow through the ESP32-S3 master's SDA output pull-down to ground when SDA is being driven low. The added current raises V_OL by ~100 mV at the master's output, and that elevation propagates to BQ's input pin (the bus equilibrates). When SDA's worst-case peak excursion during a 0-bit (894 mV with cable) crosses BQ's effective V_IL threshold (~800–900 mV), BQ's CMOS receiver mis-classifies the 0-bit as a logic 1. The address byte 0xD6 gets read by BQ as something other than 0xD6 (e.g., 0xFF or some partial corruption). BQ doesn't see itself addressed and NACKs.

**Why only BQ:** INA219 has V_IL(max) = 0.99 V (standard I2C spec) — its tolerance window includes the elevated V_OL. BQ24195 has unusually strict input thresholds in this silicon, making it the failure-mode discriminator on a marginally-loaded bus.

**Why every prior phase is consistent:**

- **Phase 5 (pullup-strength insensitivity):** 4.7 kΩ–47 kΩ all inject enough current to push V_OL across BQ's threshold; exact value isn't critical.
- **Phase 6 (cable-only stub passes):** no DC pullup → no current path → no V_OL elevation.
- **Phase 11 (rail-load-only passes):** resistor between VCC and GND doesn't drive current into SDA.
- **Phase 12 (SCL-only pullup harmless):** elevates SCL's V_OL but not SDA's; BQ's address-byte sampling is on SDA.
- **Phase 13 (polarity asymmetry):** SDA-to-GND assists the master's pull-down (V_OL drops further, BQ ACKs); SDA-to-VCC fights it (V_OL rises, BQ NACKs). **Now perfectly explained.**
- **Phase 14 (clean PSU triggers identically):** DC current contribution is the same regardless of source noise.
- **Phase 15 (bus-recovery doesn't help):** bit-level corruption, not state-machine confusion.
- **Phase 18 (VBUS-independent, live/ongoing):** DC current path is independent of VBUS and persists while the cable is electrically connected.
- **Phase 20 (no V_IH violation):** the disturbance is on the LOW level, not the high level — we were probing the wrong feature for two phases.

**Conclusion (as of Phase 21):** Story G-revised is the mechanism. *Note: this conclusion is later refuted by Phase 23 — see below.*

### Phase 22 — I2C clock slowdown null result (2026-05-01)

Goal: test Story G-revised's prediction that slowing SCL allows SDA to relax to its true V_OL floor between transitions, dropping the peak excursion below BQ's V_IL.

Setup: `Wire.setClock(100000)` → `Wire.setClock(50000)` in `SensorManager::init()`. Reflashed `motion-play-v7-diag`. Failing-config cable in J6. Sensepeek probes still on BQ pin 6.

Result: **no change.** BQ NACKs identically (`BQ:X(2)` on TCA2 row, every iteration). Operator-reported scope observation: SDA and SCL waveforms look "clean and consistent," same DC shift from cable as Phase 21, no visible change in wobble dynamics or peak excursion. Slowing 2× already shows the wobble has time to fully relax — going further to 10 kHz would not help.

Implication: clock-speed-dependent dynamics are ruled out as the gating factor. Whatever mechanism is gating BQ's ACK is invariant to SCL period. Story G-revised is still alive as written but the "peak excursion crosses threshold" sub-story is weakened — the floor/average level itself is what would need to cross threshold.

### Phase 23 — ESP32-S3 GPIO drive-capability bump (2026-05-01)

Goal: directly test Story G-revised's V_OL prediction. Bump SDA/SCL drive from `GPIO_DRIVE_CAP_2` (default ~20 mA) to `GPIO_DRIVE_CAP_3` (~40 mA) to roughly halve master pull-down R_DS(on) and hence V_OL by Ohm's law. Predicted: V_OL drops from ~750 mV (cable in) to ~350 mV, well below BQ's ~800 mV effective V_IL → BQ ACKs.

Setup: added `gpio_set_drive_capability(GPIO_NUM_43, GPIO_DRIVE_CAP_3)` and same for GPIO 44 after `Wire.begin()`, with `#include <driver/gpio.h>`. Clock kept at 100 kHz to match Phase 21 baseline. Reflashed `motion-play-v7-diag`. Failing-config cable in J6. Sensepeek probes still on BQ pin 6.

Results (cursor measurement, cable in, BQ NACKs):

| Quantity | Phase 21 (CAP_2) | Phase 23 (CAP_3) |
|---|---|---|
| V_OL floor | ~581 mV | ~30 mV |
| V_OL peak | ~894 mV | ~77 mV |
| SCL V_OL range | (not cursor-measured) | ~290–350 mV |
| BQ behavior | NACK | NACK |

**Story G-revised refuted.** V_OL at ~50 mV (average) is far below any plausible V_IL — datasheet 0.4 V max, Phase 21's inferred effective threshold ~800 mV. There's no threshold story that fits V_OL = 50 mV failing while V_OL = 650 mV (Phase 21 no-cable baseline) succeeded. Operator confirmed via direct cursor measurement at BQ pin 6.

**Operator observation noted but not load-bearing**: when SCL falls to its V_OL, SDA shows a small downward spike (the floor 30 mV reading). This is normal SCL→SDA capacitive crosstalk via mutual C on the parallel-routed pair. Was present in Phase 20 captures too. Slaves sample SDA on SCL **rising** edges, not falling, so coupling during SCL fall doesn't directly affect bit-reading.

**What this leaves:**

- The mechanism is not at SDA's voltage levels (both V_IH and V_IL ruled out by direct measurement).
- The bus produces a transaction the I2C analyzer decodes as `Write:D6 A:1` (Phase 20) but BQ silently doesn't ACK.
- SDA and SCL both look visibly clean at BQ's pad with cable in.
- Whatever's wrong is something the simple "voltage level crosses threshold" model doesn't capture.

**Surviving option space:**

- *Story F — ESP32-S3 I2C peripheral interaction.* S3's I2C is GPIO-matrix-routed (no IOMUX direct path); community reports document subtle output glitches and "S3 touchier than ESP32 on same bus" patterns (Phase 19). The cable + S3 master combination may emit something on the wire that the analyzer accepts but BQ's stricter input rejects. Promoted from "tracked" to **highest-priority surviving hypothesis**.
- *Story H — BQ input-feature interaction.* BQ's I2C input may have a Schmitt deglitcher, START detector, or other feature whose timing/edge-shape sensitivity is disturbed by cable parasitics in a way not captured by simple voltage thresholds. Cannot be directly tested without BQ internals; would be inferred if Arduino-as-master also fails.
- Timing-related effects we haven't directly captured (setup/hold, START condition shape, etc.).

**Implications for next steps:**

- **Arduino-as-master test is now the uncontested top-priority experiment.** Its predictive power has *increased* with this null result — it cleanly discriminates Story F (Arduino succeeds) from Story H (Arduino also fails). Either outcome closes a real branch. Infrastructure ready.
- Cheap pre-test (5 min): scope-capture the START condition at BQ pin 6 — SDA falling edge while SCL high — with cable in vs out. Look for SCL droop, ringing, or unexpected coupling that could break BQ's START detection. Probes are already on BQ pins 5/6.
- v8 with I2C buffer remains the architectural answer: it isolates BQ from any upstream-side perturbation regardless of mechanism.

### Phase 24 — Arduino-as-master test confirms Story F (2026-05-01)

Goal: discriminate Story F (ESP32-S3 master peripheral quirk) from Story H (BQ-side input issue regardless of master). Procedure described in Phase 19 / Immediate next steps: `motion-play-v7-relbus` env releases the bus from the ESP32, then a SAMD21-based Arduino Nano 33 IoT becomes master via `tools/arduino-sketches/v7_bq_master_probe/v7_bq_master_probe.ino`.

Result: **Arduino Nano 33 IoT (SAMD21 SERCOM master) ACKs BQ at 0x6B in the failing config — same physical wire, same JST-SH cable with 10 kΩ pullup on SDA at far end, same TCA channel state.** The ESP32-S3 master NACKs the same address byte on the same wire seconds before/after.

**Story F confirmed; Story H refuted.** The fault is unambiguously in the ESP32-S3 master peripheral. BQ's input is functioning correctly — it ACKs the SAMD21's address byte cleanly. Whatever the ESP32-S3 emits on the wire — accepted by the I2C protocol analyzer as `Write:D6 A:1` — is rejected by BQ for reasons not visible at the analyzer's time/voltage resolution.

**Implications:**
- Mechanism narrowed to the ESP32-S3 master peripheral itself: timing, edge-shape, sub-ns glitches, FIFO/state-machine quirks, GPIO-matrix routing artifacts, or open-drain emulation glitches at the pad.
- Hardware fixes (v8 I2C buffer) remain the architectural answer regardless. Buffer regenerates clean edges and isolates BQ from any S3-emitted artifact.
- Firmware mitigation is now worth a deep investigation as a parallel track. See **`docs/explorations/esp32-s3-i2c-master-deep-dive.md`** — full audit of the ESP32-S3 I2C master peripheral configuration knobs, community-known issues (ESP-IDF #14343, #17474, #14030, #15675; Adafruit's Troublesome Chips guidance; PlatformIO Wire-vs-IDF disambiguator), hypothesis mapping, and a ranked experiment plan with concrete code.

### Phase 24 — Experiment 1: I2C glitch filter null result (2026-05-01)

Goal: highest-priority cheap experiment from the deep-dive doc. The arduino-esp32 v2.0.14 / IDF v4.4 legacy I2C driver leaves the I2C controller's digital deglitcher OFF by default; the new IDF 5.2+ driver enables it at 7 cycles by default. If the failing-config bus produces sub-µs glitches on SDA that the analyzer integrates over but BQ rejects, enabling the filter would resolve.

Setup: added `i2c_filter_enable(I2C_NUM_0, 7)` after `Wire.begin()` and after the existing CAP_3 drive bump in [SensorManager.cpp:649-658](../../firmware/src/components/sensor/SensorManager.cpp#L649-L658). Boot log confirms `filter_enable(7)=OK`. Failing-config cable in J6, `motion-play-v7-diag` env.

Result (5 iterations, all identical):

```
TCA0  INA:.  BQ:.    TCA:.  PCA:X(2)  VCNL:X(2)
TCA1  INA:.  BQ:.    TCA:.  PCA:X(2)  VCNL:X(2)
TCA2  INA:.  BQ:X(2) TCA:.  PCA:X(2)  VCNL:X(2)
```

**Null. BQ NACK pattern on TCA2 byte-identical to Phase 23 baseline.** Filter is on (register write succeeded, return ESP_OK), but the failure is unaffected.

**Implication: refutes "sub-µs glitches at the I2C controller's input" as the missing knob.** The I2C controller's `I2C_FILTER_CFG_REG` deglitcher rejects pulses shorter than 7 × T(I2C_SCLK) on both SDA and SCL — whatever's wrong is either (a) a legitimately wide-enough pulse that the filter passes, (b) on the *output* side (master emitting something the slave rejects, not master input glitching), or (c) at a path the I2C controller's filter doesn't sit on (e.g., the pad-level input filter, or the GPIO matrix output skew).

Filter kept on in firmware — no downside, removing it for the next experiments would conflate two changes.

### Phase 25 — Experiment 2 + 3: pad-level filter and explicit internal-pull-disable (in progress)

Goals (bundled into a single firmware change to amortize flash time):

- **Experiment 2**: enable `IO_MUX_FUN_FILTER_EN` (bit 15 of `IO_MUX_GPIOn_REG`) on GPIO 43 and 44. Independent ~25 ns pulse rejection at the GPIO pad input itself, separate physical filter from `i2c_filter_enable()`. The IDF I2C driver does not enable it. The IDF v4.4 SDK header for S3 doesn't even export the macro — bit defined locally per TRM Register 6.36.
- **Experiment 3**: explicitly call `gpio_pullup_dis()` and `gpio_pulldown_dis()` on GPIO 43 and 44. Per arduino-esp32 #4887 the internal pulls don't reliably disable through `pinMode`/`Wire.begin()` alone. Phase 5 has already shown total bus pull strength isn't the mechanism, so the predicted outcome is null — but it's a free piggyback on the Phase 25 flash.

Code: see [SensorManager.cpp:649-682](../../firmware/src/components/sensor/SensorManager.cpp#L649-L682). Filter from Phase 24 is preserved; CAP_3 from Phase 23 is preserved. The accumulating change list keeps each experiment's effect additive — if any single experiment fixes the fault, we'll see it. If none of them does, we know none of {I2C-controller filter, pad-level filter, internal-pull combination, drive strength} is the gating variable, and the next move is software bit-bang (Experiment 6 in the deep-dive) to discriminate "I2C peripheral logic" from "GPIO pad / matrix output."

Pending: flash + observe diagnostic loop. Result to be filled in after the run.

---

## Current working theory

Both threshold stories at the BQ pad have been refuted by direct cursor measurement (Phases 20 and 23). The mechanism is unidentified.

- **Story D-revised — V_IH violation (REFUTED, Phase 20).** SDA's worst dip during the 9th-clock NACK window is 3.01 V, ~1.7 V above V_IH = 1.3 V. ~280 mV high-level wobble is normal SCL crosstalk, identical in ACKed and NACKed transactions.
- **Story G-revised — V_IL violation (REFUTED, Phase 23).** Drive bump to `GPIO_DRIVE_CAP_3` dropped V_OL at BQ pin 6 to peak 77 mV / floor 30 mV with cable still in; BQ still NACKs. There's no plausible V_IL the bus is crossing. The bus produces a transaction the analyzer accepts as 0xD6 but BQ silently rejects.
- **Story F — ESP32-S3 master peripheral interaction (HIGHEST-PRIORITY SURVIVING HYPOTHESIS).** ESP32-S3's I2C is GPIO-matrix-routed (no IOMUX direct path); community reports document subtle output glitches and "S3 touchier than ESP32 on same bus" patterns (Phase 19). The cable + S3 master combination may emit something on the wire — sub-nanosecond glitches, edge-shape anomalies, or timing artifacts — that the analyzer integrates over but BQ's input rejects. Discriminator: Arduino-as-master test.
- **Story H — BQ-side input-feature interaction (NEW).** BQ's I2C input may have a Schmitt deglitcher, START detector, or other feature whose timing/edge-shape sensitivity is disturbed by cable parasitics in a way not captured by simple voltage thresholds. Inferred-only if Arduino-as-master also fails. Polarity asymmetry (Phase 13) and SDA-only sensitivity (Phase 12) remain consistent under this story but unexplained mechanistically.
- **Story E — cable-mediated mechanism not yet captured (still open as catch-all).** Closed framings: cable-as-EMI-antenna (Phase 17/19), rail-perturbation (Phase 11), source-noise (Phase 14). Open: any unaccounted parasitic interaction with the master or BQ's input.

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
- **`gpio_set_drive_capability(...)` calls and `#include <driver/gpio.h>`** in `SensorManager.cpp` — added in Phase 23, no longer needed once the bus issue is resolved. Harmless to leave but unnecessary.
- **`STARTUP_I2C_SCAN` back to `false`** in `platformio.ini` (or leave on — adds ~50 ms to boot, useful diagnostic).
- **`runBusDiagnosticLoop()`** — can stay, only runs on init failure. Noisy but gated by actual fault.
- **`[PWR ...]` log lines at boot** — can stay. Low cost, useful.
- **Per-channel scan on VCNL4040 NACK** — keep. Useful always.
- **`selectChannelVerify()`** — keep. Strictly a robustness improvement.
- **`probeAndPrint()` error codes** — keep. Strictly more information, no cost.
- **`DIAG_NO_WIFI` flag / `motion-play-v7-diag` env** — keep. Zero cost, useful for future RF-related debugging.

---

## Candidate fixes

With both threshold stories refuted, fixes that target voltage levels (clock slowdown, drive-strength bump, R28 increase) are now known to NOT work — Phase 22 and 23 demonstrated this empirically. Fix candidates ranked by what's left:

1. **I2C buffer / repeater IC for BQ (v8).** P82B96 or PCA9517 between upstream I2C and BQ. Isolates BQ from any upstream perturbation regardless of mechanism — works for both surviving hypotheses (Story F master-side, Story H BQ-side input feature). Architectural answer.
2. **Replace ESP32-S3 with original ESP32 / use external I2C master IC.** Only relevant if Arduino-as-master test confirms Story F. Bigger redesign.
3. **Active I2C bus accelerator (LTC4311).** May help with edge-shape issues that the simple V_OL/V_IH model didn't catch. Worth evaluating during v8 work.

**Disproven by direct measurement (do NOT retry):**

- Slow down I2C clock (Phase 22): no effect on V_OL or BQ behavior.
- Bump GPIO drive strength to CAP_3 (Phase 23): drops V_OL ~15× but BQ still NACKs. V_OL is not the gating variable.
- Increase R28 (would lower V_OL further): same logic — V_OL isn't the issue.
- Lower R28 (Phase 7 bodge): directionally wrong even under the now-refuted V_OL story; damaged Board 1 with no test data.

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

Both threshold stories at the BQ pad have been refuted (Phases 20, 23). Mechanism is unidentified. Priority order:

1. **Arduino-as-master validation test (~30 min).** Highest-value remaining experiment. Discriminates Story F (S3 master quirk — Arduino succeeds) from Story H (BQ-side input issue — Arduino also fails). Either outcome closes a real branch. Procedure: `pio run -e motion-play-v7-relbus -t upload`, wait for "BUS RELEASED", wire Arduino Nano ESP32 (SDA/SCL/GND only, no power rails tied), flash `tools/arduino-sketches/v7_bq_master_probe/v7_bq_master_probe.ino`, read serial.
2. **Pre-test scope capture (~5 min).** With Sensepeek probes already on BQ pins 5/6 and cable in J6: capture the START condition (SDA falling edge while SCL high) at BQ pin 6, cable in vs out. Look for SCL droop during SDA fall, ringing, or coupling that could break BQ's START detection. If START looks broken with cable in, "BQ never enters address-decode" is a coherent story compatible with all current data.
3. **v8 design with I2C buffer.** P82B96 or PCA9517 between upstream I2C and BQ. Architectural answer regardless of which surviving story is right — buffer isolates BQ from any upstream perturbation. Start design in parallel with #1.

**Completed phases:**
- Phase 11 — Rail-load-only test: rail-perturbation ruled out.
- Phase 12 — Asymmetry test: SDA-specific (SCL loading harmless).
- Phase 13 — Polarity test: polarity-sensitive (SDA-to-VCC fails, SDA-to-GND works). Mechanistic explanation now unclear (was attributed to V_OL, but Phase 23 refutes that).
- Phase 14 — Clean-power-source test: source noise quality irrelevant. Story C ruled out.
- Phase 15 — Firmware bus-recovery test: software recovery doesn't help. Story A residual ruled out.
- Phase 16 — Routing-aware audit: SDA and SCL routing-symmetric. Routing-asymmetry-EMI ruled out.
- Phase 17 — BQ24195 SDA pin protection drill: no upper ESD clamp at +3.3 V. Original ESD-diode framing of Story D ruled out.
- Phase 18 — Bench-PSU-from-battery-pads test: USB-C / VBUS state ruled out. Disturbance is live/ongoing.
- Phase 19 — ESP32-S3 / TCA9548A literature search: no smoking-gun errata; S3 "touchier on marginal bus" pattern noted.
- **Phase 20 — Scope at BQ pin 6: Story D-revised refuted. SDA worst dip 3.01 V, ~1.7 V above V_IH.**
- **Phase 21 — V_OL measurement at BQ pin 6: V_OL elevation by cable confirmed (~100 mV), but Phase 23 later refutes V_OL as the gating variable.**
- **Phase 22 — I2C clock slowdown to 50 kHz: null result. No change in V_OL, wobble, or BQ behavior. Clock-rate-dependent dynamics ruled out.**
- **Phase 23 — `GPIO_DRIVE_CAP_3` drive bump: V_OL dropped to ~50 mV (peak 77, floor 30) at BQ pin 6 with cable in, BQ still NACKs. Story G-revised refuted.**
- **Phase 24 — Arduino-as-master test: SAMD21 (Nano 33 IoT) ACKs BQ on the failing-config wire that the ESP32-S3 NACKs. Story F confirmed; Story H refuted. Mechanism narrowed to the ESP32-S3 master peripheral. Spawned [esp32-s3-i2c-master-deep-dive.md](../explorations/esp32-s3-i2c-master-deep-dive.md).**
- **Phase 24 — Experiment 1 (`i2c_filter_enable(I2C_NUM_0, 7)`): null result. I2C-controller digital deglitcher is on; BQ still NACKs identically. Refutes sub-µs input glitches at the I2C controller as the gating mechanism.**
- **Phase 25 (in flight) — Experiment 2 (pad-level `IO_MUX_FUN_FILTER_EN`) + Experiment 3 (explicit `gpio_pullup_dis`/`gpio_pulldown_dis`).** Bundled into one flash. Built clean for `motion-play-v7-diag`.

**Deprioritised:**
- Clock slowdown to 10 kHz: covered by Phase 22's null result; no value in going slower.
- Increase R28 to 4.7 kΩ: would lower V_OL further but Phase 23 already proved V_OL isn't the gating variable.
- Cable-position scope test: ruled out by Phase 17/19.

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
