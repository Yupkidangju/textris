"""제품 재생은 외부 플레이어나 BEL 없이 네이티브 PCM과 패키지 리소스를 쓴다."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

from textris.audio import Audio, find_backend
from textris.soundtrack import AssetLibrary
from textris.storage import DEFAULTS
from tests.test_soundtrack_audio import make_assets
from tests.filesystem_helpers import symlink_or_skip


class SilentAudioTests(unittest.TestCase):
    def wait_for(self, condition):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if condition(): return
            time.sleep(.01)
        self.fail('audio worker condition timed out')

    def test_backend_selection_never_searches_or_launches_external_player(self):
        with patch('shutil.which') as which, patch('subprocess.Popen') as launch:
            self.assertEqual(find_backend(), ('miniaudio', 'native'))
            with patch('textris.audio.miniaudio', None): self.assertIsNone(find_backend())
        which.assert_not_called(); launch.assert_not_called()

    def test_missing_dependency_and_assets_stay_silent_without_files_or_bell(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, patch('textris.audio.miniaudio', None), patch('textris.audio.resource_root', return_value=Path(tmp) / 'missing'):
            with redirect_stdout(output), redirect_stderr(output):
                audio = Audio(Path(tmp) / 'data', dict(DEFAULTS))
                try:
                    audio.set_music(True)
                    for name in ('drop', 'hold', 'clear'): audio.play(name)
                    self.assertTrue(audio.ready.wait(2))
                    self.assertEqual(audio.status, 'audio_silent')
                    self.assertTrue(audio.requests.empty())
                    self.assertEqual(audio.diagnostics['active_voices'], 0)
                    self.assertFalse((Path(tmp) / 'data').exists())
                    self.assertTrue(audio.music_state['error'])
                finally: audio.close()
            self.assertFalse(audio.thread.is_alive())
            self.assertEqual(output.getvalue(), '')

    def test_missing_music_catalog_does_not_disable_valid_effect_catalog(self):
        from tests.test_soundtrack_audio import FakeDevice
        device = FakeDevice()
        def launch(callback): device.start(callback); return device
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'assets'; make_assets(root)
            (root / 'music.json').unlink()
            with patch('textris.audio.resource_root', return_value=root), patch('textris.audio.open_device', side_effect=launch):
                audio = Audio(Path(tmp) / 'data', dict(DEFAULTS))
                try:
                    self.assertTrue(audio.ready.wait(2))
                    self.assertEqual(audio.catalog, ())
                    audio.play('tetris')
                    self.wait_for(lambda: audio.diagnostics['active_voices'] == 1)
                    self.assertTrue(any(device.pump()))
                finally: audio.close()
            self.assertTrue(device.closed)


class PackagedResourcesTests(unittest.TestCase):
    def test_zip_resources_extract_with_hash_inside_data_root_and_repair_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; make_assets(root)
            archive = Path(tmp) / 'assets.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                for path in root.iterdir(): bundle.write(path, 'audio/' + path.name)
            with zipfile.ZipFile(archive) as bundle:
                library = AssetLibrary(zipfile.Path(bundle, 'audio/'), Path(tmp) / 'data')
                library.load()
                row = library.tracks[0]; path = library.path(row)
                self.assertTrue(path.resolve().is_relative_to((Path(tmp) / 'data').resolve()))
                self.assertEqual(path.name, row['sha256'] + '.wav')
                self.assertEqual(path.read_bytes(), (root / row['file']).read_bytes())
                path.write_bytes(b'corrupt cache')
                self.assertEqual(library.path(row).read_bytes(), (root / row['file']).read_bytes())
                self.assertFalse(list(path.parent.glob('*.tmp')))

    def test_zip_hash_failure_preserves_existing_cache_and_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; make_assets(root)
            archive = Path(tmp) / 'assets.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                for path in root.iterdir(): bundle.write(path, 'audio/' + path.name)
            with zipfile.ZipFile(archive) as bundle:
                library = AssetLibrary(zipfile.Path(bundle, 'audio/'), Path(tmp) / 'data'); library.load()
                good = library.path(library.tracks[0])
                bad = dict(library.tracks[1], sha256='f' * 64)
                with self.assertRaises(ValueError): library.path(bad)
                self.assertTrue(good.exists())
                self.assertEqual(list(good.parent.iterdir()), [good])

    def test_cache_symlink_cannot_write_outside_data_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; make_assets(root)
            data = Path(tmp) / 'data'; data.mkdir()
            outside = Path(tmp) / 'outside'; outside.mkdir()
            symlink_or_skip(data / 'audio-cache', outside, directory=True)
            archive = Path(tmp) / 'assets.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                for path in root.iterdir(): bundle.write(path, 'audio/' + path.name)
            with zipfile.ZipFile(archive) as bundle:
                library = AssetLibrary(zipfile.Path(bundle, 'audio/'), data); library.load()
                with self.assertRaises(ValueError): library.path(library.tracks[0])
            self.assertEqual(list(outside.iterdir()), [])

    def test_failed_cache_capacity_check_removes_the_new_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'; make_assets(root)
            archive = Path(tmp) / 'assets.zip'
            with zipfile.ZipFile(archive, 'w') as bundle:
                for path in root.iterdir(): bundle.write(path, 'audio/' + path.name)
            with zipfile.ZipFile(archive) as bundle:
                library = AssetLibrary(zipfile.Path(bundle, 'audio/'), Path(tmp) / 'data'); library.load()
                with patch('textris.soundtrack.MAX_CACHE_BYTES', 32 * 1024):
                    with self.assertRaisesRegex(ValueError, 'capacity'):
                        library.path(library.tracks[0])
                self.assertEqual(list((Path(tmp) / 'data' / 'audio-cache').iterdir()), [])


if __name__ == '__main__': unittest.main()
