#!/usr/bin/env python3
"""Strip non-semantic cruft from a TI document-viewer HTML capture."""

import hashlib
import re
import sys


def remove_ti_raw_content_attribute(content):
    return re.sub(r'\s+content="[^"]*"', '', content, flags=re.DOTALL)


def strip_attributes_and_decorations(content):
    content = re.sub(r'<script\b[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<style\b[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)

    content = re.sub(r'<meta\b[^>]*/?>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<link\b[^>]*/?>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<img\b[^>]*/?>', '[image]', content, flags=re.IGNORECASE)
    content = re.sub(r'<col\b[^>]*/?>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</?colgroup\b[^>]*>', '', content, flags=re.IGNORECASE)

    content = re.sub(r'<a\s+id="[^"]*"\s*></a>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<a\s+name="[^"]*"\s*></a>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<a\s+[^>]*>(.*?)</a>', r'\1', content, flags=re.DOTALL | re.IGNORECASE)

    for attr in ['class', 'style', 'align', 'valign', 'data-url', 'data-handleshtml',
                 'data-tooltip', 'src', 'href', 'alt', 'width', 'height', 'role',
                 'aria-label', 'aria-hidden', 'tabindex']:
        content = re.sub(rf'\s+{attr}="[^"]*"', '', content, flags=re.IGNORECASE)

    for _ in range(5):
        content = re.sub(r'<span\s*>(\s*)</span>', r'\1', content)
    for _ in range(3):
        content = re.sub(r'<div\s*>(\s*)</div>', r'\1', content)

    return content


def deduplicate_sections(content):
    parts = re.split(r'(<ti-raw\b[^>]*>|</ti-raw>)', content)
    output = []
    inside = False
    buf = []
    seen = set()

    for part in parts:
        if part.startswith('<ti-raw'):
            inside = True
            buf = [part]
        elif part == '</ti-raw>':
            inside = False
            buf.append(part)
            block = ''.join(buf)
            m = re.search(r'<h([1-6])\s+id="([^"]+)"', block)
            key = m.group(2) if m else hashlib.md5(block.encode()).hexdigest()[:8]
            if key not in seen:
                seen.add(key)
                output.append(block)
            buf = []
        else:
            if inside:
                buf.append(part)
            else:
                output.append(part)

    return ''.join(output)


def normalize_whitespace(content):
    content = re.sub(r'^[ \t]+', '', content, flags=re.MULTILINE)
    content = re.sub(r'\n[ \t]*\n[ \t]*\n+', '\n\n', content)
    return content.strip() + '\n'


def main():
    if len(sys.argv) != 3:
        print('Usage: strip_datasheet.py <input.html> <output.html>', file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        content = f.read()

    sizes = [('Original', len(content))]

    content = remove_ti_raw_content_attribute(content)
    sizes.append(('After removing content attrs', len(content)))

    content = strip_attributes_and_decorations(content)
    sizes.append(('After stripping attrs/tags', len(content)))

    content = deduplicate_sections(content)
    sizes.append(('After dedup', len(content)))

    content = normalize_whitespace(content)
    sizes.append(('After whitespace normalize', len(content)))

    with open(sys.argv[2], 'w') as f:
        f.write(content)

    base = sizes[0][1]
    for label, size in sizes:
        pct = 100 * size / base
        print(f'{label:<32} {size:>10,} bytes  ({pct:5.1f}%)')


if __name__ == '__main__':
    main()
