# probe_points

Board pictures for bench procedures: a KiCad 3D render of the top side with red (#ff1744) circles on the pads to probe, zoom panels, and a legend. It made `lab/procedures/img/v6-probe-points.png` and `v7-probe-points.png`.

## Usage

```sh
# v7 picture from the board at the commit named in v7.json (source.ref)
python3 tools/lab/probe_points/probe_points.py render \
    --points tools/lab/probe_points/v7.json --out /tmp/v7-probe-points.png

# another board or commit
... render --points P.json --ref <commit> [--path <board path>] --out OUT.png
... render --points P.json --board path/to/board.kicad_pcb --out OUT.png

# authoring helpers: pad centres of footprints, pads near a point (mm)
python3 tools/lab/probe_points/probe_points.py pads --ref c2acffc U5 C21
python3 tools/lab/probe_points/probe_points.py near --ref c2acffc 95.99 122.89 --radius 0.5
```

`render` writes `OUT.png` and an `OUT.png.meta.json` provenance sidecar (source path, commit, source sha256, points file, calibration). Work files (render, SVG, screenshot) go to a temp dir or `--work DIR`. The kicad-cli render takes about 2.5 minutes at 6400×4800; `--render-png` reuses an earlier render of the same board. `--pngquant` compresses the output (the committed v7 picture was compressed this way).

Requirements: macOS paths by default. `kicad-cli` 9.0.4 at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` (`--kicad-cli` or `$KICAD_CLI`), Google Chrome (`--chrome` or `$CHROME`), git. Stdlib Python 3.7+.

## Method

1. `kicad-cli pcb render --side top --quality high --width 6400 --height 4800` (transparent background). kicad-cli trims the requested size (6400×4800 gives 6384×4792), so the image size is read from the PNG header, never assumed.
2. The board's pixel bbox is the bbox of the opaque pixels (alpha > 128), decoded in pure Python. The mm bbox is the Edge.Cuts bbox from the board file. The two give the px/mm scale in x and y; they should agree within 1 %, and a warning says if they don't (something overhanging the board edge).
3. Each marker is placed at a footprint pad centre (reference + pad number, footprint rotation applied), so nothing is placed by eye. The SVG overlay embeds the render once and shows it through panel windows given in board mm.
4. Headless Chrome rasterises the SVG (`--headless --screenshot --window-size`). qlmanage is not used: it crops.

Then look at the result and check every marker sits on its pad.

**Boards from git:** `--ref` runs `git show <ref>:<path>` into the work dir (default path `hardware/pcb-main/kicad/motion-play-main.kicad_pcb`). v6 is `fd632ef`, v7 is `c2acffc`. 3D models with a path relative to the board directory (e.g. `SN74AHCT125PWR.stp`) are not found from the work dir, so that part may render without its 3D body; the approved pictures were made the same way.

**Freshness:** `check_state.py --fresh OUT.png` compares the sidecar's `source_sha256` with the working-tree board. For a picture of an old commit (v6), STALE only means the board has moved on; `source_ref` records the commit pictured.

## Points file

JSON. Top level: `source` (`ref`, `path`: the default board), `render` (`side`, `quality`, `width`, `height`), `width` (output px, 1600), `bottom` (px below the last block), `blocks`.

Blocks are laid out top to bottom; each `space` is the px from the previous block's baseline or bottom edge.

- `{"type": "text", "space", "text", "size", "bold", "fill"}`. `{commit}` in the text becomes the source commit.
- `{"type": "panel", "id", "space", "window_mm": [x0, y0, x1, y1], "x", "width", "boxes", "markers", "legend", "legend_space"}`. A box `{"panel": "<id>", "label"}` outlines another panel's window. With `legend: true` the markers' `legend` strings are listed under the panel.
- A marker: `{"label", "ref", "pad", "legend", "r", "font", "stroke", "halo", "dx", "dy", "offset_mm"}`. `at_mm: [x, y]` replaces `ref`/`pad` for a point that is not a pad (warned).
