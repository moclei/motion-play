"""Minimal s-expression reader for KiCad files, independent of any KiCad parser library.

Quoted strings come back as `Q` (a str subclass), so quoted and bare atoms stay distinct.
Read-only: nothing here writes a KiCad file.
"""
import re

_TOK = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


class Q(str):
    """A quoted string."""


def parse(text):
    stack = [[]]
    pos, n = 0, len(text)
    while pos < n:
        m = _TOK.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError("s-expression syntax error at offset {}".format(pos))
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            x = stack.pop()
            stack[-1].append(x)
        elif m.group(3) is not None:
            stack[-1].append(Q(m.group(3)))
        elif m.group(4) is not None:
            stack[-1].append(m.group(4))
    return stack[0][0]


def load(path):
    with open(str(path), encoding="utf-8") as f:
        return parse(f.read())


def child(node, head):
    """First child list whose head is `head`, or None."""
    for c in node:
        if isinstance(c, list) and c and c[0] == head:
            return c
    return None


def value(node, head):
    """Second element of the first `head` child, or ''."""
    c = child(node, head)
    return c[1] if c and len(c) > 1 else ""
