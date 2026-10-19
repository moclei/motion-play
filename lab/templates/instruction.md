# Bench instruction block

Source: `docs/research/v7-retry/test-workflow-audit.md` §4.8. Every physical step the AI hands the user uses this block. The AI sends **one step (or one short group) at a time** and waits for the report.

```
STEP S<n> of <total> — <V7R-NNN> arm <A1|B|A2|Sn|val> (<one-line condition>)
DO:      <the physical action>
CHECK:   <setup and instrument expectations only>
CAPTURE: <what to save, e.g. Press STOP, then Save (PNG + CSV + setup). Note the file names the scope shows.>
REPORT:  1. <pre-numbered blank, e.g. Serial: paste the last 3 iterations verbatim>
         2. <pre-numbered blank, e.g. Scope: Vbase CH1 = ___ mV (from the measurement panel)>
         3. File names saved: ___
         4. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: <abort conditions>, or anything smells/gets hot → report and wait.
```

Example:

```
STEP S3 of 7 — V7R-012 arm B (cable in)
DO:      Plug the failing-config cable into J6. Do not touch the probe arms.
CHECK:   Serial shows the diagnostic loop still iterating.   ← instrument/setup expectations only
         Decode still shows D6 on screen.
CAPTURE: Press STOP, then Save (PNG + CSV + setup). Note the file names the scope shows.
REPORT:  1. Serial: paste the last 3 iterations verbatim
         2. Scope: Vbase CH1 = ___ mV, Vbase CH2 = ___ mV (from the measurement panel)
         3. File names saved: ___
         4. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: decode no longer shows D6, or anything smells/gets hot → report and wait.
```

## Rules

1. **CHECK lists only setup and instrument expectations,** never the expected measurement outcome. The prediction lives in the card and is not shown to the operator during the run ("symptoms, not guesses").
2. **The REPORT fields are pre-numbered blanks,** so the user transcribes rather than interprets.
3. **One physical action per step** where the board is powered.
