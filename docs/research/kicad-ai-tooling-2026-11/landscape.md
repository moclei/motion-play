---
title: AI tooling for KiCad — landscape, November 2026
date: 2026-11-04
author: research agent (Claude), for Motion Play
scope: KiCad MCP servers, the official IPC API / kicad-python, circuit-as-code, autorouting, AI design review, agent skills; compared with tools/schematic-*, tools/pcb-context
local_kicad: kicad-cli 9.0.4 (checked 2026-11-04); kiutils 1.4.8 installed; kipy not installed in KiCad's bundled Python
method: GitHub API (stars, last push, releases, read 2026-11-04), project READMEs/docs fetched 2026-11-04, KiCad dev docs, PyPI. Claims marked (unverified) come from one secondary source or vendor marketing.
---

# AI tooling for KiCad — landscape, November 2026

## 1. Plain-language summary

- There are now many "AI plugs" for KiCad. A handful are serious: one big general MCP server (mixelpixx, ~3.2k stars), one strong review-only toolkit for Claude Code (kicad-happy, ~1.6k stars), and a few smaller ones.
- None of them does anything our tools fundamentally cannot. Most of them do what we do: edit the KiCad text files directly and call `kicad-cli` for checks.
- KiCad's official "remote control" (the IPC API) still only covers the **PCB editor**, and only while KiCad is open on screen. Schematic control and headless use arrive with **KiCad 11** (expected around early 2027, not yet released).
- So "draw the wires for me" and "Update PCB from Schematic" are still done by third-party file editing everywhere. No official headless path exists today.
- One honest data point: the author of a 100-tool KiCad MCP server put it into maintenance mode after measuring that **plain Claude Code + kicad-cli beat his MCP server** on edit accuracy (18/18 vs 3/18). This supports our approach of scripts plus a coding agent.
- What's worth trying: (1) kicad-happy as a **second-opinion design review** of the v8 schematic/PCB, alongside our circuit-context; (2) Freerouting 2.5 (native macOS binary, IPC with KiCad 10) for a **routing experiment** on a scratch copy; (3) mixelpixx's wiring and `sync_schematic_to_board` tools as a **reference** for closing our wiring / Update-PCB gap, or tried on a scratch copy.
- The biggest risk on our side: **kiutils** (our parser) has had no release since Feb 2024. Moving to KiCad 10 may break it. Whatever we adopt should help us with that, not add to it.

## 2. Tools table

Activity figures come from the GitHub API on 2026-11-04. "R" = read, "W" = write. "File" = edits `.kicad_sch`/`.kicad_pcb` text, "IPC" = drives a running KiCad over the official API, "SWIG" = legacy `pcbnew` Python module (removed in KiCad 11), "CLI" = `kicad-cli`.

