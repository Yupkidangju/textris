"""진단이 백엔드 완료와 앱/OS 음소거 및 청취를 혼동하지 않는다."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from textris.__main__ import main


class AudioCheckTests(unittest.TestCase):
    def test_completed_backend_does_not_claim_audible_output(self):
        result=dict(backend='waveout',backend_completed=True,app_sound=True,
            app_music=True,app_volume=.5,app_muted=False,
            os_output=dict(available=True,master_volume=0.,master_muted=True),
            listening_confirmed=False)
        with tempfile.TemporaryDirectory() as tmp, patch('textris.__main__.check_audio',return_value=result):
            out=io.StringIO()
            with redirect_stdout(out): code=main(['--audio-check','--data-dir',tmp])
        self.assertEqual(code,0)
        self.assertIn('Backend completion: PASS',out.getvalue())
        self.assertIn('OS output: muted=True / volume=0%',out.getvalue())
        self.assertIn('Listening: unconfirmed',out.getvalue())

    def test_muted_or_unavailable_is_explicit_failure(self):
        result=dict(backend='waveout',backend_completed=False,app_sound=False,
            app_music=True,app_volume=.5,app_muted=True,
            os_output=dict(available=False),listening_confirmed=False)
        with tempfile.TemporaryDirectory() as tmp, patch('textris.__main__.check_audio',return_value=result) as check:
            out=io.StringIO()
            with redirect_stdout(out): code=main(['--audio-check','--no-sound','--data-dir',tmp])
            self.assertFalse(check.call_args.args[1]['sound'])
        self.assertEqual(code,1)
        self.assertIn('OS output: unknown',out.getvalue())
        self.assertIn('muted=True',out.getvalue())
