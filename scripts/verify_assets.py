#!/usr/bin/env python3
"""Verify selected official files without downloading or executing firmware."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat


def load_assets(path):
    data = json.loads(path.read_text())
    if data.get('schema_version') != 1 or data.get('board') != 'biscuit' or data.get('model') != 'RS03QR':
        raise ValueError('unsupported lock schema or target')
    assets = {}
    for item in data['assets']:
        name = item['name']
        if not name or Path(name).name != name or name in assets:
            raise ValueError('invalid or duplicate artifact name')
        if type(item['size']) is not int or item['size'] <= 0:
            raise ValueError('invalid artifact size')
        if not re.fullmatch('[0-9a-f]{64}', item['sha256']):
            raise ValueError('invalid artifact digest')
        assets[name] = item
    if not assets:
        raise ValueError('empty artifact lock')
    return assets


def verify(path, assets):
    if path.name not in assets:
        raise ValueError('artifact is not in the selected board/release lock')
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('artifact must be a regular file, not a symlink')
    expected = assets[path.name]
    if path.stat().st_size != expected['size']:
        raise ValueError('artifact size differs')
    digest = hashlib.sha256()
    total = 0
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if total > expected['size']:
                raise ValueError('artifact grew while reading')
            digest.update(chunk)
    if total != expected['size'] or digest.hexdigest() != expected['sha256']:
        raise ValueError('artifact digest or final size differs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', type=Path, nargs='+')
    parser.add_argument('--lock', type=Path, default=Path(__file__).resolve().parents[1] / 'upstream-lock.json')
    args = parser.parse_args()
    try:
        assets = load_assets(args.lock)
        for path in args.files:
            verify(path, assets)
            print(f'{path.name}: size and SHA-256 verified')
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'Verification failed: {error}\n')
    print('No installation performed; signature and device compatibility checks remain separate.')


if __name__ == '__main__':
    main()
