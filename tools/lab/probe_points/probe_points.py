#!/usr/bin/env python3
"""Probe-point pictures: a KiCad 3D render of a board with red markers on named pads.

Pipeline (each step is deliberate; see README.md for why):
  1. `kicad-cli pcb render` (top side, high quality) -> render PNG.
  2. The PNG size is read from its header (kicad-cli trims the requested size),
     and the board's pixel bbox is measured from the PNG alpha channel.
     pixel <-> mm calibration = that bbox against the Edge.Cuts bbox.
  3. Marker positions come from footprint pad centres (reference + pad number),
     so nothing is placed by eye. An SVG overlay draws every marker, box and
     label in #ff1744 over the render.
  4. Headless Chrome rasterises the SVG (`--headless --screenshot`). qlmanage
     is not used: it crops.

Subcommands:
  render  --points P.json --out OUT.png [--board F | --ref R [--path P]]
  pads    [--board F | --ref R [--path P]] REF [REF ...]   print pad centres
  near    [--board F | --ref R [--path P]] X Y [--radius MM] list pads near a point

Stdlib only (Python 3.7+). The board file is parsed programmatically and only
the numbers needed are printed; never read a .kicad_pcb into context.
"""
import argparse
import base64
import datetime
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from xml.sax.saxutils import escape

RED = "#ff1744"
KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_BOARD_PATH = "hardware/pcb-main/kicad/motion-play-main.kicad_pcb"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def die(msg, code=2):
    sys.stderr.write("probe_points: %s\n" % msg)
    sys.exit(code)


# ------------------------------------------------------------------ board source

def load_board(args, points=None, work=None):
    """Return (board_file, provenance dict). A git ref is extracted with `git show`."""
    src = (points or {}).get("source", {})
    board = args.board
    ref = args.ref or (None if board else src.get("ref"))
    path = args.path or src.get("path") or DEFAULT_BOARD_PATH
    if board:
        data = open(board, "rb").read()
        rel = os.path.relpath(os.path.abspath(board), REPO)
        return board, {"source": rel, "source_ref": None,
                       "source_sha256": hashlib.sha256(data).hexdigest()}
    if not ref:
        die("no board: pass --board FILE, or --ref REF [--path PATH], or set source.ref in the points file")
    try:
        data = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    except subprocess.CalledProcessError as e:
        die("git show %s:%s failed: %s" % (ref, path, e.stderr.decode().strip()))
    commit = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", ref],
                            stdout=subprocess.PIPE, check=True).stdout.decode().strip()
    work = work or tempfile.mkdtemp(prefix="probe_points_")
    out = os.path.join(work, "board_%s.kicad_pcb" % commit)
    with open(out, "wb") as f:
        f.write(data)
    return out, {"source": path, "source_ref": commit,
                 "source_sha256": hashlib.sha256(data).hexdigest()}


# ------------------------------------------------------------------ .kicad_pcb parsing

TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


def parse_sexpr(text):
    stack = [[]]
    for t in TOKEN.findall(text):
        if t == "(":
            stack.append([])
        elif t == ")":
            node = stack.pop()
            stack[-1].append(node)
        else:
            stack[-1].append(t[1:-1] if t.startswith('"') else t)
    return stack[0][0]


