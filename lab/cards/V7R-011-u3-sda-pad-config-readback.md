---
test_id: V7R-011
title: "U3 pad configuration read-back: GPIO43 (SDA) vs GPIO44 (SCL) in the failing state"
status: recorded
created: 2026-10-25
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-diag   # start and end image. Run image: V7R-011 register build u3-regs (V7R-009 scope build + read-only dump; firmware.bin 5f0d9f39), user-approved delta ("1. approved.")
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2. Nano ESP32 powered on the blank sketch throughout (power order, V7R-008)
  hardware_config: "As V7R-010 end (notebook 2026-10-25 s06): v7 #0003, no battery, J4 empty. J6: sensor rigid #1 (SW1 ON = PCA 0x76, SW2 OFF) via ~400 mm cable. J5: pigtail, black in breadboard 'V' rail with the 10 kΩ, blue + yellow dangling, red → Nano GND. TPIO43 green / TPIO44 yellow pad wires → ~175 mm Dupont → Nano A4 / A5. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Probes off the board; no scope."
variable_changed: "None on the bench (read-out card). Compared: the firmware-readable pad configuration of GPIO43 (SDA) against GPIO44 (SCL) on U3, read while the bus is in the failing state."
structure: "single (read-out of a static configuration; the comparison is GPIO43 vs GPIO44 within each dump), repeated: ≥ 5 dumps after the upload reset (R1) and ≥ 5 after a v7 power cycle (R2)"
revert_on_null: yes           # end: U3 on v7-clean motion-play-v7-diag, Nano on the blank sketch (unchanged)
---

# V7R-011 — U3 pad configuration read-back, GPIO43 (SDA) vs GPIO44 (SCL)

Map region cut: **master: pin role** (and **master: peripheral config** for drive, open-drain, pulls and filter). V7R-010 (F-13) placed U3's ~0.90 V SDA low at U3's own pad; U3's SCL lows reach ~0.1 V. This card asks whether the two pads are set up differently in the registers firmware can read. User chose STATE §8 option (b) ("let's go with (b)"), the 7th card in the master bundle region.

Correction to the V7R-010 interpretation: on the S3 the IO_MUX selects one function per pad (0 = U0TXD, 1 = GPIO matrix, 2 = CLK_OUT1 for GPIO43), so UART0 TX and the I²C controller cannot both drive GPIO43 through that selector. The "fight" picture there was imprecise. What a read-back can show is whether GPIO43 is set up differently from GPIO44.

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | GPIO43 is routed differently from GPIO44: IO_MUX function ≠ 1 (GPIO), matrix output signal ≠ I2CEXT0_SDA_OUT (90), or output/enable inversion or enable source differs | map: master: pin role; V7R-010 interpretation |
| H2 | Routing matches, but GPIO43's pad electrical setting differs from GPIO44's: drive strength (fun_drv), open-drain (od), pull-up/-down, input enable, or filter | map: master: peripheral config |
| H3 | Every firmware-readable field matches between the pads (apart from the signal index 90/89 and which pad each input select names): the SDA low difference lies outside this pad configuration (module/pad hardware, supply, or below register level) | map: master: module/path, master supply |
| M  | Read-back artefact: wrong register or bit (header macros, build), a dump taken outside the failing state, or a configuration that changes between dumps | always listed |

**Magnitude (argued, for H2).** At ~0.90 V low with the bus pull-ups (combined 1.5–2.1 kΩ, legacy, unmeasured on this config) U3 sinks ~1.1–1.6 mA, an effective pull-down of ~560–790 Ω. The S3 pad's weakest drive setting is specified at roughly 5 mA [verify: ESP32-S3 datasheet, drive strength table], i.e. tens of ohms. A drive-strength difference alone would therefore raise the low by tenths of a volt at most, not to 0.9 V; an open-drain or routing difference has no such bound. Row 3 is recorded either way, with this caveat.

