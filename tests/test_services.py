import json
from pathlib import Path
import struct
import tempfile
import unittest
import wave
from textris.storage import Store
from textris.audio import synthesize
from textris.i18n import STRINGS, tr


class ServicesTests(unittest.TestCase):
    def test_storage_roundtrip_and_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Store(Path(tmp)); s.load()
            s.settings['language'] = 'en'
            for score in range(15):
                s.record('marathon', dict(score=score,lines=1,level=1,seconds=5.,completed=False,date='2026-10-07'))
            t = Store(Path(tmp)); t.load()
            self.assertEqual(t.settings['language'], 'en')
            self.assertEqual(len(t.records['marathon']), 10)
            self.assertEqual(t.records['marathon'][0]['score'],14)
            self.assertFalse(list(Path(tmp).glob('*.tmp')))

    def test_corrupt_file_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'records.json'; p.write_text('{broken')
            s = Store(Path(tmp)); s.load(); s.save()
            self.assertTrue(s.warning)
            self.assertEqual(p.read_text(), '{broken')

    def test_invalid_settings_and_records_filtered(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'records.json').write_text(json.dumps({'version':1,
                'settings':{'volume':500,'language':'xx','sound':'yes','ascii':True},
                'records':{'sprint':[{'score':-1},None]}}))
            s = Store(Path(tmp)); s.load()
            self.assertEqual(s.settings['volume'],.5)
            self.assertEqual(s.settings['language'],'ko')
            self.assertIs(s.settings['sound'],True)
            self.assertIs(s.settings['ascii'],True)
            self.assertEqual(s.records['sprint'],[])

    def test_sprint_completed_first_and_time_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Store(Path(tmp)); s.load()
            for seconds, done in [(1,False),(90,True),(60,True)]:
                s.record('sprint',dict(score=100,lines=40,level=5,seconds=seconds,completed=done,date='2026-10-07'))
            self.assertEqual([r['seconds'] for r in s.records['sprint']],[60,90,1])

    def test_wav_signal_and_music(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('move','rotate','hold','drop','lock','clear','tetris','level','gameover','win','music'):
                p = Path(tmp)/(name+'.wav'); synthesize(name,p,.5)
                with wave.open(str(p),'rb') as f:
                    self.assertEqual(f.getnchannels(),1)
                    self.assertEqual(f.getsampwidth(),2)
                    self.assertEqual(f.getframerate(),22050)
                    raw = f.readframes(f.getnframes())
                    data = struct.unpack('<'+'h'*(len(raw)//2),raw)
                    self.assertGreater(max(data),100)
                    self.assertLess(min(data),-100)
                    self.assertLessEqual(max(abs(v) for v in data),32767)
                    if name == 'music': self.assertGreater(len(data)/22050,5)

    def test_translation_keys(self):
        self.assertEqual(set(STRINGS['ko']),set(STRINGS['en']))
        for lang in STRINGS:
            self.assertEqual(tr(lang,'level',value=2), STRINGS[lang]['level'].format(value=2))



class StorageFailureTests(unittest.TestCase):
    def test_stat_permission_error_is_nonfatal(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp))
            with patch.object(Path,'exists',side_effect=PermissionError('blocked')):
                s.load()
            self.assertEqual(s.warning,'save_read')

    def test_temp_cleanup_permission_error_is_nonfatal(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            s=Store(Path(tmp))
            with patch.object(Path,'replace',side_effect=PermissionError('blocked')), patch.object(Path,'unlink',side_effect=PermissionError('blocked')):
                self.assertFalse(s.save())
            self.assertEqual(s.warning,'save_write')

    def test_huge_json_numbers_are_filtered_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            row=dict(score=1,lines=1,level=1,seconds=10**400,completed=False,date='2026-10-07')
            (Path(tmp)/'records.json').write_text(json.dumps(dict(version=1,settings=dict(volume=10**400),records=dict(marathon=[row]))))
            s=Store(Path(tmp)); s.load()
            self.assertEqual(s.settings['volume'],.5)
            self.assertEqual(s.records['marathon'],[])

class AudioBoundaryTests(unittest.TestCase):
    def test_audio_symlink_cannot_write_outside_data_root(self):
        from textris.audio import audio_path
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'data'; root.mkdir()
            outside=Path(tmp)/'outside'; outside.mkdir()
            (root/'audio').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(ValueError): audio_path(root,'move-5.wav')
            self.assertFalse(list(outside.iterdir()))

    def test_wav_leaf_symlink_cannot_write_outside_data_root(self):
        from textris.audio import audio_path
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'data'; (root/'audio').mkdir(parents=True)
            (root/'audio'/'move-5.wav').symlink_to(Path(tmp)/'outside.wav')
            with self.assertRaises(ValueError): audio_path(root,'move-5.wav')

class AudioLifecycleTests(unittest.TestCase):
    def wait_for(self, condition):
        import time
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            if condition(): return
            time.sleep(.01)
        self.fail('audio worker condition timed out')

    def test_music_pause_mute_close_and_failed_backend_fallback(self):
        from unittest.mock import patch
        from textris.audio import Audio
        from textris.storage import DEFAULTS
        class Process:
            def __init__(self): self.returncode=None; self.terminated=False
            def poll(self): return self.returncode
            def terminate(self): self.terminated=True; self.returncode=0
            def wait(self,timeout=None): return self.returncode
            def kill(self): self.returncode=-9
        processes=[]
        def launch(*args,**kw):
            p=Process(); processes.append(p); return p
        with tempfile.TemporaryDirectory() as tmp:
            settings=dict(DEFAULTS)
            with patch('textris.audio.find_backend',return_value=('aplay','fake')), patch('textris.audio.subprocess.Popen',side_effect=launch):
                audio=Audio(Path(tmp),settings)
                try:
                    audio.set_music(True)
                    self.wait_for(lambda: audio.music_process is not None)
                    music=audio.music_process
                    audio.set_music(False)
                    self.wait_for(lambda: music.terminated)
                    audio.play('drop')
                    self.wait_for(lambda: bool(audio.effects))
                    effect=audio.effects[0]
                    settings['sound']=False
                    self.wait_for(lambda: effect.terminated)
                    settings['sound']=True
                    audio.play('clear')
                    self.wait_for(lambda: bool(audio.effects))
                    audio.effects[0].returncode=1
                    self.wait_for(lambda: audio.failed)
                    self.wait_for(lambda: not audio.bells.empty())
                    self.assertEqual(audio.status,'audio_bell')
                finally:
                    audio.close()
                self.assertFalse(audio.thread.is_alive())
                self.assertTrue(all(p.poll() is not None for p in processes))

if __name__ == '__main__': unittest.main()
