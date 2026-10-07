"""재생기 부재와 실패가 터미널 경고음으로 바뀌지 않는지 검증한다."""
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from textris.audio import Audio
from textris.storage import DEFAULTS


class Process:
    def __init__(self):
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.returncode = -9


class SilentAudioTests(unittest.TestCase):
    def wait_for(self, condition):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(.01)
        self.fail('audio worker condition timed out')

    def assert_silent(self, audio):
        self.assertEqual(audio.status, 'audio_silent')
        bell_events = getattr(audio, 'bells', None)
        if bell_events is not None:
            self.assertTrue(bell_events.empty(), 'silent audio must not request a terminal bell')

    def test_missing_player_handles_effects_and_music_without_bell_or_output(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, patch('textris.audio.shutil.which', return_value=None):
            with redirect_stdout(output), redirect_stderr(output):
                audio = Audio(Path(tmp), dict(DEFAULTS))
                try:
                    audio.set_music(True)
                    for name in ('drop', 'hold', 'clear'):
                        audio.play(name)
                    self.wait_for(lambda: audio.requests.empty())
                    self.assert_silent(audio)
                    self.assertIsNone(audio.music_process)
                    self.assertEqual(audio.effects, [])
                    self.assertEqual(list(Path(tmp).iterdir()), [])
                finally:
                    audio.close()
            self.assertFalse(audio.thread.is_alive())
            self.assertEqual(output.getvalue(), '')

    def test_launch_failure_stays_silent(self):
        with tempfile.TemporaryDirectory() as tmp, patch('textris.audio.find_backend', return_value=('ffplay', 'fake')):
            with patch('textris.audio.subprocess.Popen', side_effect=OSError('unavailable')):
                audio = Audio(Path(tmp), dict(DEFAULTS))
                try:
                    audio.play('drop')
                    self.wait_for(lambda: audio.failed)
                    audio.play('clear')
                    self.wait_for(lambda: audio.requests.empty())
                    self.assert_silent(audio)
                finally:
                    audio.close()
                self.assertFalse(audio.thread.is_alive())

    def test_nonzero_exit_stops_music_and_other_effects(self):
        with tempfile.TemporaryDirectory() as tmp, patch('textris.audio.find_backend', return_value=('aplay', 'fake')):
            with patch('textris.audio.subprocess.Popen', side_effect=lambda *args, **kwargs: Process()):
                audio = Audio(Path(tmp), dict(DEFAULTS))
                try:
                    audio.set_music(True)
                    self.wait_for(lambda: audio.music_process is not None)
                    music = audio.music_process
                    audio.play('drop')
                    audio.play('clear')
                    self.wait_for(lambda: len(audio.effects) == 2)
                    first, second = audio.effects
                    first.returncode = 1
                    self.wait_for(lambda: audio.failed)
                    self.wait_for(lambda: second.poll() is not None and music.poll() is not None)
                    self.assert_silent(audio)
                finally:
                    audio.close()


if __name__ == '__main__':
    unittest.main()
