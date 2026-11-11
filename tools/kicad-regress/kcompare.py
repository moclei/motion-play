"""Comparison methods of the KiCad regression harness (regress.py). Read-only, stdlib only.

Each method was first used in kicad10-tooling Phases 1-3 (SESSION.md, Worker #1-#3 Notes):
  erc_counts      ERC violations per (severity, type), as v8_debug_sheet.erc_summary counts them
  erc_split       ERC/DRC counts with library items split into 'setup' (in KiCad 9's global lib
                  table but not the project's: resolves on 9 only) and 'real'
  netlist_diff    structural compare of two s-expression netlists (components and net membership)
  svg_strings     plotted strings per sheet (<desc> texts of kicad-cli SVG plots)
  census          token-kind census of a KiCad file; census_diff lists the kinds whose count differs
  tree_equal      exact tree equality of two KiCad files (whitespace ignored, quoted vs bare kept)
  json_diff       leaf-by-leaf JSON compare, numbers within a tolerance
"""
import collections
import html
import json
import os
import re

from sexp import Q, child, load, value

# ---------------------------------------------------------------------------
# ERC / DRC
# ---------------------------------------------------------------------------


def _violations(report):
    out = []
    for sh in report.get("sheets", []):
        for v in sh.get("violations", []):
            out.append((sh.get("path"), v))
    for v in report.get("violations", []):
        out.append((None, v))
    return out


def erc_counts(report):
    """Lines: '<severity> <type> <n>' sorted, then each non-pin_to_pin violation with its sheet."""
    counts, items = {}, []
    for sh in report.get("sheets", []):
        for v in sh.get("violations", []):
            k = (v.get("severity"), v.get("type"))
            counts[k] = counts.get(k, 0) + 1
            items.append((sh.get("path"), v))
    lines = ["{} {} {}".format(s, t, n) for (s, t), n in sorted(counts.items())]
    for p, v in items:
        if v.get("type") != "pin_to_pin":
            lines.append("   {} {} {}".format(p, v.get("type"), v.get("description")))
    return lines


def _lib_names(path):
    try:
        with open(path) as f:
            return set(re.findall(r'\(name "([^"]+)"\)', f.read()))
    except (IOError, OSError):
        return set()


def erc_split(report, project_dir, global_dir=None):
    """Counts per (severity, type, 'setup'|'real'|'') for an ERC or DRC JSON report."""
    gdir = global_dir or os.path.expanduser("~/Library/Preferences/kicad/9.0")
    g_sym, g_fp = _lib_names(os.path.join(gdir, "sym-lib-table")), _lib_names(os.path.join(gdir, "fp-lib-table"))
    p_sym = _lib_names(os.path.join(project_dir, "sym-lib-table"))
    p_fp = _lib_names(os.path.join(project_dir, "fp-lib-table"))
    lib_types = ("lib_symbol_issues", "footprint_link_issues", "lib_footprint_issues", "lib_footprint_mismatch")
    c = collections.Counter()
    libs = collections.defaultdict(collections.Counter)
    for _, v in _violations(report):
        t, s = v.get("type"), v.get("severity")
        m = re.search(r"(symbol|footprint) library '([^']+)'", v.get("description", ""))
        if m and t in lib_types:
            kind, lib = m.groups()
            glob, proj = (g_sym, p_sym) if kind == "symbol" else (g_fp, p_fp)
            cat = "setup" if (lib in glob and lib not in proj) else "real"
            c[(s, t, cat)] += 1
            libs[(t, cat)][lib] += 1
        else:
            c[(s, t, "")] += 1
    lines = ["{} {} {} {}".format(s, t, cat, c[(s, t, cat)]) for (s, t, cat) in sorted(c)]
    if "unconnected_items" in report:
        lines.append("unconnected_items {}".format(len(report["unconnected_items"])))
    if "schematic_parity" in report:
        lines.append("schematic_parity {}".format(len(report["schematic_parity"])))
    for k, v in sorted(libs.items()):
        lines.append("  libs {} {}".format(k, dict(v)))
    return lines


# ---------------------------------------------------------------------------
# Netlists
# ---------------------------------------------------------------------------


