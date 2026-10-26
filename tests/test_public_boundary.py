from pathlib import Path
import subprocess
import tempfile
import unittest
from scripts.check_public import MAX_TEXT_BYTES, audit, path_problem


class PublicBoundary(unittest.TestCase):
    def test_generated_and_private_files(self):
        for name in ('private/settings.json', 'recordings/take.wav', 'voice.onnx', 'voice.tflite', 'host.local.json', 'state.tfstate'):
            with self.subTest(name=name):
                self.assertIsNotNone(path_problem(name))
        self.assertIsNone(path_problem('docs/migration.md'))

    def test_staged_secret_survives_working_file_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', directory], check=True)
            path = root / 'settings.txt'
            path.write_text('password = "' + 'not' + '_an_example_credential"\n')
            subprocess.run(['git', '-C', directory, 'add', 'settings.txt'], check=True)
            path.write_text('clean working file\n')
            count, issues = audit(root)
            self.assertEqual(count, 1)
            self.assertTrue(any('possible credential' in issue for issue in issues))
            self.assertFalse(any('not_an_example_credential' in issue for issue in issues))


    def test_oversized_working_file_is_not_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', directory], check=True)
            path = root / 'readme.txt'
            path.write_text('small safe text')
            subprocess.run(['git', '-C', directory, 'add', 'readme.txt'], check=True)
            path.write_bytes(b'x' * (MAX_TEXT_BYTES + 1))
            _, issues = audit(root)
            self.assertTrue(any('oversized working' in issue for issue in issues))


if __name__ == '__main__':
    unittest.main()