def kids(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


class Board:
    def __init__(self, path):
        with open(path, encoding="utf-8") as f:
            self.tree = parse_sexpr(f.read())
        self.pads = {}      # (ref, pad) -> list of dicts (a pad number can repeat, e.g. thermal pads)
        self.fp_layer = {}
        for fp in kids(self.tree, "footprint"):
            ref = None
            for p in kids(fp, "property"):
                if len(p) > 2 and p[1] == "Reference":
                    ref = p[2]
            for p in kids(fp, "fp_text"):
                if len(p) > 2 and p[1] == "reference":
                    ref = p[2]
            if ref is None:
                continue
            at = kids(fp, "at")[0]
            fx, fy = float(at[1]), float(at[2])
            fr = float(at[3]) if len(at) > 3 else 0.0
            self.fp_layer[ref] = kids(fp, "layer")[0][1]
            a = math.radians(-fr)  # KiCad: positive rotation is CCW on screen (y down)
            for pad in kids(fp, "pad"):
                pa = kids(pad, "at")[0]
                px, py = float(pa[1]), float(pa[2])
                x = fx + px * math.cos(a) - py * math.sin(a)
                y = fy + px * math.sin(a) + py * math.cos(a)
                net = kids(pad, "net")
                net = (net[0][2] if len(net[0]) > 2 else net[0][1]) if net else ""
                size = kids(pad, "size")
                size = (float(size[0][1]), float(size[0][2])) if size else (0.0, 0.0)
                self.pads.setdefault((ref, str(pad[1])), []).append(
                    {"ref": ref, "pad": str(pad[1]), "x": x, "y": y, "size": size, "net": net,
                     "layer": self.fp_layer[ref]})

    def edge_bbox(self):
        xs, ys = [], []

        def add(n):
            for k in ("start", "end", "mid"):
                for p in kids(n, k):
                    xs.append(float(p[1]))
                    ys.append(float(p[2]))
            for pts in kids(n, "pts"):
                for p in kids(pts, "xy"):
                    xs.append(float(p[1]))
                    ys.append(float(p[2]))

        for g in self.tree:
            if not (isinstance(g, list) and g and g[0] in ("gr_line", "gr_rect", "gr_arc", "gr_circle", "gr_poly")):
                continue
            if not any(l[1] == "Edge.Cuts" for l in kids(g, "layer")):
                continue
            if g[0] == "gr_circle":
                c, e = kids(g, "center")[0], kids(g, "end")[0]
                cx, cy = float(c[1]), float(c[2])
                r = math.hypot(float(e[1]) - cx, float(e[2]) - cy)
                xs += [cx - r, cx + r]
                ys += [cy - r, cy + r]
            else:
                add(g)
        if not xs:
            die("no Edge.Cuts graphics found in the board file")
        return min(xs), min(ys), max(xs), max(ys)

    def pad(self, ref, pad):
        hits = self.pads.get((ref, str(pad)))
        if not hits:
            die("pad %s.%s not found in the board" % (ref, pad))
        if len(hits) > 1:
            sys.stderr.write("probe_points: warning: %s.%s has %d pads; using the first\n" % (ref, pad, len(hits)))
        return hits[0]


# ------------------------------------------------------------------ PNG: size and alpha bbox

def png_alpha_bbox(path, threshold=128):
    """Return (w, h, (x0, y0, x1, y1)) of pixels with alpha > threshold (inclusive bounds).

    Pure Python: only the alpha channel is un-filtered (PNG filters are per byte
    offset, so one channel can be decoded on its own)."""
    d = open(path, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        die("%s is not a PNG" % path)
    i, idat = 8, []
    w = h = ct = bd = None
    while i < len(d):
        n, = struct.unpack(">I", d[i:i + 4])
        t = d[i + 4:i + 8]
        if t == b"IHDR":
            w, h, bd, ct, _, _, il = struct.unpack(">IIBBBBB", d[i + 8:i + 21])
            if il:
                die("interlaced PNG not supported")
        elif t == b"IDAT":
            idat.append(d[i + 8:i + 8 + n])
        i += 12 + n
    if bd != 8 or ct != 6:
        die("%s: need 8-bit RGBA (kicad-cli renders with a transparent background); got depth %s type %s"
            % (path, bd, ct))
    raw = zlib.decompress(b"".join(idat))
    stride = w * 4
    gate = bytes(1 if v > threshold else 0 for v in range(256))
    prev = bytearray(w)
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        o = y * (stride + 1)
        f = raw[o]
        line = bytearray(raw[o + 4:o + 1 + stride:4])  # alpha bytes of this row, still filtered
        if f == 1:
            acc = 0
            for x in range(w):
                acc = (acc + line[x]) & 255
                line[x] = acc
        elif f == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif f == 3:
            left = 0
            for x in range(w):
                left = (line[x] + ((left + prev[x]) >> 1)) & 255
                line[x] = left
        elif f == 4:
            left = upleft = 0
            for x in range(w):
                up = prev[x]
                p = left + up - upleft
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - upleft)
                pr = left if (pa <= pb and pa <= pc) else (up if pb <= pc else upleft)
                left = (line[x] + pr) & 255
                line[x] = left
                upleft = up
        m = bytes(line).translate(gate)
        a = m.find(b"\x01")
        if a >= 0:
            b = m.rfind(b"\x01")
            x0, x1 = min(x0, a), max(x1, b)
            y0 = min(y0, y)
            y1 = y
        prev = line
    if x1 < 0:
        die("%s: no opaque pixels" % path)
    return w, h, (x0, y0, x1, y1)


def png_size(path):
    d = open(path, "rb").read(24)
    return struct.unpack(">II", d[16:24])


# ------------------------------------------------------------------ SVG overlay

class Overlay:
    def __init__(self, board, img_path, cal, width, subst):
        self.board, self.cal, self.W, self.subst = board, cal, width, subst
        self.o = []
        self.marks = []     # (label, ref, pad, x_mm, y_mm, panel) for the report
        with open(img_path, "rb") as f:
            self.b64 = base64.b64encode(f.read()).decode()

    def P(self, x, y):
        c = self.cal
        return c["px0"] + c["sx"] * (x - c["mx0"]), c["py0"] + c["sy"] * (y - c["my0"])

    def text(self, x, y, s, size, bold=False, fill="#111", outline=False):
        extra = ' font-weight="bold"' if bold else ""
        if outline:
            extra += ' stroke="#fff" stroke-width="1.5"'
        self.o.append('<text x="%.2f" y="%.2f" font-size="%s"%s fill="%s">%s</text>'
                      % (x, y, size, extra, fill, escape(s)))

    def where(self, m):
        if "ref" in m:
            p = self.board.pad(m["ref"], m["pad"])
            return p["x"] + m.get("offset_mm", [0, 0])[0], p["y"] + m.get("offset_mm", [0, 0])[1]
        if "at_mm" in m:
            sys.stderr.write("probe_points: warning: marker %s placed by at_mm, not by a pad\n" % m.get("label"))
            return m["at_mm"]
        die("marker %s needs ref+pad (or at_mm)" % m.get("label"))

    def panel(self, spec, y):
        x0, y0, x1, y1 = spec["window_mm"]
        ox, width = spec.get("x", 20), spec.get("width", self.W - 40)
        bx0, by0 = self.P(x0, y0)
        bx1, by1 = self.P(x1, y1)
        k = width / (bx1 - bx0)
        h = (by1 - by0) * k
        self.o.append('<svg x="%.2f" y="%.2f" width="%.2f" height="%.2f" viewBox="%.3f %.3f %.3f %.3f">'
                      '<use xlink:href="#render"/></svg>' % (ox, y, width, h, bx0, by0, bx1 - bx0, by1 - by0))

        def f(xm, ym):
            px, py = self.P(xm, ym)
            return ox + (px - bx0) * k, y + (py - by0) * k

        return f, h

    def marker(self, f, m, panel_id):
        xm, ym = self.where(m)
        cx, cy = f(xm, ym)
        r, fs = m.get("r", 20), m.get("font", 30)
        sw = m.get("stroke", r / 8.0 + 2)
        halo = m.get("halo", r / 4.0 + 3)
        self.o.append('<circle cx="%.2f" cy="%.2f" r="%s" fill="none" stroke="#fff" stroke-width="%.2f"/>'
                      '<circle cx="%.2f" cy="%.2f" r="%s" fill="none" stroke="%s" stroke-width="%.2f"/>'
                      % (cx, cy, r, halo, cx, cy, r, RED, sw))
        tx = cx + m.get("dx", r + 6)
        ty = cy + m.get("dy", fs / 3.0)
        self.text(tx, ty, m["label"], fs, bold=True, fill=RED, outline=True)
        self.marks.append((m["label"], m.get("ref"), m.get("pad"), xm, ym, panel_id))

    def box(self, f, b):
        win = b.get("window_mm") or self.panels_spec[b["panel"]]["window_mm"]
        a, c = f(win[0], win[1])
        e, g = f(win[2], win[3])
        self.o.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="#fff" stroke-width="7"/>'
                      '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="none" stroke="%s" stroke-width="4"/>'
                      % (a, c, e - a, g - c, a, c, e - a, g - c, RED))
        if b.get("label"):
            self.text(a, c - 10, b["label"], b.get("font", 26), bold=True, fill=RED, outline=True)

    def build(self, blocks, bottom=40):
        # boxes may name a panel that is drawn later, so index the panels first
        self.panels_spec = {b["id"]: b for b in blocks if b.get("type") == "panel" and "id" in b}
        y = 0.0
        for b in blocks:
            t = b["type"]
            y += b.get("space", 0)
            if t == "text":
                self.text(b.get("x", 20), y, b["text"].format(**self.subst), b.get("size", 25), bold=b.get("bold", False),
                          fill=b.get("fill", "#111"))
            elif t == "panel":
                f, h = self.panel(b, y)
                for bx in b.get("boxes", []):
                    self.box(f, bx)
                for m in b.get("markers", []):
                    self.marker(f, m, b.get("id"))
                y += h
                if b.get("legend"):
                    y += b.get("legend_space", 45)
                    for i, m in enumerate(b.get("markers", [])):
                        self.legend_line(y + i * 36, m["label"], m["legend"])
                    y += 36 * (len(b.get("markers", [])) - 1)
            else:
                die("unknown block type %r" % t)
        total = int(math.ceil(y + bottom))
        head = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                'width="%d" height="%d" viewBox="0 0 %d %d" font-family="Helvetica,Arial,sans-serif">'
                % (self.W, total, self.W, total),
                '<defs><image id="render" width="%d" height="%d" xlink:href="data:image/png;base64,%s"/></defs>'
                % (self.cal["img_w"], self.cal["img_h"], self.b64),
                '<rect width="%d" height="%d" fill="#fff"/>' % (self.W, total)]
        return "\n".join(head + self.o + ["</svg>"]), total

    def legend_line(self, y, label, s):
        self.o.append('<text x="20" y="%.2f" font-size="25" fill="#111"><tspan font-weight="bold" fill="%s">%s'
                      '</tspan>  %s</text>' % (y, RED, escape(label), escape(s)))


