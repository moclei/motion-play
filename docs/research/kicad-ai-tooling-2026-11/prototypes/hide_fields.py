"""Prototype: hide every placed-symbol field except Reference and Value (and power-symbol Value)."""
import sys
from kiutils.schematic import Schematic
KEEP={'Reference','Value'}
for f in sys.argv[1:]:
    s=Schematic.from_file(f); n=0
    for sym in s.schematicSymbols:
        for p in sym.properties:
            if p.key not in KEEP and not p.effects.hide:
                p.effects.hide=True; n+=1
    s.to_file(f); print(f,'hidden',n)