def read_netlist(path, strip_pin_suffix=False):
    """(components, nets, classes, suffixes stripped) from an s-expression netlist (.net).

    components: ref -> value, footprint, fields, non-Sheetname properties, libsource, sheetpath, tstamps
    nets: name -> frozenset of (ref, pin, pintype, pinfunction)
    strip_pin_suffix: drop the '_<pin>' that kicad-cli 10 appends to every pinfunction.
    """
    t = load(path)
    comps, nets, classes, sfx = {}, {}, {}, 0
    for c in child(t, "components")[1:]:
        f = child(c, "fields")
        fields = {}
        for fl in (f[1:] if f else []):
            v = fl[2] if len(fl) > 2 else ""
            fields[value(fl, "name")] = "" if v == "~" else v
        props = {value(p, "name"): value(p, "value") for p in c if isinstance(p, list) and p and p[0] == "property"}
        props.pop("Sheetname", None)
        ls, sp = child(c, "libsource"), child(c, "sheetpath")
        comps[value(c, "ref")] = dict(
            value=value(c, "value"), footprint=value(c, "footprint"), fields=fields, props=props,
            lib=(value(ls, "lib"), value(ls, "part")) if ls else ("", ""),
            sheet=(value(sp, "names"), value(sp, "tstamps")) if sp else ("", ""), ts=value(c, "tstamps"))
    for n in child(t, "nets")[1:]:
        nodes = set()
        for nd in n:
            if isinstance(nd, list) and nd and nd[0] == "node":
                pin, pf = value(nd, "pin"), value(nd, "pinfunction")
                if strip_pin_suffix and pf.endswith("_" + pin):
                    pf = pf[:-len(pin) - 1]
                    sfx += 1
                nodes.add((value(nd, "ref"), pin, value(nd, "pintype"), pf))
        nets[value(n, "name")] = frozenset(nodes)
        classes[value(n, "name")] = value(n, "class")
    return comps, nets, classes, sfx


def netlist_diff(path_a, path_b, strip_a=False, strip_b=False, show=10):
    """(lines, equal). Equal means same components (every compared field) and same nets."""
    A, B = read_netlist(path_a, strip_a), read_netlist(path_b, strip_b)
    lines = ["components A {} B {}; nets A {} B {}; pinfunction suffixes stripped A {} B {}".format(
        len(A[0]), len(B[0]), len(A[1]), len(B[1]), A[3], B[3])]
    cd = sorted(r for r in set(A[0]) | set(B[0]) if A[0].get(r) != B[0].get(r))
    lines.append("components differing: {}".format(len(cd)))
    for r in cd[:show]:
        a, b = A[0].get(r) or {}, B[0].get(r) or {}
        lines.append("   {} {}".format(r, {k: (a.get(k), b.get(k)) for k in sorted(set(a) | set(b))
                                          if a.get(k) != b.get(k)}))
    nd = sorted(n for n in set(A[1]) | set(B[1]) if A[1].get(n) != B[1].get(n))
    lines.append("nets differing (name or node set): {}".format(len(nd)))
    for n in nd[:show]:
        lines.append("   {} {}".format(n, sorted((A[1].get(n) or set()) ^ (B[1].get(n) or set()))))
    cl = [(n, A[2][n], B[2][n]) for n in sorted(set(A[2]) & set(B[2])) if A[2][n] != B[2][n]]
    lines.append("net class strings differing: {} {}".format(
        len(cl), dict(collections.Counter((x[1], x[2]) for x in cl)) if cl else ""))
    return lines, not cd and not nd


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def _svg_strings(path):
    with open(path, encoding="utf-8") as f:
        s = re.findall(r"<desc>([^<]*)</desc>", f.read())
    return collections.Counter(html.unescape(x) for x in s if not x.startswith("Image generated by"))


def svg_strings(dir_a, dir_b):
    """(lines, equal): the multiset of plotted strings in each same-named SVG of two folders."""
    lines, equal = [], True
    names = sorted(n for n in set(os.listdir(dir_a)) | set(os.listdir(dir_b)) if n.endswith(".svg"))
    for n in names:
        pa, pb = os.path.join(dir_a, n), os.path.join(dir_b, n)
        A = _svg_strings(pa) if os.path.exists(pa) else collections.Counter()
        B = _svg_strings(pb) if os.path.exists(pb) else collections.Counter()
        same = A == B
        equal &= same
        lines.append("{} {}: {} -> {}{}".format("same" if same else "DIFF", n, sum(A.values()), sum(B.values()),
                                                "" if same else "; lost {} gained {}".format(dict(A - B), dict(B - A))))
    return lines, equal


