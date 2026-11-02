# Relay — Debugger → Planner — v8 main board as a debug board (parallel respin track) — 2026-10-31

For the Planner. Opened by the user's checkpoint decision (notebook 2026-10-31, "decision: parallel respin track opened"). This track is **not evidence about the v7 I²C mechanism**. The relay holds pointers and asks; the Planner scopes it into an initiative (BRIEF / PLAN / TASKS per PROTOCOL.md).

## 1. Context (read, don't restate)
- `lab/STATE.md` §1–§4 (symptom, IS / IS NOT, map, facts) and §8.
- Notebook 2026-10-31: checkpoint @ V7R-019 (fix re-derivation, challenges 1–4) and the decision entry (user prior, design candidates).
- Cards V7R-019 (SDA from GPIO16 clears BQ + VCNL on #0003) and V7R-018 (ROM drives GPIO43 push-pull at boot; SDA lows −0.36 to −0.43 V with a rigid on J5, M not separated).
- `docs/research/v7-retry/v6-v7-changelist.md` (CL-IDs), `kicad-extraction-audit.md` (what the extractors can't show: zones, routes, staleness), `decisioning.md` §4.1–4.2.

## 2. Ask
1. **v8 goal:** a large, probe-friendly debug board, compactness not a goal (user). Test points on every I²C net (both sides of the TCA), every rail, U3's spare GPIOs; ground points beside each probe point sized for a ground spring; debug LEDs; jumper/solder-jumper pads at the decisions below.
2. **Jumper-selectable v7 configuration (so a v8 result can be A/B/A'd, P11):** at minimum (a) SDA (and SCL) master pin: GPIO43/44 vs other free pads (GPIO43/44 then free for UART0 boot log); (b) protection on the cable-facing channel lines (TVS / series R) fitted vs bypassed; (c) MCU 3.3 V and bus pull-up rail shared (v7) vs separate (v6, CL-03); (d) on-board pull-up values selectable. The Planner may add others from the changelist.
3. **Known v7 design faults to fix:** BQ24195 needing an I²C command to work (user; find the root cause in the design, don't just keep the firmware workaround); battery connection cooked #0001 and #0002 (cause unknown, not investigated methodically; a separate investigation should precede the v8 power-path design; the user can supply the boards).
4. **Design review before ordering:** decide how — the extraction tooling as the audit found it is not adequate for layout review (zones, routes, staleness). Options include fixing the extractor first (audit's 3-phase recommendation), a targeted AI review with specific questions (what touches GPIO43 / the SDA net; what protects cable-facing lines; battery/BQ power path), and a human review (e.g. r/PrintedCircuitBoard) of schematic + layout. The never-executed `routing-verification` initiative is relevant.
5. **Board count:** enough units that irreversible tests become possible (one good v7 unit today).

## 3. Inputs the debug track will add as they land
- V7R-020 (h): GPIO43 vs GPIO44 low side on #0004 / #0005 (unit vs batch/design).
  - Landed 2026-11-02 (card `lab/cards/V7R-020-gpio43-low-found-boards.md`): #0005 GPIO43 533 Ω vs #0003 534 Ω (GPIO44 31 / 34 Ω) — not #0003 alone (measured-refuted for "unit only", one sibling); batch vs design not separated. Power path (extra, argued): #0004 powered from USB, +5 V ≈ 3.75 V (vs 5.10 V on #0003), +3.3 V ≈ 2.69 V, no USB device — boost U6 not running, LDO in dropout; #0005's old image reset-looped after "Connecting to WiFi" (reset_reason 9, VSYS 4.30 V) and found no BQ at 0x6B. Inputs for the battery/power investigation.
- (j): GPIO43 static dose at the module castellation vs the board pad on #0003 (joint vs inside the module).
The Planner should not wait on these to start scoping, but they bear on (2a)/(2b) and the footprint.

## 4. Not asked
- No change to `lab/`, cards, or the debug track's order.
- No v7 rework on #0003 (the only good unit).
