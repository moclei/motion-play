# Bench instruction block

Source: `docs/research/v7-retry/test-workflow-audit.md` §4.8. Every physical step the AI hands the user uses this block. The AI sends **one step (or one short group) at a time** and waits for the report. Each instruction block goes in a message of its own, never under a results table or analysis.

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
CHECK:   The terminal (serial monitor) shows the diagnostic loop still iterating.   ← instrument/setup expectations only
         The decode band on the scope screen still shows Write:d6.
CAPTURE: Press STOP, then Save (PNG + CSV + setup). Note the file names the scope shows.
REPORT:  1. Serial: paste the last 3 iterations verbatim
         2. Scope: Vbase CH1 = ___ mV, Vbase CH2 = ___ mV (from the measurement panel)
         3. File names saved: ___
         4. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: the decode band on the scope screen no longer shows Write:d6, or anything smells/gets hot → report and wait.
```

## Rules

1. **CHECK lists only setup and instrument expectations,** never the expected measurement outcome. The prediction lives in the card and is not shown to the operator during the run ("symptoms, not guesses").
2. **The REPORT fields are pre-numbered blanks,** so the user transcribes rather than interprets.
3. **One physical action per step** where the board is powered.
4. **CHECK comes after all of DO.** The user reads CHECK only once DO is done. So a check that must happen before a later action (for example "Vpp shows on the Result panel" before a capture, or "nothing touches an X pad" before powering on) ends the block, and that action starts the next STEP. After a CHECK, only the fix for a failed check may follow ("if X, do Y").
5. **Name the screen.** The bench has three: the **scope screen** (the DHO804's display), the **board display** (the T-Display on v6) and the **terminal** (Cursor's terminal on the Mac). Every DO, CHECK and REPORT line that asks the user to look at something says which one. Never write "the screen" alone. The decode band is "the row labelled B1 / I2C at the left edge of the scope screen; byte labels such as `Write:d6` appear in that row".