| Name | Link | Maintainer | Last activity | KiCad versions | Schematic R/W | PCB R/W | Mechanism | Maturity |
|---|---|---|---|---|---|---|---|---|
| **KiCAD-MCP-Server** | github.com/mixelpixx/KiCAD-MCP-Server | mixelpixx (individual + community) | push 2026-11-04; v2.8.3 2026-10-26; 3,151 stars | 9.0+ | R/W: symbols, wires (`add_schematic_wire`, pin snap), labels, no-connects, `connect_to_net`; `sync_schematic_to_board` (= F8), back-annotation | R/W: place/move, traces, vias, zones, outline; Freerouting integration | Hybrid: schematic via kicad-skip + raw S-expr splices; PCB via SWIG, ~20 commands over IPC (experimental, docs dated 2026-03-21) | Most popular, very active, 122 tools. History of file-corruption bugs (fixed in 2.2.1 and 2.7.0); flat vendor symbols break schematic tools (open, KNOWN_ISSUES 2026-09-01). New feature work moving to "Konnect" (Rust, AGPL, KiCad 10, IPC) (unverified beyond README) |
| **kicad-mcp-pro** | github.com/oaslananka/kicad-mcp-pro | oaslananka (individual) | push 2026-11-04; v4.7.0 2026-11-04; 180 stars | **10.0.x only** (9.x dropped; 11 preview) | R; W in "build" profile (via kicad-sch-api) | R; W gated; reads live board via IPC plugin | File (kicad-sch-api, sexpdata) + kicad-python IPC + CLI; SWIG banned | Fast-moving, heavy process (profiles, human-gated release). Default profile is 24 read-only tools. Own README: "first-pass… not sign-off". **Unusable on our KiCad 9.0.4** |
| **Seeed kicad-mcp-server** | github.com/Seeed-Studio/kicad-mcp-server | Seeed Studio | push 2026-10-22; no releases; 178 stars | 8.0+ (9/10 recommended) | R (components, nets, pin tracing); W experimental (add component/wire/label; "imperfect wire connections") | R (tracks, stats, SI/PI heuristics); W minimal (setup outline, Gerber) | File (manual S-expr) + CLI + optional bundled pcbnew | Analysis-oriented; editing explicitly experimental |
| **mcp-server-kicad** | github.com/ProductOfAmerica/mcp-server-kicad (fork: danidask) | ProductOfAmerica | push 2026-10-29; 16 stars; **maintenance mode** | 9.x / 10.x (CI on macOS for 10) | R/W: place, wire pin-to-net, labels, hierarchy, power symbols | R/W: footprints, traces, zones; `update_pcb_from_schematic`; Freerouting autoroute | File (byte-minimal edits) + CLI + pcbnew for fill/route | Author's own A/B test: plain Claude Code beat the plugin 18/18 vs 3/18 on single edits; recommends a coding agent + kicad-cli instead |
| **lamaalrajih/kicad-mcp** | github.com/lamaalrajih/kicad-mcp | lamaalrajih | push 2025-10-17 (stale); 532 stars | 8/9 era | R (project listing, netlist, BOM, DRC) | R | File + CLI | Early mover, now inactive |
| **daedalus/mcp-kicad** | github.com/daedalus/mcp-kicad | daedalus | push 2026-04-21; 1 star | 9+ | — | R/W via IPC | IPC (kipy) | Toy / experiment |
| **kicad-happy** | github.com/aklofas/kicad-happy | aklofas (individual) | push 2026-11-04; v3.0.0 2026-11-03; 1,585 stars; MIT | 6–10 (5 legacy) | R (own S-expr parser; no KiCad needed) | R (thermal vias, stitching, trace width vs current, DFM, impedance) + Gerber review | File (own parser), optional ngspice; Claude Code / Codex skills (11) | Most credible review tool; datasheet download + structured extraction per MPN; EMC pre-compliance (44 rules). Validation numbers are self-reported. Review only, no editing |
| **akcli** | github.com/tipoLi5890/akcli | tipoLi5890 | push 2026-08-25; v0.22; 11 stars | not stated | R/W via JSON op-lists; dry-run default; **net diff before/after**, `--strict-nets`, undo | schematic-vs-PCB verify only | File (stdlib) + CLI + bundled ngspice; Claude Code plugin | Small user base, but the design (op-lists + net-diff gate) closely mirrors ours |
| **kicad-tools (`kct`)** | github.com/rjwalters/kicad-tools | rjwalters | push 2026-11-04; v0.27.0 2026-10-31; 73 stars | 8+ files; pins 10.0.6 | R/W (wires, labels, hierarchy, symbol replace) | R/W; own A\* autorouter; LLM layout module | File (round-trip) + CLI; MCP server (`kct mcp serve`) | Very high commit churn (~8.3k commits). Wrote an evaluation rejecting kipy because it needs live KiCad |
| **circuit-synth** (+ kicad-sch-api) | github.com/circuit-synth/circuit-synth | circuit-synth | push 2026-03-08 (kicad-sch-api 2025-12-05); 291 stars | 8.0+ | W: Python → `.kicad_sch`/`.kicad_pcb`; partial import back | W: initial board only | File | Claude Code agents included; activity slowing |
| **KiCad IPC API + kicad-python (kipy)** | dev-docs.kicad.org/en/apis-and-binding/ipc-api; pypi.org/project/kicad-python | KiCad project | kipy 0.8.0 2026-08-30 | 9.0+ (groups 10; connectivity queries 10.0.1) | **None in 9/10.** Schematic-editor plugins arrive in KiCad 11 | R/W live board (items, tracks, zones, clone, flip, stackup) | IPC over Unix socket on macOS; GUI must be running in 9/10; headless via kicad-cli in 11 | Official; stable protobuf; no export/plot until 11 |
| **Freerouting** | github.com/freerouting/freerouting | freerouting org | v2.5.0 2026-10-05; push 2026-11-04; 2,177 stars | DSN/SES any; IPC with 10+ | — | W (routes) | Specctra DSN/SES; IPC on KiCad 10+; REST API; MCP `autoroute_board`; native CLI (macOS arm64/x64, no Java) | Mature baseline. Next release drops SWIG and moves fully to IPC |
| **DeepPCB plugin** | github.com/instadeepai/deeppcb-kicad-plugin | InstaDeep | push 2026-10-08; 69 stars | 6.0+ | — | W (routes) | Cloud service, credit-priced; board uploaded | Vendor completion claims unverified; privacy terms not in README |
| **Quilter** | quilter.ai | Quilter (commercial) | blog 2026 | accepts KiCad projects | — | W (placement + routing) | Cloud | Commercial; vendor claims only (unverified) |
| **Traceformer** | traceformer.io | commercial | 2026 | 7.0+ | R (datasheet-aware review) | R | Cloud upload | Commercial, pay per review (unverified) |
| **atopile / SKiDL / tscircuit** | github.com/atopile/atopile; devbisme/skidl; tscircuit/tscircuit | atopile Inc; Dave Vandenbout; tscircuit | atopile push 2026-10-14; SKiDL 3.0.0 2026-10-16; tscircuit push 2026-11-04 | various | Code → netlist (SKiDL), code → KiCad layout (atopile), code → `kicad_pcb` export (tscircuit, pours missing per open issue) | W (generated) | Own languages, export to KiCad | Mature as code-first design; would mean redesigning, not augmenting |
| **KiBot / KiRI** | github.com/INTI-CMNB/KiBot; leoheck/kiri | INTI-CMNB; leoheck | KiBot push 2026-11-03; KiRI 2026-06-22 | 5–9+ | R (outputs, visual diff) | R | CLI | Mature CI and visual-diff tools; not AI, but useful for agent checks |

