#!/usr/bin/env python3
"""
kiutils_k9.py - KiCad 8/9 compatibility shim for kiutils 1.4.8, plus a save guard.

kiutils 1.4.8 (last release, written for KiCad 7) only understands the bare
``hide`` atom. KiCad 8 and 9 write ``(hide yes)``, so a plain kiutils load and
save of a KiCad-saved sheet makes every hidden field visible and drops
``pin_numbers`` / ``pin_names`` / pin hiding
(docs/research/kicad-ai-tooling-2026-11/schematic-readability.md section 1).

Importing this module patches kiutils in place, once per process:

- ``Effects.from_sexpr``: ``(effects ... (hide yes))`` -> ``hide = True``
- ``Property.from_sexpr``: ``(property ... (hide yes))`` -> ``effects.hide = True``
- ``Symbol.from_sexpr``: ``(pin_numbers (hide yes))`` -> ``hidePinNumbers``,
  ``(pin_names ... (hide yes))`` -> ``pinNamesHide``
- ``SymbolPin.from_sexpr``: ``(pin ... (hide yes))`` -> ``hide = True``

kiutils then writes the older bare ``hide`` form, which KiCad 9 reads as hidden.
``(fields_autoplaced yes)`` already survives (kiutils writes the bare form);
``(exclude_from_sim ...)`` is dropped, which is harmless while every one is ``no``.

Rules (tools/schematic-modify/CONTEXT.md):
- Every kiutils load of a ``.kicad_sch`` / ``.kicad_sym`` goes through a module
  that has imported this one.
- Every schematic save goes through ``save_schematic`` (or calls
  ``assert_not_open``), which refuses while KiCad has the project open.

Usage from another tools/ folder::

    sys.path.insert(0, str(<repo>/"tools/schematic-modify"))
    import kiutils_k9  # noqa: F401  (patches kiutils on import)
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from kiutils.items import common
from kiutils.symbol import Symbol, SymbolPin

PATCHED_ATTR = "_motion_play_k9_shim"


def _is_hide_yes(item: object) -> bool:
    return isinstance(item, list) and len(item) >= 2 and item[0] == "hide" and item[1] == "yes"


def _patch() -> None:
    if getattr(common.Effects, PATCHED_ATTR, False):
        return

    orig_effects = common.Effects.from_sexpr.__func__

    def effects_from_sexpr(cls, exp):
        obj = orig_effects(cls, exp)
        if any(_is_hide_yes(item) for item in exp):
            obj.hide = True
        return obj

    common.Effects.from_sexpr = classmethod(effects_from_sexpr)

    orig_property = common.Property.from_sexpr.__func__

    def property_from_sexpr(cls, exp):
        obj = orig_property(cls, exp)
        if any(_is_hide_yes(item) for item in exp):
            if obj.effects is None:
                obj.effects = common.Effects()
            obj.effects.hide = True
        return obj

    common.Property.from_sexpr = classmethod(property_from_sexpr)

    orig_symbol = Symbol.from_sexpr.__func__

    def symbol_from_sexpr(cls, exp):
        obj = orig_symbol(cls, exp)
        for item in exp:
            if not (isinstance(item, list) and item and item[0] in ("pin_numbers", "pin_names")):
                continue
            if any(_is_hide_yes(x) for x in item):
                if item[0] == "pin_numbers":
                    obj.hidePinNumbers = True
                else:
                    obj.pinNames = True
                    obj.pinNamesHide = True
        return obj

    Symbol.from_sexpr = classmethod(symbol_from_sexpr)

    orig_pin = SymbolPin.from_sexpr.__func__

    def pin_from_sexpr(cls, exp):
        obj = orig_pin(cls, exp)
        if any(_is_hide_yes(item) for item in exp):
            obj.hide = True
        return obj

    SymbolPin.from_sexpr = classmethod(pin_from_sexpr)

    setattr(common.Effects, PATCHED_ATTR, True)


_patch()


def lock_files(path: Path) -> List[Path]:
    """KiCad schematic lock files (``~*.kicad_sch.lck``) in the folder of ``path``."""
    path = Path(path).resolve()
    folder = path if path.is_dir() else path.parent
    return sorted(folder.glob("~*.kicad_sch.lck"))


class KiCadOpenError(RuntimeError):
    pass


def assert_not_open(path: Path) -> None:
    """Raise KiCadOpenError if KiCad has the project holding ``path`` open."""
    locks = lock_files(path)
    if locks:
        raise KiCadOpenError(
            "KiCad has this project open ({}). Close KiCad and retry; "
            "a script save now would be overwritten by KiCad's next save.".format(
                ", ".join(p.name for p in locks)
            )
        )


def save_schematic(schematic: object, path: Path) -> None:
    """Save a kiutils Schematic, refusing while a KiCad lock file exists."""
    assert_not_open(Path(path))
    schematic.to_file(str(path))
