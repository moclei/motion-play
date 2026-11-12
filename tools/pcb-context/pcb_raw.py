#!/usr/bin/env python3
"""
pcb_raw.py: read-only views over a board's raw s-expression tree.

The board readers (board_model.py, extract.py, routing_extract.py,
tools/verify-routing.py) load a .kicad_pcb through ``kicad_io.load_board``
(the only loader; tools/CONTEXT.md) and read it through these views. They
don't use kicad-tools' typed ``PCB``: it rebases coordinates onto the
Edge.Cuts corner and substitutes defaults for absent tokens (initiative
kicad10-tooling, PLAN "Raw-layer traps").

The readers were written against kiutils 1.4.8's ``Board``, so the views keep
its attribute names (``fp.position.X``, ``pad.pinFunction``,
``board.traceItems``, ``type(g).__name__ == "GrRect"``), and its class names
and attribute sets, because the readers test ``hasattr`` and the class name.
An absent token reads as kiutils read it (the default is noted per class),
and numbers come back as kiutils parsed them (``kicad_io.to_lists``: an
integral number is an int).

Two reads differ from kiutils on purpose, because kiutils misread v7's board
(PLAN "Accepted differences from preport", E1):
  - ``Zone.connectPads`` is the type atom of ``(connect_pads <type> ...)``
    (``yes``, ``no``, ``thru_hole_only``), or None when there is no type atom
    or no ``connect_pads``. kiutils kept the atom but board_model read a
    ``.type`` off it, so it was always None.
  - A graphic's ``width`` is ``(width w)``, else ``(stroke (width w))``, else
    kiutils' default 0.12. kiutils' ``Gr*`` classes ignored ``stroke``.

KiCad 10 boards write nets by name only (``(net "GND")``, no top-level net
table). Then a net's ``number`` is its name, and ``Board.nets`` lists each
name once, in file order, so ``{n.number: n.name}`` still resolves every
item's ``net``. A zone with a name-only net and no ``net_name`` takes that
name as ``netName``. A zone with no ``net`` token at all is a zone on no net
(KiCad 10 omits net 0; KiCad 9 wrote ``(net 0) (net_name "")``), so on a board
with no net table it reads ``netName`` ``""``, as KiCad 9's file does. On a
board with a net table, kiutils' absent default "unknown" stays.

Usage:
    import pcb_raw
    board = pcb_raw.load(path)          # Board view; board.doc is the kicad_io Doc
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "kicad-io"))
import kicad_io as kio  # noqa: E402


# ---------------------------------------------------------------------------
# Raw access in kiutils' terms
# ---------------------------------------------------------------------------

def _v(n):
    """A node as kiutils' parser gave it (atom → str/int/float; list → nested lists)."""
    return kio.to_lists(n)


def _item(n, k: int, default=None):
    """kiutils' ``item[k]``: the k-th element after the node's name (k ≥ 1)."""
    return _v(n.children[k - 1]) if 0 < k <= len(n.children) else default


def _bare(n) -> List[str]:
    """The node's bare string atoms (``locked``, ``board_only``, ``micro`` ...)."""
    return [c.value for c in n.children if c.is_atom and isinstance(c.value, str)]


def _lists(n):
    return [c for c in n.children if not c.is_atom]


def _last(n, name: str):
    """The last child list called ``name`` (kiutils' parse loops let the last one win)."""
    found = None
    for c in n.children:
        if not c.is_atom and c.name == name:
            found = c
    return found


def _val(n, name: str, default=None):
    """``item[1]`` of the last ``(name ...)`` child, or ``default``."""
    c = _last(n, name)
    return _item(c, 1, default) if c is not None else default


class Pos:
    """kiutils ``Position``: ``(at x y [angle])``, ``(start x y)``, ``(xy x y)``, ``(size w h)``."""
    __slots__ = ("X", "Y", "angle")

    def __init__(self, X=0.0, Y=0.0, angle=None):
        self.X, self.Y, self.angle = X, Y, angle

    @classmethod
    def of(cls, n) -> "Pos":
        p = cls(_item(n, 1), _item(n, 2))
        a = _item(n, 3)
        if a is not None and a != "unlocked":
            p.angle = a
        return p

    def __repr__(self):
        return "Pos(%r, %r, %r)" % (self.X, self.Y, self.angle)


