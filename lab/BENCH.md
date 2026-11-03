# Bench — boards, fixtures, what's flashed

> Shared by every investigation in `lab/investigations/`. Cite card IDs, as STATE does. A card that changes a board or what's flashed updates this file in the same commit. Content moved verbatim from `lab/investigations/v7-i2c/STATE.md` §6 at V7R-020 (2026-11-02); the Investigations column is new.

## Boards
| ID | Condition | Mods | Role | Investigations |
|---|---|---|---|---|
| v6 | healthy | ~10 mm wire on pad C (U2.14, GND), V7R-001 | known-good reference, on the bench. | v7-i2c |
| v7 #0003 (barcode; probably not legacy B3: user found a separate board marked "Board #3" in marker, 2026-10-27; history unknown; U3 die rev v0.2) | healthy | ~68 mm 26 AWG wires soldered on TPIO43 (green) and TPIO44 (yellow), fitted before V7R-004; ~170 mm grey Dupont jumper soldered on TPIO16 (male pin taped, off the net), V7R-019 | the v7 on the bench; treated as the only good unit. | v7-i2c |
| Arduino Nano ESP32 (S3 rev v0.1) | healthy | none | external S3 master (V7R-004). | v7-i2c |
| YD-ESP32-23 (2022-V1.3, WROOM-1-N16R8, die rev v0.2, MAC 98:88:e0:04:3c:14) | healthy | none | module control (V7R-017). | v7-i2c |
| Legacy: v7 B1 | bodge-damaged (L-Ph7) | rework | none. | v7-i2c |
| v7 B2 | BQ I²C open (L-Ph8), never reflowed? | none known | symptom identity: causal, if it still exists. | v7-i2c |
| v7 #0005 (sharpie; was "Board #3", likely legacy B3, argued; old image found no BQ at 0x6B, which fits B2, so mapping uncertain; v0.2, MAC 44:1b:f6:c5:58:a4) | boots on USB; old image brownout reset loop | none | GPIO43 533 Ω (V7R-020); power reference (PWR intake). | v7-i2c, power |
| v7 #0004 (sharpie; unmarked before) | no USB device; +5 V ≈ 3.75 V, +3.3 V ≈ 2.69 V powered (V7R-020) | none | power-path case. | v7-i2c, power |
| v7 #0001, #0002 (user names; no barcodes) | "burnt out" after a 30Q 18650 in BT1 in legacy testing (user); binned (user, 2026-11-02) | none known | gone; mapping to legacy B1/B2 unknown. | v7-i2c, power |

#0004 could be B1, B2 or a spare.

## Fixtures
- Failing config fixtures (v7-i2c): cable in J6 with 10 kΩ SDA→+3.3 V at the far end, SCL wire dangling (L-Ph12); sensor rigid on J4/J5/J6.

## Flashed now
Board → commit + env, with the card ID that set it.
- v6 → v6-ref 4da1c67, lilygo-t-display-s3 (V7R-002 S2 step F). v7 #0003 → v7-clean 90053af, motion-play-v7-diag binary 166f5f40 (SHA-1; `lab/evidence/V7R-018/diag-166f5f40.bin`; reflashed at V7R-020 End, 2026-11-02 11:18:16). #0005 → u3-static 3c23d99a (V7R-020; left on it, user). #0004 → as found (never flashed this track). Nano ESP32 → blank sketch, 2.0.18 hwcdc build (V7R-009 revert; not reflashed since). YD → yd-static 56a0ef90 (V7R-017; left on it, user).

## Bench at last stop
- Bench at last stop (notebook 2026-11-02, V7R-020): scope probes **parked off the board** (V7R-020 S1c incident; re-seat + V1–V8 before any scope card). **Rigid #1 in J6** (SW1 ON, SW2 OFF); **J6 pigtail now in J5** (black 'V' rail, red Nano GND, blue row 15 / 10 kΩ, yellow dangling). Grey TPIO16 jumper taped, not on the net. v7 #0003 (diag) and Nano (blank) plugged in and powered; v7 = `/dev/cu.usbmodem14301`, Nano = `/dev/cu.usbmodem14101`. #0004, #0005, YD unplugged.
