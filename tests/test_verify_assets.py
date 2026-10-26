import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.verify_assets import load_assets, verify


class AssetVerification(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.file = self.root / 'artifact'
        self.file.write_bytes(b'fixture')
        self.item = {'name': 'artifact', 'size': 7, 'sha256': hashlib.sha256(b'fixture').hexdigest()}
        self.data = {'schema_version': 1, 'board': 'biscuit', 'model': 'RS03QR', 'assets': [self.item]}
        self.lock = self.root / 'lock.json'

    def assets(self):
        self.lock.write_text(json.dumps(self.data))
        return load_assets(self.lock)

    def test_valid_file(self):
        verify(self.file, self.assets())

    def test_same_size_corruption(self):
        self.file.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'digest'):
            verify(self.file, self.assets())

    def test_truncated_download(self):
        self.file.write_bytes(b'fix')
        with self.assertRaisesRegex(ValueError, 'size'):
            verify(self.file, self.assets())

    def test_wrong_board_lock(self):
        self.data['board'] = 'donut'
        with self.assertRaisesRegex(ValueError, 'target'):
            self.assets()

    def test_unselected_file(self):
        other = self.root / 'other-board'
        other.write_bytes(b'fixture')
        with self.assertRaisesRegex(ValueError, 'not in'):
            verify(other, self.assets())

    def test_symlink_rejected(self):
        source = self.root / 'source'
        self.file.rename(source)
        self.file.symlink_to(source)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            verify(self.file, self.assets())

    def test_duplicate_name_rejected(self):
        self.data['assets'].append(dict(self.item))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.assets()

    def test_empty_lock_rejected(self):
        self.data['assets'] = []
        with self.assertRaisesRegex(ValueError, 'empty'):
            self.assets()

    def test_invalid_digest_rejected(self):
        self.item['sha256'] = 'invalid'
        with self.assertRaisesRegex(ValueError, 'digest'):
            self.assets()


if __name__ == '__main__':
    unittest.main()
