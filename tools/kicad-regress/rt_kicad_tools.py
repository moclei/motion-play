"""kicad-tools load + save of KiCad files, for regress.py roundtrip (runs in tools/.venv).

usage: rt_kicad_tools.py OUTDIR SRC_ROOT FILE...
Each FILE (a path under SRC_ROOT) is loaded and saved twice: through kicad-tools' raw s-expression
layer (OUTDIR/raw/<path>) and its typed layer (OUTDIR/typed/<path>). Prints one line per save:
'OK <layer> <path>' or 'FAIL <layer> <path>: <error>'. Never writes under SRC_ROOT.
"""
import sys
from pathlib import Path

from kicad_tools.core import sexp_file as kt
from kicad_tools.schema.pcb import PCB
from kicad_tools.schema.schematic import Schematic


def raw(src, dst):
    if src.suffix == ".kicad_sch":
        kt.save_schematic(kt.load_schematic(str(src)), str(dst))
    else:
        kt.save_pcb(kt.load_pcb(str(src)), str(dst))


def typed(src, dst):
    cls = Schematic if src.suffix == ".kicad_sch" else PCB
    cls.load(str(src)).save(str(dst))


def main():
    out, src_root = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    bad = 0
    for f in sys.argv[3:]:
        src = Path(f).resolve()
        rel = src.relative_to(src_root)
        for layer, fn in (("raw", raw), ("typed", typed)):
            dst = out / layer / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                fn(src, dst)
                print("OK {} {}".format(layer, rel))
            except Exception as e:  # report and go on: the caller counts failures
                bad += 1
                print("FAIL {} {}: {}: {}".format(layer, rel, type(e).__name__, str(e)[:300]))
            sys.stdout.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
