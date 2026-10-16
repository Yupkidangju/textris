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
from textris.storage import Store


@unittest.skipUnless(sys.platform == 'win32', 'Windows directory junction integration')
class WindowsPathTests(unittest.TestCase):
    def junction(self,link,target):
        env=dict(os.environ,TEXTRIS_TEST_LINK=str(link),TEXTRIS_TEST_TARGET=str(target))
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
            'New-Item -ItemType Junction -Path $env:TEXTRIS_TEST_LINK -Target $env:TEXTRIS_TEST_TARGET -ErrorAction Stop | Out-Null'],
            env=env,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(link.resolve(),target.resolve())

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

    def test_store_directory_junction_blocks_read_and_save_without_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'data'; outside=Path(tmp)/'outside'; outside.mkdir()
            original=b'{"version":1,"settings":{"volume":0.9}}'
            (outside/'records.json').write_bytes(original)
            self.junction(root,outside)
            try:
                reader=Store(root); reader.load()
                self.assertTrue(reader.read_only); self.assertEqual(reader.warning,'save_read')
                self.assertEqual(reader.settings['volume'],.5)
                writer=Store(root); self.assertFalse(writer.save())
                self.assertEqual(writer.warning,'save_write')
                self.assertEqual((outside/'records.json').read_bytes(),original)
                self.assertEqual(sorted(p.name for p in outside.iterdir()),['records.json'])
            finally: root.rmdir()

    def test_store_directory_replaced_by_junction_after_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'data'; root.mkdir(); outside=Path(tmp)/'outside'; outside.mkdir()
            store=Store(root); store.load(); root.rmdir()
            self.junction(root,outside)
            try:
                self.assertFalse(store.save()); self.assertEqual(store.warning,'save_write')
                self.assertEqual(list(outside.iterdir()),[])
            finally: root.rmdir()

    def test_store_parent_retargeted_after_construction(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp)/'parent'; (parent/'data').mkdir(parents=True)
            outside=Path(tmp)/'outside'; (outside/'data').mkdir(parents=True)
            original=b'{"version":1,"settings":{"volume":0.9}}'
            target=outside/'data'/'records.json'; target.write_bytes(original)
            store=Store(parent/'data')
            (parent/'data').rmdir(); parent.rmdir(); self.junction(parent,outside)
            try:
                store.load(); self.assertTrue(store.read_only)
                self.assertEqual(store.settings['volume'],.5)
                self.assertFalse(store.save()); self.assertEqual(target.read_bytes(),original)
            finally: parent.rmdir()

    def test_store_record_junction_blocks_read_and_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'data'; root.mkdir(); outside=Path(tmp)/'outside'; outside.mkdir()
            sentinel=outside/'keep.txt'; sentinel.write_text('keep')
            link=root/'records.json'; self.junction(link,outside)
            try:
                reader=Store(root); reader.load(); self.assertTrue(reader.read_only)
                writer=Store(root); self.assertFalse(writer.save())
                self.assertEqual(sentinel.read_text(),'keep')
                self.assertEqual(sorted(p.name for p in outside.iterdir()),['keep.txt'])
                self.assertTrue(link.is_dir())
            finally: link.rmdir()

    def test_store_roundtrip_with_extended_windows_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'data'
            long_root=Path('\\\\?\\'+str(root))
            store=Store(long_root); self.assertTrue(store.save())
            loaded=Store(root); loaded.load()
            self.assertFalse(loaded.read_only)
            self.assertEqual(loaded.settings,store.settings)

    def test_store_dangling_junctions_are_blocked_before_missing_file_return(self):
        for leaf in (False,True):
            with self.subTest(record_leaf=leaf), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)/'data'; outside=Path(tmp)/'outside'; outside.mkdir()
                if leaf: root.mkdir()
                link=root/'records.json' if leaf else root
                self.junction(link,outside); outside.rmdir()
                try:
                    reader=Store(root); reader.load()
                    self.assertTrue(reader.read_only)
                    self.assertEqual(reader.warning,'save_read')
                    self.assertFalse(Store(root).save())
                    self.assertFalse(outside.exists())
                finally: link.rmdir()
