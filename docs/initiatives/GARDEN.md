# Garden

Small, already-scoped refinements to existing features. Outstanding items only; the Gardener removes cleared items.

- [from: v8-debug-board] `docs/references/bq24195/DATASHEET_REFERENCE.md`: remove the "minimum ILIM current 500 mA" / "2.7 kΩ clamps at 500 mA" claim (SLUSB97A §8.3.5.1 doesn't support it). Add the 100 mA-SDP → HIZ rule (§8.3.1.3.5) and the 45-min SDP timer (§8.4.1.2).
- [from: v8-debug-board] `firmware/src/main.cpp`, comment above the BQ24195 defines: the default input limit is 100 mA (OTG low at detection), not "~500 mA"; the "IINLIM=2A" setting is capped by R32 at about 1.3–1.6 A. (v8-debug-board Phase 12 also touches `configureBQ24195()`.)
- [from: v8-debug-board] `hardware/pcb-main/kicad/circuit-context.json`: R2's annotation is stale v6 text ("PMOS gate bias resistor to BAT_RAW"). On v7, R2 is the BOOST_EN pull-down. Fix via `annotate.py`, not by hand.
