#!/usr/bin/env python3
"""Validate local Markdown links and publication/source hashes without networking."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

def main():
    failures = []
    links = 0
    for path in ROOT.rglob('*.md'):
        if '.git' in path.parts:
            continue
        text = re.sub(r'```.*?```', '', path.read_text(), flags=re.S)
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            if '://' in target or target.startswith('#'):
                continue
            target = unquote(target.split('#', 1)[0])
            links += 1
            if not (path.parent / target).exists():
                failures.append(f'{path.relative_to(ROOT)} -> {target}')
    manifest = json.loads((ROOT / 'reference/harness/source-manifest.json').read_text())
    for name, info in manifest.items():
        p = ROOT / 'reference/harness' / name
        if hashlib.sha256(p.read_bytes()).hexdigest() != info['public_sha256']:
            failures.append('Source hash mismatch: ' + name)
    public = json.loads((ROOT / 'PUBLICATION_SHA256.json').read_text())
    for name, expected in public.items():
        p = ROOT / name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            failures.append('Publication hash mismatch: ' + name)
    actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.name != 'PUBLICATION_SHA256.json'}
    if actual != set(public):
        failures.append('Publication file inventory differs from manifest')
    if failures:
        raise SystemExit('\n'.join(failures))
    print(f'PASS: {links} local links, {len(manifest)} source files, {len(public)} publication hashes')

if __name__ == '__main__':
    main()
