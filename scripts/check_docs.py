#!/usr/bin/env python3
"""Check local documentation links, SVG syntax and source pins."""
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


def main():
    root = Path(__file__).resolve().parents[1]
    names = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--cached', '--others', '--exclude-standard', '-z']).decode().split('\0')
    problems = []
    for name in sorted(set(filter(None, names))):
        path = root / name
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^\s)]+)', path.read_text()):
                if target.startswith(('http:', 'https:', 'mailto:', '#')):
                    continue
                dest = (path.parent / target.split('#')[0]).resolve()
                if not dest.is_relative_to(root) or not dest.exists():
                    problems.append(f'{name}: missing/outside local link {target}')
        elif path.suffix == '.svg':
            ET.parse(path)
    lock = json.loads((root / 'upstream-lock.json').read_text())
    for source in lock['upstreams'].values():
        if not re.fullmatch('[0-9a-f]{40}', source['commit']):
            problems.append('Source is not pinned to a commit')
    if lock['board'] != 'biscuit' or lock['model'] != 'RS03QR':
        problems.append('Target differs from documented pilot')
    if problems:
        raise SystemExit('\n'.join(problems))
    print('Documentation links, SVG and source pins verified.')


if __name__ == '__main__':
    main()