# ---------------------------------------------------------------------------
# Token census and tree equality
# ---------------------------------------------------------------------------

_NUM = re.compile(r"^-?[0-9.]+(e-?[0-9]+)?$")
# Bare atoms that are flags (true when present) in KiCad's grammar.
_FLAGS = {
    "hide", "locked", "bold", "italic", "mirror", "fields_autoplaced", "dnp", "in_bom", "on_board",
    "exclude_from_sim", "free", "embedded_fonts", "embedded_files", "allow_missing_courtyard",
    "exclude_from_pos_files", "exclude_from_bom", "board_only", "allow_soldermask_bridges", "keep_end_layers",
    "remove_unused_layers", "do_not_autoplace", "power", "knockout", "private", "duplicate_pin_numbers_are_jumpers",
    "in_pos_files", "unlocked", "show_name", "hide_name", "filled_areas_thickness", "island", "circular", "gap",
    "legacy_teardrops", "dimension", "zone_connect", "placed", "fixed"}


def census(path):
    """Counter of token kinds:
    L:<head>        every list, by its head
    F:<flag>        a flag set true, written (<flag> yes) or as a bare atom
    N:<flag>        (<flag> no)
    A:<parent>/<x>  any other bare, non-numeric atom, by its parent's head
    """
    c = collections.Counter()

    def rec(n):
        h = n[0] if n and isinstance(n[0], str) and not isinstance(n[0], Q) else None
        c["L:" + str(h)] += 1
        if len(n) == 2 and n[1] in ("yes", "no") and not isinstance(n[1], Q):
            c[("F:" if n[1] == "yes" else "N:") + str(h)] += 1
        for x in n[1:]:
            if isinstance(x, list):
                rec(x)
            elif not isinstance(x, Q) and not _NUM.match(x) and x not in ("yes", "no"):
                c[("F:" + x) if x in _FLAGS else "A:{}/{}".format(h, x)] += 1
    rec(load(path))
    return c


def census_diff(path_a, path_b):
    """Lines 'kind<TAB>a<TAB>b<TAB>delta' for every kind whose count differs."""
    a, b = census(path_a), census(path_b)
    return ["{}\t{}\t{}\t{:+d}".format(k, a[k], b[k], b[k] - a[k]) for k in sorted(set(a) | set(b)) if a[k] != b[k]]


def _tree(n):
    if isinstance(n, list):
        return tuple(_tree(c) for c in n)
    return ("Q", str(n)) if isinstance(n, Q) else str(n)


def tree_equal(path_a, path_b, show=5):
    """(equal, first differences)."""
    a, b = _tree(load(path_a)), _tree(load(path_b))
    if a == b:
        return True, []
    d = []

    def cmp(x, y, p):
        if len(d) >= show:
            return
        if isinstance(x, tuple) and isinstance(y, tuple) and len(x) == len(y):
            for i, (u, v) in enumerate(zip(x, y)):
                cmp(u, v, "{}/{}[{}]".format(p, x[0] if x and isinstance(x[0], str) else "?", i))
        elif x != y:
            d.append((p, str(x)[:120], str(y)[:120]))
    cmp(a, b, "")
    return False, d


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def json_diff(a, b, tol=1e-9, skip=("_provenance",)):
    """List of (path, detail) for every leaf that differs. Numbers equal within `tol`
    (bool and int vs float type changes count as differences). Top-level keys in `skip` are ignored."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        a = {k: v for k, v in a.items() if k not in skip}
        b = {k: v for k, v in b.items() if k not in skip}

    def num(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y)):
                if k not in x or k not in y:
                    out.append((path + "/" + k, "key missing in " + ("A" if k not in x else "B")))
                else:
                    walk(x[k], y[k], path + "/" + k)
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                out.append((path, "length {} vs {}".format(len(x), len(y))))
                return
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, "{}[{}]".format(path, i))
        elif num(x) and num(y) and type(x) is type(y):
            if abs(x - y) > tol:
                out.append((path, (x, y)))
        elif type(x) is not type(y) or x != y:
            out.append((path, (x, y)))
    walk(a, b, "")
    return out