def _pos(n, name: str, default=None):
    c = _last(n, name)
    return Pos.of(c) if c is not None else default


def _pts(n) -> List[Pos]:
    c = _last(n, "pts")
    return [Pos.of(p) for p in _lists(c) if p.name == "xy"] if c is not None else []


class Net:
    """``(net N "name")``; on KiCad 10 ``(net "name")``, where ``number`` is the name."""
    __slots__ = ("number", "name")

    def __init__(self, number, name):
        self.number, self.name = number, name

    @classmethod
    def of(cls, n) -> "Net":
        a, b = _item(n, 1), _item(n, 2)
        if b is None and isinstance(a, str):
            return cls(a, a)
        return cls(a, b)


def _net_number(n, default=0):
    """An item's ``net`` as kiutils held it: the number (KiCad 9), or the name (KiCad 10)."""
    c = _last(n, "net")
    return Net.of(c).number if c is not None else default


# ---------------------------------------------------------------------------
# Graphics (board, footprint, custom-pad primitives)
# ---------------------------------------------------------------------------

def _width(n):
    """``(width w)``, else ``(stroke (width w))``, else kiutils' 0.12 (E1: kiutils ignored stroke)."""
    w = _val(n, "width")
    if w is None:
        s = _last(n, "stroke")
        w = _val(s, "width") if s is not None else None
    return 0.12 if w is None else w


class _Graphic:
    """Base for the graphic views. Each subclass sets only the attributes its kiutils class has."""
    LAYER_DEFAULT: Optional[str] = None

    def __init__(self, n):
        self.node = n
        self.layer = _val(n, "layer", self.LAYER_DEFAULT)
        self.locked = "locked" in _bare(n)


class _Line(_Graphic):
    def __init__(self, n):
        super().__init__(n)
        self.start, self.end = _pos(n, "start", Pos()), _pos(n, "end", Pos())
        self.width = _width(n)


class _Rect(_Line):
    def __init__(self, n):
        super().__init__(n)
        self.fill = _val(n, "fill")


class _Circle(_Graphic):
    def __init__(self, n):
        super().__init__(n)
        self.center, self.end = _pos(n, "center", Pos()), _pos(n, "end", Pos())
        self.width = _width(n)
        self.fill = _val(n, "fill")


class _Arc(_Line):
    def __init__(self, n):
        super().__init__(n)
        self.mid = _pos(n, "mid", Pos())


class _Poly(_Graphic):
    def __init__(self, n):
        super().__init__(n)
        self.coordinates = _pts(n)
        self.width = _width(n)
        self.fill = _val(n, "fill")


class _Curve(_Graphic):
    def __init__(self, n):
        super().__init__(n)
        self.coordinates = _pts(n)
        self.width = _width(n)


class _Text(_Graphic):
    def __init__(self, n):
        super().__init__(n)
        self.text = _item(n, 1) if n.name == "gr_text" else _item(n, 2)
        self.position = _pos(n, "at", Pos())


class _TextBox(_Graphic):
    def __init__(self, n):
        super().__init__(n)
        self.start, self.end = _pos(n, "start"), _pos(n, "end")
        self.pts = _pts(n)


class _Image(_Graphic):
    def __init__(self, n):
        super().__init__(n)
        self.position = _pos(n, "at", Pos())


def _kinds(prefix: str, layer_default: Optional[str]) -> Dict[str, type]:
    out = {}
    for tok, base, cls in (("line", _Line, "Line"), ("rect", _Rect, "Rect"), ("circle", _Circle, "Circle"),
                           ("arc", _Arc, "Arc"), ("poly", _Poly, "Poly"), ("curve", _Curve, "Curve"),
                           ("text", _Text, "Text"), ("text_box", _TextBox, "TextBox")):
        name = ("Gr" if prefix == "gr_" else "Fp") + cls
        out[prefix + tok] = type(name, (base,), {"LAYER_DEFAULT": layer_default})
    out["image"] = type("Image", (_Image,), {"LAYER_DEFAULT": None})
    return out


