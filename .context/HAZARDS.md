# Hazards

Known traps that waste a session's time. One trap per entry; the Gardener removes an entry once its cause is fixed.

- **pip on Python 3.7 can't find matplotlib wheels for this macOS.** pip 20.0.2 sees no wheel and tries a source build. Upgrade pip to 24.0 (the last version for 3.7) first; matplotlib 3.5.3 then installs. Done once in the user's pyenv 3.7.3 on 2026-11-02 (v8-debug-board Phase 5); see `tools/pcb-context/requirements.txt`.
