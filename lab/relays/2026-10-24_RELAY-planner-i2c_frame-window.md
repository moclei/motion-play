# Relay — Debugger → Planner — `i2c_frame.py`: frame window and setup/hold timing — 2026-10-24

For the Planner. Build work the debug track needs; the Debugger does not implement it. Pointers only; the results live in the cards.

## 1. Frame window (needed by any 400 kHz capture)

- **Problem:** at 400 kHz the scope build's frames sit close together. A 10 µs/div record (±80 µs around an address trigger) starts inside the frame before the 0x6B frame, and `tools/lab/i2c_frame.py` reports `NO FRAME: no START in the record …`.
- **Stopgap used in V7R-009:** the CSV is cropped to −30…+40 µs around the trigger before the tool runs. The script is `lab/evidence/V7R-009/i2c_frame/crop.py` and the deviation is recorded in the card.
- **Ask:** an option to analyse the frame that contains the trigger point, or a time window (for example `--window -30e-6 40e-6`). The output should name the window it used, and tests should cover it (`tools/lab/tests/`).
- **Check:** on the original V7R-009 CSVs, the new option must reproduce the cropped results in `lab/evidence/V7R-009/i2c_frame/` to the printed digit.

## 2. Setup/hold timing (registered in V7R-009, not yet evaluated)

- **Ask:** per master-driven address bit, measure t_SU;DAT and t_HD;DAT exactly as the card registers them. The definitions are in the **Timing** paragraph of `lab/cards/V7R-009-scope-bq-end-master-swap.md`.
- **Validation:** the method should be checked on a known-good frame (V9 reference, `lab/procedures/known-good-reference.md`) before any v7 number counts.
- **Inputs once it exists:** the V7R-009 CSVs are kept in `lab/captures/V7R-009/` (backed up to iCloud).

## 3. Not asked

- No change to the pass-table limits or to `capture.py`.