## Predictions and exclusions (written before the run)
Read per dump (`[regs]` lines, both pads): `mcu_sel`, `fun_drv`, `wpu`, `wpd`, `ie`, `filt` (IO_MUX bit 15, FILTER_EN per the TRM [verify]), `od` (GPIO_PINn pad driver), `out_sig`, `out_inv`, `oen_sel`, `oen_inv`; plus `oe`/`out`/`in` (recorded, not judged: they change with bus activity) and the input selects for I2CEXT0 SDA/SCL and U0RXD.
Controls: (c1) read sanity: GPIO44 `mcu_sel=1`, `out_sig=89` (I2CEXT0_SCL_OUT), input select `scl=44`; (c2) failing state: `[scope]` lines spanning the dumps show `tca` = `ina` = n and `bq` ACK ≤ 5 % of n; (c3) no reboot within a run; (c4) ≥ 5 dumps per run.

| Outcome | Excludes | Supports (weakly) |
|---|---|---|
| Row 1: in every dump of R1 and R2, all judged fields of GPIO43 equal GPIO44's, except `out_sig` 90 vs 89; input selects `sda=43`, `scl=44`; controls pass | H1, H2 (measured-refuted for the firmware-readable pad configuration) | H3 |
| Row 2: GPIO43 `mcu_sel` ≠ 1, or `out_sig` ≠ 90, or `out_inv` / `oen_sel` / `oen_inv` differ from GPIO44's, or input select `sda` ≠ 43; consistent across dumps; controls pass | H3 | H1 (the differing field is named in the record) |
| Row 3: routing as in row 1, but `fun_drv`, `od`, `wpu`, `wpd`, `ie` or `filt` differ between the pads; consistent across dumps; controls pass | H3 | H2 (with the magnitude caveat above) |
| Row 4: a judged field changes between dumps or between R1 and R2; controls pass | — (recorded as measured; no exclusion) | M or dynamic reconfiguration; investigate |
| Row 5: a control fails (c1–c4) | — (result void) | M |