# ------------------------------------------------------------------ commands

def run(cmd, **kw):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    if r.returncode != 0:
        die("command failed (%d): %s\n%s" % (r.returncode, " ".join(cmd), r.stdout.decode(errors="replace")[-2000:]))
    return r.stdout.decode(errors="replace")


def cmd_render(args):
    with open(args.points, encoding="utf-8") as f:
        points = json.load(f)
    work = args.work or tempfile.mkdtemp(prefix="probe_points_")
    os.makedirs(work, exist_ok=True)
    board_file, prov = load_board(args, points, work)
    board = Board(board_file)
    r = points.get("render", {})
    if args.render_png:
        img = args.render_png
        print("render: reusing %s" % img)
    else:
        img = os.path.join(work, "render.png")
        cmd = [args.kicad_cli, "pcb", "render", "--side", r.get("side", "top"),
               "--quality", r.get("quality", "high"),
               "--width", str(r.get("width", 6400)), "--height", str(r.get("height", 4800)),
               "-o", img, board_file]
        print("render: %s (takes a few minutes at 6400x4800)" % " ".join(cmd))
        run(cmd)
    w, h, (x0, y0, x1, y1) = png_alpha_bbox(img)
    mx0, my0, mx1, my1 = board.edge_bbox()
    sx = (x1 + 1 - x0) / (mx1 - mx0)
    sy = (y1 + 1 - y0) / (my1 - my0)
    cal = {"img_w": w, "img_h": h, "px0": x0, "py0": y0, "mx0": mx0, "my0": my0, "sx": sx, "sy": sy}
    print("image %dx%d (measured); board alpha bbox x %d..%d, y %d..%d px" % (w, h, x0, x1, y0, y1))
    print("Edge.Cuts %.3f..%.3f x %.3f..%.3f mm -> %.3f / %.3f px/mm (x / y)" % (mx0, mx1, my0, my1, sx, sy))
    if abs(sx / sy - 1) > 0.01:
        sys.stderr.write("probe_points: warning: x and y scales differ by %.1f%%; something in the render "
                         "probably overhangs the board edge, so the bbox is not the board\n" % (100 * abs(sx / sy - 1)))
    for ref in sorted({m["ref"] for b in points["blocks"] for m in b.get("markers", []) if "ref" in m}):
        if board.fp_layer.get(ref, "F.Cu") != "F.Cu" and r.get("side", "top") == "top":
            sys.stderr.write("probe_points: warning: %s is on %s, not visible from the top\n" % (ref, board.fp_layer[ref]))
    ov = Overlay(board, img, cal, points.get("width", 1600),
                 {"commit": prov["source_ref"] or "working tree", "source": prov["source"]})
    svg, total = ov.build(points["blocks"], points.get("bottom", 40))
    svg_path = os.path.join(work, "overlay.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)
    for label, ref, pad, xm, ym, pid in ov.marks:
        print("  %-2s %-10s (%.3f, %.3f) mm  panel %s" % (label, "%s.%s" % (ref, pad) if ref else "at_mm", xm, ym, pid))
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shot = os.path.join(work, "shot.png")
    run([args.chrome, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
         "--window-size=%d,%d" % (ov.W, total), "--screenshot=%s" % shot, "file://" + os.path.abspath(svg_path)])
    sw, sh = png_size(shot)
    if (sw, sh) != (ov.W, total):
        sys.stderr.write("probe_points: warning: screenshot is %dx%d, expected %dx%d\n" % (sw, sh, ov.W, total))
    if args.pngquant:
        q = shutil.which("pngquant")
        if not q:
            die("--pngquant given but pngquant is not on PATH")
        run([q, "--force", "--output", out, "256", shot])
    else:
        shutil.copyfile(shot, out)
    head = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], stdout=subprocess.PIPE).stdout.decode().strip()
    meta = {"_provenance": dict(prov, generator="tools/lab/probe_points/probe_points.py", generator_commit=head,
                                generated=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                                points=os.path.relpath(os.path.abspath(args.points), REPO),
                                points_sha256=hashlib.sha256(open(args.points, "rb").read()).hexdigest(),
                                kicad_cli=run([args.kicad_cli, "--version"]).strip() if not args.render_png else None,
                                calibration=cal)}
    with open(out + ".meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    print("wrote %s (%dx%d) and %s.meta.json; work files in %s" % (out, sw, sh, out, work))


def cmd_pads(args):
    board = Board(load_board(args)[0])
    for ref in args.refs:
        pads = sorted((p for (r, _), ps in board.pads.items() if r == ref for p in ps), key=lambda p: p["pad"])
        if not pads:
            print("%s: not found" % ref)
        for p in pads:
            print("%s.%s  (%.3f, %.3f) mm  size %.2fx%.2f  %s  %s" % (ref, p["pad"], p["x"], p["y"],
                                                                     p["size"][0], p["size"][1], p["layer"], p["net"]))


def cmd_near(args):
    board = Board(load_board(args)[0])
    hits = []
    for ps in board.pads.values():
        for p in ps:
            d = math.hypot(p["x"] - args.x, p["y"] - args.y)
            if d <= args.radius:
                hits.append((d, p))
    for d, p in sorted(hits, key=lambda t: t[0]):
        print("%.3f mm  %s.%s  (%.3f, %.3f)  size %.2fx%.2f  %s  %s" % (d, p["ref"], p["pad"], p["x"], p["y"],
                                                                     p["size"][0], p["size"][1], p["layer"], p["net"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    def src(p):
        p.add_argument("--board", help="a .kicad_pcb file")
        p.add_argument("--ref", help="git ref to take the board from (with --path)")
        p.add_argument("--path", help="board path in the repo for --ref (default: %s)" % DEFAULT_BOARD_PATH)

    r = sub.add_parser("render", help="make a probe-point picture")
    src(r)
    r.add_argument("--points", required=True, help="points JSON (see README.md)")
    r.add_argument("--out", required=True, help="output PNG; a <out>.meta.json provenance sidecar is written beside it")
    r.add_argument("--work", help="directory for the render, overlay SVG and screenshot (default: a new temp dir)")
    r.add_argument("--render-png", help="reuse an existing kicad-cli render of the same board (skips the render)")
    r.add_argument("--pngquant", action="store_true", help="compress the output with pngquant (256 colours)")
    r.add_argument("--kicad-cli", default=os.environ.get("KICAD_CLI", KICAD_CLI))
    r.add_argument("--chrome", default=os.environ.get("CHROME", CHROME))
    p = sub.add_parser("pads", help="print the pad centres of footprints")
    src(p)
    p.add_argument("refs", nargs="+")
    n = sub.add_parser("near", help="list the pads within --radius of a point")
    src(n)
    n.add_argument("x", type=float)
    n.add_argument("y", type=float)
    n.add_argument("--radius", type=float, default=0.5)
    args = ap.parse_args(argv)
    if args.cmd == "render":
        cmd_render(args)
    elif args.cmd == "pads":
        cmd_pads(args)
    elif args.cmd == "near":
        cmd_near(args)
    else:
        ap.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