Not verified: whether the `kicad-cli pcb update --netlist` command described in kicad-tools' guide exists. It does **not** exist in our 9.0.4 (`kicad-cli pcb --help` lists only drc/export/render). A July 2026 devlist proposal for `kicad-cli pcb update-from-schematic` has no evidence of a merge. kicad-mcp-pro's claim that KiCad 11 adds `kicad-cli api-server` agrees with the official docs' "headless mode through kicad-cli … for KiCad 11", but KiCad 11 is unreleased. Under KiCad's annual policy, feature merges close 2026-10-31 and the release lands around January 2027 (this timing is our inference).

## 3. Comparison with our toolset

Our stack, from `tools/CONTEXT.md`: kiutils parsing, `kicad-cli` ERC/DRC/netlist, `schematic-context/extract.py` → `circuit-context.json` with `ai_*` annotations and `_provenance`, `schematic-gen` from JSON specs, `schematic-modify/modify.py` surgical edits with `--check` scripts, and the `pcb-context` board model (`board_model.py`, net/plane reports, renders). Wiring on canvas and Update PCB are GUI-only.

**Overlaps (what we already have):**
- Read/extract: every MCP server lists components, nets and pins. Our `circuit-context.json` plus annotations and provenance is richer, and is checked for staleness. None of the others has provenance or freshness checks.
- ERC/DRC driving: everyone wraps `kicad-cli`, as we do.
- Label-based connection (`set_pin_net`, `add_local_label`, `add_wire`): mixelpixx `connect_to_net`, mcp-server-kicad pin-to-net and akcli ops do the same thing.
- PCB analysis: our board model (true pad polygons, plane ownership, return paths, method-named measurements) is deeper than any MCP server's PCB analysis. kicad-happy's PCB checks (thermal vias, current vs width, DFM, impedance) overlap partly and are complementary.

