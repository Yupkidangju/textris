"""시각 테마 확장이 저장과 기존 음악 분류를 깨뜨리지 않는지 검사한다."""
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from textris.audio import Audio
from textris.art import THEME_COLORS
from textris.scenes import THEMES
from textris.storage import Store, DEFAULTS
from textris.soundtrack import BalancedShuffle
from textris.themes import MUSIC_THEMES, music_theme
from tests.test_soundtrack_ui import soundtrack_catalog
from textris.ui import App
from tests.test_ui import AudioStub, Window


class EightThemeIntegrationTests(unittest.TestCase):
    def test_profiles_cycle_all_themes_and_preserve_game_and_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(Path(directory)); store.load()
            audio=AudioStub()
            with patch.object(App,'_setup'):
                app=App(Window(),store,audio,42)
            app.screen='profiles'; app.profile_selection=0
            seen=[]
            for _ in THEMES:
                app.handle('d'); seen.append(app.settings['theme'])
            self.assertEqual(seen,list(THEMES[1:]+THEMES[:1]))
            self.assertIsNone(app.game); self.assertIsNone(app.session)
            loaded=Store(Path(directory)); loaded.load()
            self.assertEqual(loaded.settings['theme'],'cathedral')
            self.assertEqual(loaded.records,store.records)

    def test_new_visual_ids_roundtrip_without_migrating_existing_save(self):
        self.assertEqual(THEMES[-2:], ('abyss', 'aurora'))
        for theme in THEMES:
            with self.subTest(theme=theme), tempfile.TemporaryDirectory() as directory:
                store=Store(Path(directory)); store.load()
                store.settings['theme']=theme
                store.save()
                loaded=Store(Path(directory)); loaded.load()
                self.assertEqual(loaded.settings['theme'], theme)
                self.assertEqual(len(THEME_COLORS[theme]), 23)
                self.assertEqual(loaded.records, store.records)

    def test_visual_music_mapping_keeps_balanced_complete_classic_pool(self):
        tracks=soundtrack_catalog()
        by_id={row['id']:row for row in tracks}
        before=random.getstate()
        for theme, source in [('abyss','space'),('aurora','mono')]:
            self.assertEqual(music_theme(theme),source)
            shuffle=BalancedShuffle(tracks,music_theme(theme),random.Random(102))
            chosen=[by_id[shuffle.next()] for _ in range(32)]
            self.assertEqual(sum(row['theme']==source for row in chosen),16)
            self.assertEqual(sum(row['theme']=='classic' for row in chosen),16)
            classics=[row['id'] for row in chosen if row['theme']=='classic']
            self.assertEqual(len(set(classics[:8])),8)
        self.assertEqual(random.getstate(),before)
        self.assertEqual(len(MUSIC_THEMES),6)

    def test_worker_normalizes_both_startup_and_theme_switches(self):
        for theme, source in [('abyss','space'),('aurora','mono')]:
            with patch('textris.audio.threading.Thread.start'):
                audio=Audio(Path('.'),dict(DEFAULTS,theme=theme))
            self.assertEqual(audio._theme,source)
            audio._catalog=soundtrack_catalog()
            other='aurora' if theme=='abyss' else 'abyss'
            with patch.object(audio,'_select') as select:
                audio.set_theme(other); audio._handle_commands()
            self.assertEqual(audio._theme,music_theme(other))
            self.assertEqual(select.call_count,1)
            self.assertIn(select.call_args.args[0],{t['id'] for t in audio._catalog
                if t['theme'] in (music_theme(other),'classic')})


if __name__=='__main__': unittest.main()