# kiutils: Gr* layers default to None, Fp* layers to "F.Cu" (GrTextBox also "F.Cu").
GR_KINDS = _kinds("gr_", None)
GR_KINDS["gr_text_box"].LAYER_DEFAULT = "F.Cu"
FP_KINDS = _kinds("fp_", "F.Cu")


def _graphics(n, kinds: Dict[str, type]) -> List[_Graphic]:
    return [kinds[c.name](c) for c in _lists(n) if c.name in kinds]


# ---------------------------------------------------------------------------
# Footprints and pads
# ---------------------------------------------------------------------------

class Drill:
    """``(drill d)``, ``(drill d w)``, ``(drill oval d w)``; kiutils ``DrillDefinition``."""

    def __init__(self, n):
        a = _item(n, 1)
        self.oval = a == "oval"
        self.diameter = _item(n, 2) if self.oval else a
        self.width = _item(n, 3) if self.oval else _item(n, 2)
        if isinstance(self.width, list):
            self.width = None
        self.offset = _pos(n, "offset")


class PadOptions:
    """``(options (clearance outline) (anchor rect))``; kiutils defaults ``outline`` / ``rect``."""

    def __init__(self, n):
        self.clearance = _val(n, "clearance", "outline")
        self.anchor = _val(n, "anchor", "rect")


class Pad:
    """kiutils ``Pad``. Absent: drill/net/pinFunction/pinType/roundrectRatio/customPadOptions None,
    position and size (0, 0)."""

    def __init__(self, n):
        self.node = n
        self.number = _item(n, 1, "x")
        self.type = _item(n, 2, "smd")
        self.shape = _item(n, 3, "rect")
        self.position = _pos(n, "at", Pos())
        self.size = _pos(n, "size", Pos())
        d = _last(n, "drill")
        self.drill = Drill(d) if d is not None else None
        ls = _last(n, "layers")
        self.layers = [_v(c) for c in ls.children] if ls is not None else []
        c = _last(n, "net")
        self.net = Net.of(c) if c is not None else None
        self.pinFunction = _val(n, "pinfunction")
        self.pinType = _val(n, "pintype")
        self.roundrectRatio = _val(n, "roundrect_rratio")
        o = _last(n, "options")
        self.customPadOptions = PadOptions(o) if o is not None else None
        p = _last(n, "primitives")
        self.customPadPrimitives = _graphics(p, GR_KINDS) if p is not None else []


class Attributes:
    """``(attr [smd|through_hole] [board_only] [exclude_from_pos_files] [exclude_from_bom] ...)``."""

    def __init__(self, n=None):
        bare = _bare(n) if n is not None else []
        first = bare[0] if bare and n.children and n.children[0].is_atom else None
        self.type = first if first in ("through_hole", "smd") else None
        self.boardOnly = "board_only" in bare
        self.excludeFromPosFiles = "exclude_from_pos_files" in bare
        self.excludeFromBom = "exclude_from_bom" in bare
        self.allowMissingCourtyard = "allow_missing_courtyard" in bare


class Footprint:
    """kiutils ``Footprint``. Absent: layer "F.Cu", position None, attributes all unset."""

    def __init__(self, n):
        self.node = n
        self.libId = str(_item(n, 1, ""))
        self.entryName = self.libId.split(":", 1)[1] if ":" in self.libId[1:-1] else self.libId
        self.layer = _val(n, "layer", "F.Cu")
        self.position = _pos(n, "at")
        self.properties: Dict[str, Any] = {}
        for p in _lists(n):
            if p.name == "property":
                self.properties[_item(p, 1)] = _item(p, 2)
        a = _last(n, "attr")
        self.attributes = Attributes(a)
        self.pads = [Pad(c) for c in _lists(n) if c.name == "pad"]
        self.graphicItems = _graphics(n, FP_KINDS)


