# v7 Probe Tools

## Intent
Build the two log-only probe tools that v7 debug cards 2 and 3 need but don't have yet. Card 2 needs a v6 build that prints the v7 diag loop's rows. Card 3 needs an external-master sketch that can reach VCNL 0x60 behind a sensor rigid's PCA9546A.

## Goals
- **v6 diag readout (card 2):** a tagged build for the v6 T-Display master. It prints the same banner, rows and error codes as the v7 diag loop (`t=… TCA2  INA:. BQ:X(2) …`) and loops until reset. I²C init is the same as `v6-ref`, so a card can declare it as one firmware delta against `v6-ref`.
- **PCA-aware external-master probe (card 3):** a sketch that adds `TCA<n>+PCA0` / `TCA<n>+PCA1` rows (PCA 0x76 column, VCNL 0x60 column) to the existing BASE / TCA rows. Its rows are character-compatible with the v7 diag loop, so counts compare directly. It builds for the Arduino Nano 33 IoT (SAMD21) and the Arduino Nano ESP32.
- Each tool names itself in its serial banner (tool, version or tag, I²C clock), so a card can cite exactly what ran.

## Scope
In: the two tools; a build check for each target; the tag/commit references a card cites.
Out: any change to `v7-clean`, `v6-ref`, the existing `v7_bq_master_probe` sketch, `lab/` (STATE, cards, procedures), or the product firmware on `main`. Flashing and bench runs are the debugger's job. A serial-capture lab tool belongs to `test-workflow-setup`.

## Constraints
- v6 build: `Wire.begin(43, 44)`, 400 kHz, default drive, no filters, default pulls. These stay byte-for-byte as in `v6-ref` (4da1c67), along with the Arduino core pin (`#2.0.14`).
- Probe sketch: Arduino `Wire` only. No platform-specific I²C calls, so the same source builds on SAMD21 and ESP32 cores.
- Light ceremony: user's request. Build-only verification; no bench time required to finish.
