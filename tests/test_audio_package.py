"""누락·변조·경로 탈출 음원을 배포 전에 차단한다."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

EFFECT_IDS=('ui_move','ui_select','ui_back','ui_toggle','ui_error','countdown','go','pause','resume',
            'move','rotate','hold','drop','lock','clear_single','clear_double','clear_triple','tetris',
            'tspin','all_clear','combo','b2b','fever_start','fever_end','level','danger','win','gameover','boss_hit','boss_break')

class AudioPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'music').mkdir(); (self.root/'sfx').mkdir()
        self.tracks=[];self.effects=[]
        themes=['cathedral']*3+['cyberpunk']*3+['space']*3+['fire']*3+['crt']*3+['mono']*3+['classic']*8
        for i,theme in enumerate(themes):
            data=b'OggS'+bytes([i])*32
            name=f'music/{i}.ogg';(self.root/name).write_bytes(data)
            self.tracks.append(dict(id=f'track_{i}',theme=theme,file=name,duration=90,
                title=str(i),bpm=120,time_signature='4/4',instruments=['a','b','c','d'],sha256=hashlib.sha256(data).hexdigest()))
        for i,identity in enumerate(EFFECT_IDS):
            data=b'RIFF'+bytes([i])*32
            name=f'sfx/{i}.wav';(self.root/name).write_bytes(data)
            self.effects.append(dict(id=identity,file=name,duration=.1,gain=.5,priority=1,cooldown=.1,sha256=hashlib.sha256(data).hexdigest()))
        self.save()

    def save(self):
        (self.root/'music.json').write_text(json.dumps(dict(version=1,tracks=self.tracks)))
        (self.root/'sfx.json').write_text(json.dumps(dict(version=1,effects=self.effects)))

    def test_full_inventory_and_hashes(self):
        from textris.asset_check import verify_audio_assets
        result=verify_audio_assets(self.root)
        self.assertEqual((result['tracks'],result['effects']),(26,30))

    def test_missing_or_modified_asset_fails(self):
        from textris.asset_check import verify_audio_assets
        (self.root/'music/0.ogg').write_bytes(b'changed')
        with self.assertRaises(ValueError): verify_audio_assets(self.root)
        (self.root/'music/0.ogg').unlink()
        with self.assertRaises(ValueError): verify_audio_assets(self.root)

    def test_escape_and_duplicate_ids_fail(self):
        from textris.asset_check import verify_audio_assets
        self.tracks[0]['file']='../outside.ogg'; self.save()
        with self.assertRaises(ValueError): verify_audio_assets(self.root)
        self.tracks[0]['file']='music/0.ogg';self.tracks[0]['id']=self.tracks[1]['id'];self.save()
        with self.assertRaises(ValueError): verify_audio_assets(self.root)

    def test_wrong_theme_count_and_track_duration_fail(self):
        from textris.asset_check import verify_audio_assets
        self.tracks[0]['theme']='classic';self.save()
        with self.assertRaises(ValueError): verify_audio_assets(self.root)
        self.tracks[0]['theme']='cathedral';self.tracks[0]['duration']=8;self.save()
        with self.assertRaises(ValueError): verify_audio_assets(self.root)

    def test_runtime_rejected_metadata_and_unmapped_cue_fail(self):
        from textris.asset_check import verify_audio_assets
        self.tracks[0]['bpm']=None;self.save()
        with self.assertRaises(ValueError): verify_audio_assets(self.root)
        self.tracks[0]['bpm']=120;self.effects[0]['id']='unmapped_effect';self.save()
        with self.assertRaises(ValueError): verify_audio_assets(self.root)