# ---------------------------------------------------------------------------
# Tracks
# ---------------------------------------------------------------------------

class Segment:
    """kiutils ``Segment``. Absent: width 0.1, layer "F.Cu", net 0."""

    def __init__(self, n):
        self.node = n
        self.start, self.end = _pos(n, "start", Pos()), _pos(n, "end", Pos())
        self.width = _val(n, "width", 0.1)
        self.layer = _val(n, "layer", "F.Cu")
        self.net = _net_number(n)


class Arc:
    """kiutils ``Arc``. Absent: width 0.2, layer "F.Cu", net 0. Not a Segment subclass: the readers
    tell them apart with isinstance."""

    def __init__(self, n):
        self.node = n
        self.start, self.mid, self.end = _pos(n, "start", Pos()), _pos(n, "mid", Pos()), _pos(n, "end", Pos())
        self.width = _val(n, "width", 0.2)
        self.layer = _val(n, "layer", "F.Cu")
        self.net = _net_number(n)


class Via:
    """kiutils ``Via``. Absent: type None (``micro``/``blind`` atoms), size and drill 0.0, net 0."""

    def __init__(self, n):
        self.node = n
        bare = _bare(n)
        self.type = next((b for b in bare if b in ("micro", "blind")), None)
        self.position = _pos(n, "at", Pos())
        self.size = _val(n, "size", 0.0)
        self.drill = _val(n, "drill", 0.0)
        ls = _last(n, "layers")
        self.layers = [_v(c) for c in ls.children] if ls is not None else []
        self.net = _net_number(n)


TRACK_KINDS = {"segment": Segment, "arc": Arc, "via": Via}


# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------

class KeepoutSettings:
    """kiutils defaults: tracks/vias/pads "allowed", copperpour/footprints "not-allowed"."""

    def __init__(self, n):
        self.tracks = _val(n, "tracks", "allowed")
        self.vias = _val(n, "vias", "allowed")
        self.pads = _val(n, "pads", "allowed")
        self.copperpour = _val(n, "copperpour", "not-allowed")
        self.footprints = _val(n, "footprints", "not-allowed")


class ZonePolygon:
    def __init__(self, n):
        self.coordinates = _pts(n)


class FilledPolygon:
    def __init__(self, n):
        self.layer = _val(n, "layer", "F.Cu")
        self.island = _last(n, "island") is not None
        self.coordinates = _pts(n)


class Zone:
    """kiutils ``Zone``. Absent: net 0, netName "unknown" ("" on a board with no net table, KiCad 10),
    name/priority None, clearance and minThickness 0.254. ``connectPads`` is the type atom or None (E1)."""

    def __init__(self, n, name_only=False):
        self.node = n
        c = _last(n, "net")
        net = Net.of(c) if c is not None else None
        self.net = net.number if net is not None else 0
        self.netName = _val(n, "net_name", None)
        if self.netName is None:
            if net is not None and net.number == net.name:
                self.netName = net.name
            else:
                # KiCad 10 (no net table) writes a no-net zone with no net token: net 0, name "".
                self.netName = "" if net is None and name_only else "unknown"
        self.layers: List[str] = []
        for c in _lists(n):
            if c.name in ("layers", "layer"):
                self.layers.extend(_v(x) for x in c.children)
        self.name = _val(n, "name")
        self.priority = _val(n, "priority")
        self.connectPads = None
        self.clearance = 0.254
        cp = _last(n, "connect_pads")
        if cp is not None:
            first = cp.children[0] if cp.children else None
            if first is not None and first.is_atom:
                self.connectPads = _v(first)
            self.clearance = _val(cp, "clearance", self.clearance)
        self.minThickness = _val(n, "min_thickness", 0.254)
        k = _last(n, "keepout")
        self.keepoutSettings = KeepoutSettings(k) if k is not None else None
        self.polygons = [ZonePolygon(c) for c in _lists(n) if c.name == "polygon"]
        self.filledPolygons = [FilledPolygon(c) for c in _lists(n) if c.name == "filled_polygon"]


