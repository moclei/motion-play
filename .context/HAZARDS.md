# Hazards

Known traps that waste a session's time. One trap per entry; the Gardener removes an entry once its cause is fixed.

- **kiutils 1.4.8 unhides every hidden field in a KiCad 8/9 schematic.** It doesn't parse `(hide yes)`, so a load + save of a KiCad-saved `.kicad_sch` makes every field visible and drops `pin_numbers`/`pin_names` hiding (536 fields on v8). Load schematics only through the KiCad 9 shim (v8-debug-board Phase 11a, `tools/schematic-modify/`); never save one with bare kiutils. Evidence: `docs/research/kicad-ai-tooling-2026-11/schematic-readability.md` §1.
- **pip on Python 3.7 can't find matplotlib wheels for this macOS.** pip 20.0.2 sees no wheel and tries a source build. Upgrade pip to 24.0 (the last version for 3.7) first; matplotlib 3.5.3 then installs. Done once in the user's pyenv 3.7.3 on 2026-11-02 (v8-debug-board Phase 5); see `tools/pcb-context/requirements.txt`.