## Setup
- Readout: v7 serial logged by the session (scratch pyserial logger, host time) to `lab/captures/V7R-011/2026-10-25_V7R-011_v7_01.txt` with `=== <run>` markers; Nano port logged to `…_nano_01.txt` (blank sketch, nothing expected). Ports by USB serial (v7 44:1B:F6:C5:58:C4, Nano 34:85:18:7B:EB:38).
- Run image: `u3-regs`, built from `lab/evidence/V7R-011/src/u3/` (V7R-009 `v7_scope_bq_probe` + `dumpRegs()`; register addresses and bit positions from the core's `soc/io_mux_reg.h`, `soc/gpio_reg.h`, `soc/gpio_sig_map.h`; no register writes); same platformio env as V7R-009's `u3-scope` apart from the env name; firmware.bin 5f0d9f39, uploaded with `-t nobuild`.
- Dumps: once in setup after `Wire.begin(43, 44)`, then every 50 cycles (~5.5 s) right after the BQ probe, TCA channel 2 still open.
- Order: power on (Nano first, then v7; v7 boots diag) → session uploads `u3-regs` (R1, ≥ 60 s) → operator power-cycles the v7 at the Mac end (R2, ≥ 60 s) → session uploads `motion-play-v7-diag` from the v7-clean worktree (90053af) → bench down. No scope, no probes, no resets beyond these.

## Procedure (physical steps for the operator)
The session runs every flash and log; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| P0 | Plug in the Nano (Mac end), then the v7 | Nano enumerates (session); v7 PWR LED | done |
| R1 | Nothing (session: upload `u3-regs`, log ≥ 60 s) | — | — |
| R2 | Unplug the v7's USB-C at the Mac end, wait 5 s, plug it back in | v7 PWR LED | done |
| End | Session reverts U3 to diag; then unplug the v7, then the Nano (Mac ends) | no LEDs | bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- P0 (operator): "1. yes, 2. yes" (Nano plugged in first, then the v7; PWR LED on). Session: both ports enumerated; v7 diag boot 14:32:15, scan found 0x6B, diag rows `TCA2+PCA0/1 INA:. BQ:X(2) TCA:. PCA:. VCNL:X(2)`.
- R1 (session): `u3-regs` uploaded with `-t nobuild` (firmware.bin 5f0d9f39, hash verified) at 14:32:45; banner `[scope] sketch=v7_scope_bq_probe version=1.0 … i2c_clock=400000 Hz` at 14:32:49 (the build keeps the V7R-009 banner text). Logged to the power cycle (~14:35:05).
- R2 (operator): "1. power cycled, 2. PWR LED on". Session: re-attach 14:35:15, banner 14:35:15; logged to 14:36:13.
- End (session): U3 `motion-play-v7-diag` from the worktree at 90053af, SUCCESS; diag boot 14:36:54 (`[DIAG_NO_WIFI]`). Operator: "v7 off, nano off, no LEDs". Nano: blank throughout, log empty apart from the unplug.

### Measured values (from log; cite `lab/evidence/V7R-011/...`)
Source: `lab/evidence/V7R-011/2026-10-25_V7R-011_v7_01.txt` (blank lines removed); build source `lab/evidence/V7R-011/src/u3/`.

| Field | GPIO43 (SDA) | GPIO44 (SCL) | Same? |
|---|---|---|---|
| IO_MUX raw | 0x00001b00 | 0x00001b00 | yes |
| mcu_sel (1 = GPIO matrix) | 1 | 1 | yes |
| fun_drv | 2 | 2 | yes |
| wpu / wpd | 1 / 0 | 1 / 0 | yes |
| ie / filt | 1 / 0 | 1 / 0 | yes |
| GPIO_PIN raw, od | 0x00000004, 1 | 0x00000004, 1 | yes |
| OUT_SEL raw, out_sig | 0x0000005a, 90 (I2CEXT0_SDA_OUT) | 0x00000059, 89 (I2CEXT0_SCL_OUT) | signal index only |
| out_inv / oen_sel / oen_inv | 0 / 0 / 0 | 0 / 0 / 0 | yes |
| oe / out / in at dump time (not judged) | 1 / 1 / 1 | 1 / 1 / 1 | — |

Input selects (every dump): I2CEXT0 SDA ← GPIO43 via matrix (`sda=43 sda_mx=1`), SCL ← GPIO44 (`scl=44 scl_mx=1`); U0RXD select 60 with `u0rxd_mx=0` (not routed from 43/44).
Dumps: R1 29 per line type, R2 13; every dump identical to every other, within and across runs. Controls: (c1) GPIO44 `mcu_sel=1`, `out_sig=89`, `scl=44` — pass; (c2) `[scope]` R1 14:32:50 → 14:35:05, n 10 → 1360, 136 lines; R2 14:35:16 → 14:36:13, n 10 → 580, 58 lines; every line `tca` = `ina` = n, `bq=0`, `bq_codes=2222222222` — pass; (c3) no reboot within a run — pass; (c4) ≥ 5 dumps per run — pass.

### Interpretation (session; labelled as such)
Interpretation: as far as firmware can read them, U3's SDA and SCL pads are set up identically: same IO_MUX function (GPIO matrix), open-drain, drive 2, pull-up on, filter off, no inversion, each driven by its own I²C controller signal and read back by the controller from its own pad. Nothing in this configuration explains why SDA's low sits at ~0.90 V while SCL's reaches ~0.1 V. The difference lies outside these registers: the GPIO43 pad or its path inside the WROOM module, its supply, or something on the SDA net sinking or sourcing current that firmware cannot see. A UART0 routing onto GPIO43 is not present at run time (mcu_sel 1, out_sig 90); what the ROM does before `Wire.begin()` is not covered by this read.

## Conclusion
- Outcome row matched: row 1 — in all 42 dumps (R1 29, R2 13) every judged field of GPIO43 equals GPIO44's except `out_sig` 90 vs 89; input selects `sda=43`, `scl=44`; controls c1–c4 pass.
- Hypotheses excluded: H1 (routing differs) and H2 (pad electrical setting differs) — measured-refuted for the firmware-readable pad configuration at run time. H3 weakly supported. M not supported: the macros come from the core's own headers, the GPIO44 control reads as expected, and the dumps are constant.
- **Strength:** measured-refuted (H1, H2; one board, one image family, two boots, 42 dumps); scope limited to registers firmware can read at run time; `lab/evidence/V7R-011/`
- Deviations: (1) the build prints the V7R-009 banner text (`sketch=v7_scope_bq_probe`); the build is identified by its `[regs]` lines and firmware.bin 5f0d9f39. (2) R1 ran ~135 s, not ~60 s (the session counted 13 dumps at 55 s and the run continued until the operator's power cycle); more dumps, no change in method.
- Revert-on-null done: yes (not a null; revert per card) — U3 on v7-clean motion-play-v7-diag (90053af), Nano on the blank sketch, both boards unplugged
- Result commit: self