# ---------------------------------------------------------------------------
# Layers, stackup
# ---------------------------------------------------------------------------

class LayerToken:
    """One entry of the top-level ``(layers (0 "F.Cu" signal) ...)``."""

    def __init__(self, n):
        self.ordinal = _v(n)[0]          # the list's head, e.g. 0 in (0 "F.Cu" signal)
        self.name = _item(n, 1)
        self.type = _item(n, 2)
        self.userName = _item(n, 3)


class StackupLayer:
    """kiutils ``StackupLayer``: tokens after ``addsublayer`` belong to sub-layers, not the layer."""

    def __init__(self, n):
        self.name = _item(n, 1, "")
        self.type, self.color = "", None
        self.thickness = self.material = self.epsilonR = self.lossTangent = None
        self.subLayers: List[Dict[str, Any]] = []
        sub = None
        keys = {"type": "type", "thickness": "thickness", "material": "material",
                "epsilon_r": "epsilonR", "loss_tangent": "lossTangent", "color": "color"}
        for c in n.children[1:]:
            if c.is_atom:
                if c.value == "addsublayer":
                    sub = {"thickness": 0.1, "material": None, "epsilonR": None, "lossTangent": None}
                    self.subLayers.append(sub)
                continue
            if sub is not None:
                if c.name in keys and keys[c.name] in sub:
                    sub[keys[c.name]] = _item(c, 1)
                continue
            if c.name in keys:
                setattr(self, keys[c.name], _item(c, 1))


class Stackup:
    def __init__(self, n):
        self.layers = [StackupLayer(c) for c in _lists(n) if c.name == "layer"]


class Setup:
    """kiutils ``SetupData``: only ``stackup`` is read (None when absent)."""

    def __init__(self, n=None):
        s = _last(n, "stackup") if n is not None else None
        self.stackup = Stackup(s) if s is not None else None


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------

class Board:
    """kiutils ``Board`` over ``kicad_io.load_board``'s tree. Lists keep file order."""

    def __init__(self, doc: "kio.Doc"):
        self.doc = doc
        self.filePath = str(doc.path)
        t = doc.tree
        self.version = _val(t, "version", "")
        self.generator = _val(t, "generator", "")
        ls = _last(t, "layers")
        self.layers = [LayerToken(c) for c in _lists(ls)] if ls is not None else []
        self.setup = Setup(_last(t, "setup"))
        self.nets = [Net.of(c) for c in _lists(t) if c.name == "net"]
        name_only = not self.nets
        self.footprints: List[Footprint] = []
        self.graphicItems: List[_Graphic] = []
        self.traceItems: List[Any] = []
        self.zones: List[Zone] = []
        for c in _lists(t):
            if c.name == "footprint":
                self.footprints.append(Footprint(c))
            elif c.name in GR_KINDS:
                self.graphicItems.append(GR_KINDS[c.name](c))
            elif c.name in TRACK_KINDS:
                self.traceItems.append(TRACK_KINDS[c.name](c))
            elif c.name == "zone":
                self.zones.append(Zone(c, name_only))
        if not self.nets:
            self.nets = self._name_only_nets()

    def _name_only_nets(self) -> List[Net]:
        """KiCad 10: no net table; every net name the board uses, once, in file order."""
        seen: Dict[str, None] = {}
        for fp in self.footprints:
            for p in fp.pads:
                if p.net is not None and isinstance(p.net.number, str):
                    seen.setdefault(p.net.name, None)
        for it in self.traceItems + self.zones:
            if isinstance(it.net, str):
                seen.setdefault(it.net, None)
        return [Net(name, name) for name in seen]


def load(path) -> Board:
    """Load a .kicad_pcb through kicad_io and wrap it."""
    return Board(kio.load_board(path))