**Could replace something:**
- Nothing we should replace wholesale. The closest candidate is mixelpixx for `schematic-modify`'s generic helpers. It would cost us our `--check` discipline and add kicad-skip, which also has a flat-vendor-symbol failure mode that would hit LCSC-downloaded symbols.
- A KiCad 10 migration could make kicad-sch-api or kicad-tools' round-trip parser a **replacement for kiutils** if kiutils fails on KiCad 10 files. Watch this one. No action until we upgrade.

**Fills a gap:**
- *Datasheet-aware review:* kicad-happy (datasheet fetch + structured extraction per MPN, severity-ranked findings). We have no equivalent. This is the clearest gap-filler.
- *Netlist diff as a safety gate:* akcli's before/after net diff by pin membership is a good pattern. We could add it to `modify.py` using our own `kicad-cli` netlist export. No new dependency needed.
- *Update PCB from schematic (F8):* only third-party file-level implementations exist (mixelpixx `sync_schematic_to_board`, mcp-server-kicad `update_pcb_from_schematic`). No official headless path in KiCad 9 or 10. These would be worth reading before writing our own, or for a trial on a scratch copy. The GUI F8 remains the trustworthy path.
- *Routing:* Freerouting 2.5 (native macOS CLI, DSN/SES works with KiCad 9; IPC needs 10). kicad-tools' A\* router and DeepPCB/Quilter (cloud) also exist. For our boards, routing is mostly hand work with tight constraints (I²C, power), so autorouting is an experiment, not a replacement.
- *Live editing:* only possible for the PCB, through IPC, with KiCad open. The best route there is kipy directly (official, PCB-only), not an MCP wrapper. Live schematic editing has to wait for KiCad 11.

## 4. Risks

- **Maturity / correctness:** most MCP servers are under a year old, built largely with AI assistance (mixelpixx says so), and show corruption bugs in their changelogs (mixelpixx 2.2.1 `.kicad_sch` corruption, 2.7.0 `.kicad_sym` corruption). Vendor and author validation numbers (kicad-happy, DeepPCB, Quilter, kicad-mcp-pro "parity" badges) are self-reported.
- **Evidence that MCP wrappers can hurt:** the ProductOfAmerica A/B (3/18 vs 18/18 correct) shows a big tool menu plus "don't touch files" instructions can perform worse than an agent writing scripts. Our current model is the one that won that test.
- **Version lock:** kicad-mcp-pro requires 10.x, which rules it out for us now. KiCad 11 removes SWIG and bundled Python plugins, which breaks the SWIG halves of mixelpixx and mcp-server-kicad and the old Freerouting plugin path. Files saved in 10 can't be opened by 9. **kiutils is unmaintained** (last release 2024-02-02, last push 2024-07-10), so upgrading KiCad is a risk to our own tools first.
- **Needs KiCad running:** IPC on 9 and 10 needs the GUI open with the API server enabled (Preferences → Plugins). It doesn't work headless or in CI, and calls can time out "because KiCad is busy" (official docs). Mixing GUI edits with file-level edits in one session risks one overwriting the other (mixelpixx documents this).
- **macOS:** IPC works on macOS (Unix socket). Freerouting 2.5 ships native macOS binaries. mcp-server-kicad runs CI on macOS for KiCad 10. kicad-mcp-pro's bootstrap targets Linux. kipy is not in our KiCad's bundled Python and would need its own venv.
- **File corruption / silent connectivity change:** every file-editing tool can produce a schematic that opens but is connected differently (0.01 mm off a pin breaks a connection, per mixelpixx docs). The guard is a netlist diff plus ERC after every write, which we partly do with `--check`.
- **Data egress:** DeepPCB, Quilter and Traceformer upload the board. kicad-happy's datasheet fetching calls distributor sites, and API keys are optional.

## 5. Ranked shortlist to trial

