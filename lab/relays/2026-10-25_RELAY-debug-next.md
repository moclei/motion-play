# Relay — Debugger — Debugger (next v7 debug session) — 2026-10-25

For the user. A kickstart for the next debug-track session. It holds pointers, not state. Per the role, the handoff is `lab/STATE.md`, the open card `lab/cards/V7R-014-u3-static-low-43-vs-44.md` and the last notebook entry. Nothing here restates a result.

## 1. Before you start

- **Terminal:** a new terminal at the repo root.
  - `git status` must show `On branch debug/v7-track-3` with a clean tree (or `main`, if you merge the branch first; then tell the session to cut `debug/v7-track-4`).
  - `git config core.hooksPath` must print `.githooks`.
  - On the Mac: Local Network permission for Cursor still on (procedure §0.1); `pio`, `nc` and the USB-C Ethernet adapter as before.
- **Bench:** as left at the end of session s08 (bench-state line in the notebook entry `2026-10-25 · s08`): both boards unplugged at the Mac end, probes lifted, rigid #1 on the J6 cable, U3 on v7-clean diag, Nano on the blank sketch, scope on. Tell the session if anything has changed.
- **Card check (optional, before the session):** read V7R-014 above `--- RUN ---`. You approved the firmware change; the card itself was committed on "commit everything". If you want any change, say so first: it becomes an amendment commit before any bench step.
- **Optional:** `lab/captures/` is gitignored. If you back up captures (`tools/lab/backup_captures.sh`), V7R-012 and V7R-013 have local files in `lab/captures/V7R-012/` and `lab/captures/V7R-013/`; their cited files are already in `lab/evidence/`.

## 2. Open the session

Run plain `claude`, then paste this as your first message:

```
Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session, on branch debug/v7-track-3.
Start with the role's start-of-session steps. The open card is V7R-014 (pre-registered, not run): lab/cards/V7R-014-u3-static-low-43-vs-44.md. Last notebook entry: 2026-10-25 · s08 (cont.).
The firmware delta (u3-static, sources and hash in lab/evidence/V7R-014/src/u3/) is approved. Rebuild it from those sources in your scratchpad and check the firmware.bin hash matches firmware.sha256 before flashing; if it differs, stop and tell me.
Session helpers from the last session are in lab/evidence/V7R-014/src/session/ (serial logger with a command file for the f/r/3/4 mode commands; the frames capture script; the frame analysis script). Copy them to your scratchpad; don't edit them in place.
This is a new scope session: full validation V1–V8 at S1 before arm F, per the card (V7 in mode r, V8 in mode f). Plan probe moves per lab/templates/card.md and flag any extra move to me before making it.
The step-back checkpoint is due once V7R-014 is recorded: do it before pre-registering any further card.
Working rules for me at the bench: as in the notebook "decisions" lines of 2026-10-25 s06–s08. Also:
- Don't run a session-side action that isn't in the card's procedure (an extra reset, an extra flash) without asking me first.
```

## 3. What should happen, in order

1. **Start-up check and a five-line orientation**, then the question about bench time and boards.
2. **Rebuild and hash check** of `u3-static` (and a v7-clean worktree at 90053af for the end revert to diag).
3. **P0, then validation V1–V8 at S1.** One full placement onto C/N (V5b), then tips to A/B (V7). Last time CH2 needed a re-seat on N, CH1 needed one on A, and CH2 came loose from B once; the card's CH2 V5 must pass, because CH2 carries the counted number in arm B.
4. **Arm F (frames, reference), then A1 / B / A2** by serial command, no probe move. Raw data committed after each arm.
5. **Record** (card, log, evidence, STATE in one commit), revert U3 to diag, bench down, notebook entry.
6. **Checkpoint** (V7R-014 is the third card since V7R-011).

## 4. Known quirks (from s08; not results)

- `capture.py` sometimes reports panel Vpp CH2 invalid (9.9E37) on frame captures; the CSV is unaffected.
- `i2c_frame.py` needs the 400 kHz CSVs cropped to −30…+40 µs (`lab/evidence/V7R-009/i2c_frame/crop.py`) until the Planner relay of 2026-10-24 lands.
- After `pio run -t upload`, the serial logger must be restarted (stop it before the upload).
- The Read tool cannot render PDFs on this Mac (no poppler); s08 used pypdf in a scratch venv for datasheets.
