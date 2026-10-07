"""symlink 권한이 없어도 실제 Windows junction의 경로 탈출을 검증한다."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from textris.audio import audio_path
from textris.replay import ReplayStore
from textris.session import Session


@unittest.skipUnless(sys.platform == 'win32', 'Windows directory junction integration')
class WindowsPathTests(unittest.TestCase):
    def check_junction(self, name):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'data'; root.mkdir()
            outside=Path(tmp)/'outside'; outside.mkdir()
            link=root/name
            env=dict(os.environ, TEXTRIS_TEST_LINK=str(link), TEXTRIS_TEST_TARGET=str(outside))
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
                'New-Item -ItemType Junction -Path $env:TEXTRIS_TEST_LINK -Target $env:TEXTRIS_TEST_TARGET -ErrorAction Stop | Out-Null'],
                env=env,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            try:
                self.assertEqual(link.resolve(),outside.resolve())
                if name=='audio':
                    with self.assertRaises(ValueError): audio_path(root,'move-5.wav')
                else:
                    self.assertIsNone(ReplayStore(root).save(Session(seed=1).replay()))
                self.assertEqual(list(outside.iterdir()),[])
            finally:
                # rmdir는 이 테스트가 생성한 junction 자체만 제거한다.
                link.rmdir()

    def test_audio_junction_cannot_escape(self): self.check_junction('audio')
    def test_replay_junction_cannot_escape(self): self.check_junction('replays')
