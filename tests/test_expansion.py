from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests import test_ui
from textris.effects import Effects
from textris import scenes


class ExpansionTests(unittest.TestCase):
    setUp=test_ui.UITests.setUp

    def test_catalog_all_backgrounds_and_effects_render_bounded(self):
        a=self.app; a.screen='gallery'
        self.assertGreaterEqual(len(scenes.BACKGROUNDS),17)
        self.assertGreaterEqual(len(scenes.EFFECTS),24)
        a.win.size=(40,120)
        for ascii_mode in (False,True):
            a.settings['ascii']=ascii_mode
            for name in scenes.BACKGROUNDS:
                a.effects.scene=name
                for t in (100,100.1):
                    a.now=t; a.win.erase(); a.effects.background(a,t)
                    self.assertTrue(a.win.lines,name)
            for name in scenes.EFFECTS:
                a.effects=Effects(); a.effects.preview(name,100)
                for t in (100.1,100.5,101):
                    a.win.erase(); a.effects.update(t); a.effects.draw(a,25,5,t)
                    self.assertTrue(a.win.lines,name)
        a.effects.update(110); self.assertFalse(a.effects.actions)

    def test_fever_profile_and_priority(self):
        fx=Effects()
        data=dict(rows=[18,19,20,21],count=4,spin=False,combo=7,b2b=True,perfect=True,points=4000)
        fx.trigger('clear',data,100)
        self.assertGreater(fx.fever_until,100)
        self.assertEqual(fx.headline,'ALL CLEAR')
        fx.trigger('lock',dict(cells=((1,21),)),100)
        self.assertEqual(fx.headline,'ALL CLEAR')
        self.assertLessEqual(len(fx.director.local),8)
        fx.update(110); self.assertEqual(fx.fever,0)

    def test_replay_store_validation_and_preservation(self):
        from textris.session import Session
        from textris.replay import ReplayStore,Player
        s=Session(seed=42); s.command('drop'); s.step()
        r=ReplayStore(self.tmp.name); name=r.save(s.replay())
        self.assertIsNotNone(name)
        p=Player(r.load(name)); p.seek(1); self.assertTrue(p.verified)
        with self.assertRaises(ValueError): r.load('../records.json')
        data=s.replay(); data['actions']=[[0,'evil']]
        self.assertIsNone(r.save(data)); self.assertEqual(len(r.list()),1)

    def test_new_settings_and_boss_records_roundtrip(self):
        from textris.storage import Store
        self.store.settings.update(theme='fire',fx_intensity=.5,fx_speed=1.5,fx_density=.25,shake=False,flash=False,braille=False)
        self.store.record('boss',dict(score=20,lines=2,level=1,seconds=10,completed=True,date='2026-10-07'))
        other=Store(Path(self.tmp.name)); other.load()
        self.assertEqual(other.settings['theme'],'fire')
        self.assertEqual(len(other.records['boss']),1)
        self.assertEqual(other.settings['fx_speed'],1.5)

    def test_autoplay_legal_commands_and_input_path(self):
        from textris.autoplay import Autoplayer
        from textris.session import Session
        s=Session(seed=42,record=False); bot=Autoplayer(); placements=0
        for _ in range(10000):
            action=bot.next(s.game)
            if action:
                s.command(action)
                placements+=action=='drop'
            s.step(); s.game.events.clear()
            if s.game.state!='playing' or placements>=40: break
        self.assertGreaterEqual(placements,25)
        self.assertGreater(s.game.lines,0)
        self.assertFalse(s.actions)

    def test_hub_gallery_profiles_and_autoplay_ui(self):
        a=self.app; a.now=100
        a.handle('e'); self.assertEqual(a.screen,'hub')
        a.handle('\n'); self.assertEqual(a.screen,'gallery')
        a.handle(' '); self.assertEqual(a.effects.scene,'rain')
        a.gallery_index=len(scenes.BACKGROUNDS); a.handle(' '); self.assertTrue(a.effects.actions)
        a.gallery_index=0
        a.handle('d'); self.assertEqual(a.gallery_index,1)
        with patch('curses.doupdate'): a.draw()
        a.handle('\x1b'); self.assertEqual(a.screen,'hub')
        a.handle('s'); a.handle('\n'); self.assertEqual(a.screen,'profiles')
        a.handle('d'); self.assertEqual(a.settings['theme'],'cyberpunk')
        a.handle('\x1b'); a.handle('s'); a.handle('\n')
        self.assertEqual(a.session.mode,'boss'); self.assertEqual(a.screen,'ready')
        a.tick(3); self.assertEqual(a.screen,'playing')
        a.tick(.05); self.assertGreater(a.session.tick,0)
        a.screen='hub'; a.hub_selection=4; a.handle('\n')
        self.assertEqual(a.screen,'autoplay')
        a.tick(.1); self.assertFalse(a.session.recording)
        a.handle('\x1b'); self.assertEqual(a.screen,'hub')

    def test_ui_final_replay_analysis_and_pause(self):
        a=self.app; a.start('marathon'); a.screen='playing'; a.game.state='playing'; a.now=100
        a.game.board[0][0]='I'; a.handle(' '); a.tick(.01)
        self.assertEqual(a.screen,'result')
        self.assertTrue(a.replays.list())
        a.handle('a'); self.assertEqual(a.screen,'analysis')
        with patch('curses.doupdate'): a.draw()
        a.handle('\x1b'); self.assertEqual(a.screen,'result')

    def test_particles_bounce_and_flash_shake_controls(self):
        from textris.particles import Particle
        p=Particle(100,31,19,30,20,2,'I',0,100)
        p.advance(100.2)
        self.assertLessEqual(p.x,32); self.assertLessEqual(p.y,20)
        self.assertLess(p.vx,0)
        a=self.app; a.settings['shake']=False; a.effects.configure(a.settings)
        a.effects.preview('impact',100)
        self.assertEqual(a.effects.offset(100.05),(0,0))
        a.settings['flash']=False; a.effects.update(103)
        self.assertFalse(a.effects.actions)

    def test_replay_path_symlink_and_recent_twenty(self):
        from textris.replay import ReplayStore
        from textris.session import Session
        s=Session(seed=1); s.command('drop'); s.step()
        r=ReplayStore(self.tmp.name)
        for _ in range(22): self.assertIsNotNone(r.save(s.replay()))
        self.assertEqual(len(r.list()),20)
        with tempfile.TemporaryDirectory() as other:
            unsafe=Path(self.tmp.name)/'outside'
            unsafe.mkdir(); (unsafe/'replays').symlink_to(other,target_is_directory=True)
            store=ReplayStore(unsafe)
            self.assertIsNone(store.save(s.replay()))
            self.assertFalse(list(Path(other).iterdir()))

    def test_expanded_screens_modes_and_locales_clip_and_freeze(self):
        a=self.app
        with patch('curses.doupdate'):
            for lang in ('ko','en'):
                a.settings['language']=lang
                for size in ((28,64),(40,120)):
                    a.win.size=size
                    for ascii_mode in (False,True):
                        a.settings['ascii']=ascii_mode
                        for theme in scenes.THEMES:
                            a.settings['theme']=theme
                            a.start('boss'); a.screen='playing'; a.game.state='playing'
                            for screen in ('hub','profiles','gallery','replays','analysis','playing'):
                                a.screen=screen; a.draw(); self.assertTrue(a.win.lines)
            a.screen='playing'; a.game.state='playing'; a.tick(.1); tick=a.session.tick
            a.handle('p'); a.tick(20); self.assertEqual(a.session.tick,tick)

    def test_gallery_auto_and_replay_analysis_shortcuts(self):
        a=self.app; a.open_gallery(); a.handle('a')
        self.assertTrue(a.gallery_auto)
        from textris.session import Session
        s=Session(seed=42); s.command('drop'); s.step()
        a.open_replay(s.replay()); a.handle('a')
        self.assertEqual(a.screen,'analysis')
        a.tick(.1); a.handle('\x1b'); a.tick(.1)
        self.assertNotEqual(a.game.state,'paused')

    def test_composed_frame_limits_terminal_writes_under_storm(self):
        a=self.app; a.start(); a.screen='playing'; a.win.size=(40,120); a.now=100
        data=dict(rows=[18,19,20,21],count=4,spin=False,combo=8,b2b=True,perfect=True,points=4000)
        for _ in range(5): a.effects.trigger('clear',data,100)
        a.now+=.1
        with patch('curses.doupdate'): a.draw()
        self.assertLess(len(a.win.lines),1200)

    def test_music_layers_and_model_beat(self):
        import wave
        from textris.audio import synthesize,Audio
        for layer in range(4):
            path=Path(self.tmp.name)/f'music{layer}.wav'
            synthesize('music'+str(layer),path,.5)
            with wave.open(str(path)) as sound:
                self.assertEqual(sound.getnframes(),22050*8)
        audio=object.__new__(Audio); audio.music_started=100.; audio.music_process=True
        phase,beat=audio.visual_state(100.0625)
        self.assertAlmostEqual(phase,.0625); self.assertAlmostEqual(beat,1.)

    def test_visual_profiles_preserve_actual_session_checksum(self):
        from textris.ui import App
        from textris.storage import Store
        from tests.test_ui import Window,AudioStub
        other=Store(Path(self.tmp.name)/'other'); other.load()
        other.settings.update(theme='mono',fx_speed=2,fx_density=.25,shake=False)
        with patch.object(App,'_setup'),patch('curses.doupdate'):
            b=App(Window(),other,AudioStub(),seed=42)
            a=self.app
            for app in (a,b): app.start(); app.screen='playing'; app.game.state='playing'
            b.fx_enabled=False
            for key in ('a','x',' ','c','d','z',' '):
                for app in (a,b):
                    app.handle(key); app.tick(.05); app.draw()
            self.assertEqual(a.session.checksum(),b.session.checksum())

    def test_wide_character_overlap_keeps_cell_positions(self):
        a=self.app
        a._canvas=[[(' ',0)]*20]
        a.put(0,0,'가나',1); a.put(0,0,'x',2)
        from textris.ui import width
        self.assertEqual(width(''.join(c for c,attr in a._canvas[0])),20)
        a.put(0,3,'X',2)
        self.assertEqual(width(''.join(c for c,attr in a._canvas[0])),20)
        self.assertEqual(a._canvas[0][2][0],' ')
        a._canvas=None

    def test_analysis_old_selection_is_normalized(self):
        a=self.app; a.start(); a.screen='analysis'; a.highlight_selection=9
        a.session.highlights=[dict(tick=0,kind='clear',combo=1)]
        a.last_replay=a.session.replay()
        a.handle('\n')
        self.assertEqual(a.screen,'replay')

    def test_replay_pruning_preserves_unowned_files(self):
        from textris.replay import ReplayStore
        from textris.session import Session
        r=ReplayStore(self.tmp.name); r.directory.mkdir()
        user=r.directory/'replay-0000.json'; user.write_text('user content')
        s=Session(seed=1); s.command('drop'); s.step()
        for _ in range(21): r.save(s.replay())
        self.assertTrue(user.exists())
        self.assertEqual(user.read_text(),'user content')

    def test_unicode_particles_use_subcell_braille_with_ascii_fallback(self):
        a=self.app; a.screen='gallery'; a.settings.update(ascii=False,theme='cyberpunk'); a.effects.configure(a.settings)
        a.effects.preview('ricochet',100); a.effects.update(100.1)
        a.effects.draw(a,25,5,100.1)
        self.assertTrue(any(0x2800<ord(c)<=0x28ff for y,x,text in a.win.lines for c in text))
        a.settings['ascii']=True; a.win.erase(); a.effects.draw(a,25,5,100.1)
        self.assertFalse(any(0x2800<=ord(c)<=0x28ff for y,x,text in a.win.lines for c in text))

    def test_recording_limit_notice_is_visible_during_play(self):
        a=self.app; a.start(); a.screen='playing'; a.game.state='playing'
        a.session.max_actions=1
        a.handle('d'); a.tick(.02); a.handle('d'); a.tick(.02)
        with patch('curses.doupdate'): a.draw()
        self.assertTrue(any(a.t('replay_limit') in text for y,x,text in a.win.lines))
