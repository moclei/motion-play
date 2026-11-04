"""Prototype shim: teach kiutils 1.4.8 to read KiCad 8/9 '(hide yes)' so a round-trip keeps hidden flags."""
from kiutils.items import common
from kiutils.symbol import Symbol
_orig_eff = common.Effects.from_sexpr.__func__
def _eff(cls, exp):
    obj = _orig_eff(cls, exp)
    for item in exp:
        if isinstance(item, list) and item and item[0] == 'hide' and item[1:2] == ['yes']:
            obj.hide = True
    return obj
common.Effects.from_sexpr = classmethod(_eff)
_orig_prop = common.Property.from_sexpr.__func__
def _prop(cls, exp):
    obj = _orig_prop(cls, exp)
    for item in exp:
        if isinstance(item, list) and item[:2] == ['hide', 'yes'] and obj.effects is not None:
            obj.effects.hide = True
    return obj
common.Property.from_sexpr = classmethod(_prop)
_orig_sym = Symbol.from_sexpr.__func__
def _sym(cls, exp):
    obj = _orig_sym(cls, exp)
    for item in exp:
        if isinstance(item, list) and item and item[0] in ('pin_numbers', 'pin_names'):
            if any(isinstance(x, list) and x[:2] == ['hide', 'yes'] for x in item):
                if item[0] == 'pin_numbers': obj.hidePinNumbers = True
                else: obj.pinNamesHide = True
    return obj
Symbol.from_sexpr = classmethod(_sym)