1. **kicad-happy as a second-opinion reviewer (read-only, low risk).**
   Trial: on a scratch clone, install the plugin (`/plugin marketplace add aklofas/kicad-happy`) or check out the repo at v3.0.0. Run its schematic and PCB analyzers on `hardware/pcb-main-v8/kicad/` at the current commit. Do not let it write into the repo; send output to the scratchpad. Compare its findings with our v8 Phase 11 audit and the W3 review guide. Score: how many true issues we hadn't logged, how many false positives, and whether its datasheet extraction for 3 parts (e.g. TCA9548A, VCNL4040, the charger IC) matches the datasheets. About 1–2 h. Adopt it as a pre-fab review step if it finds at least one real issue at a tolerable noise level.

2. **Freerouting 2.5 native CLI on a routing experiment (scratch copy only).**
   Trial: download the macOS arm64 native binary. Export a Specctra DSN from a copy of the v7 board with critical nets (I²C, power) pre-routed and locked, using the KiCad 9 GUI (File → Export → Specctra DSN). Then run headless to an SES file, import it on the copy, run `kicad-cli pcb drc`, and run our `board_model.py` + `net_report.py` on the result. Question: does it route the leftover non-critical nets cleanly enough to save time? About 2 h. The IPC route needs KiCad 10, so leave it until we upgrade.

3. **Borrow, don't adopt: F8 sync and net-diff gating (reference reading, then a small change of our own).**
   Trial: read mixelpixx's `sync_schematic_to_board` and mcp-server-kicad's `update_pcb_from_schematic` (both open source) against our v8 workflow. Separately, prototype a `modify.py` wrapper in the scratchpad that exports the netlist with `kicad-cli` before and after an edit and prints a pin-membership net diff, as akcli does. Run it on one past v8 edit script. About 2 h. Output: a decision note on whether to build our own headless F8, or keep F8 in the GUI and gate with a net diff.

Not recommended now: kicad-mcp-pro (needs KiCad 10), a general-purpose MCP server as the main interface (the A/B evidence above), circuit-as-code migration (atopile/SKiDL/tscircuit would mean a redesign), and kipy/IPC work (PCB-only and GUI-bound until KiCad 11; revisit when 11.0 ships, around early 2027).

## Sources (fetched 2026-11-04)

- KiCad IPC API for add-on developers: https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/index.html
- KiCad IPC API overview: https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/
- kicad-python on PyPI: https://pypi.org/project/kicad-python/
- KiCad 10.0.0 release: https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/ ; 10.0.7: https://www.kicad.org/blog/2026/10/KiCad-10.0.7-Release/ ; 10.0.8 (status unclear): https://www.kicad.org/blog/2026/10/KiCad-10.0.8-Release/
- KiCad release policy: https://dev-docs.kicad.org/en/rules-guidelines/release-policy/
- mixelpixx: https://github.com/mixelpixx/KiCAD-MCP-Server and docs/IPC_BACKEND_STATUS.md, SCHEMATIC_TOOLS_REFERENCE.md, KNOWN_ISSUES.md
- Seeed: https://github.com/Seeed-Studio/kicad-mcp-server
- kicad-mcp-pro: https://github.com/oaslananka/kicad-mcp-pro (compatibility.yaml updated 2026-10-23)
- mcp-server-kicad: https://github.com/ProductOfAmerica/mcp-server-kicad
- kicad-happy: https://github.com/aklofas/kicad-happy
- akcli: https://github.com/tipoLi5890/akcli
- kicad-tools: https://github.com/rjwalters/kicad-tools (incl. docs/research/kipy-ipc-api-evaluation.md)
- circuit-synth: https://github.com/circuit-synth/circuit-synth
- Freerouting v2.5.0: https://github.com/freerouting/freerouting/releases/tag/v2.5.0
- DeepPCB plugin: https://github.com/instadeepai/deeppcb-kicad-plugin
- Update-from-schematic CLI proposal (devlist, July 2026): http://www.mail-archive.com/devlist@kicad.org/msg00911.html
- kiutils: https://github.com/mvnmgrx/kiutils (GitHub API: last release v1.4.8 2024-02-02)
