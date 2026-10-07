"""감상 화면의 실제 App 입력, 스크롤, 저장과 게임 이력 격리를 검증한다."""
import curses
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from textris.storage import Store
from textris.ui import App
from tests.test_ui import AudioStub, Window


def soundtrack_catalog():
    tracks=[]
    for theme,count in [('cathedral',3),('cyberpunk',3),('space',3),('fire',3),('crt',3),('mono',3),('classic',8)]:
        for index in range(count):
            tracks.append(dict(id=f'{theme}-{index}',title=f'{theme.title()} Track {index+1}',
                               theme=theme,duration=90.,bpm=108.,time_signature='4/4',
                               instruments=['Lead','Harmony','Bass','Drums']))
    return tracks


class SoundtrackUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)); self.store.load()
        self.audio=AudioStub(); self.audio.catalog=soundtrack_catalog()
        with patch.object(App,'_setup'):
            self.app=App(Window(),self.store,self.audio,seed=42)

    def open_soundtrack(self):
        a=self.app; a.handle('e'); a.handle(curses.KEY_UP); a.handle('\n')
        self.assertEqual(a.screen,'soundtrack')

    def test_extras_last_item_audition_keeps_game_and_replay_history_empty(self):
        self.open_soundtrack(); a=self.app
        a.handle('\n'); a.tick(.1)
        self.assertEqual(self.audio.music_state['track_id'],'cathedral-0')
        self.assertEqual(self.audio.music_state['mode'],'audition')
        self.assertIsNone(a.session); self.assertIsNone(a.game)
        self.assertEqual(a.replays.list(),[])
        self.assertFalse(any(self.store.records.values()))
        a.handle('\x1b')
        self.assertEqual(a.screen,'hub'); self.assertEqual(self.audio.music_state['mode'],'game')

    def test_filters_scrolling_metadata_and_fixed_controls_in_ascii_and_mono(self):
        self.open_soundtrack(); a=self.app
        a.handle('\t'); self.assertEqual(len(a.soundtrack_tracks()),8)
        a.handle('\t'); self.assertEqual(len(a.soundtrack_tracks()),26)
        for _ in range(25): a.handle(curses.KEY_DOWN)
        a.handle('\n'); self.audio.music_state['error']='Device unavailable'
        for size in ((28,64),(40,120)):
            for mode in ('ascii','mono'):
                a.win.size=size; a.settings.update(display_mode='ascii',color=mode!='mono')
                if mode=='mono': a.settings['theme']='mono'
                with patch('curses.doupdate'): a.draw()
                rows={}
                for y,x,text in a.win.lines: rows[y]=rows.get(y,'')+text
                frame='\n'.join(rows.values())
                self.assertTrue(frame.isascii()); self.assertIn('Classic Track 8',frame)
                for word in ('BPM','Lead','Harmony','Bass','Drums','Device unavailable','Space','N/P','Esc/Q','+/-'):
                    self.assertIn(word,frame)
                self.assertIn('Esc/Q',rows[size[0]-2])

    def test_transport_keys_and_globals_are_reachable_without_playing(self):
        self.open_soundtrack(); a=self.app; a.handle('\n')
        self.audio.events.clear(); a.handle(' ')
        self.assertTrue(self.audio.music_state['paused']); self.assertEqual(self.audio.events,['pause'])
        self.audio.events.clear(); a.handle(' ')
        self.assertFalse(self.audio.music_state['paused']); self.assertEqual(self.audio.events,['resume'])
        a.handle('n'); a.handle('p'); a.handle(curses.KEY_RIGHT); a.handle(curses.KEY_LEFT)
        for call in [('next',1),('next',-1),('seek',5),('seek',-5)]: self.assertIn(call,self.audio.calls)
        a.handle('s'); a.handle('r')
        self.assertTrue(self.audio.music_state['shuffle']); self.assertTrue(self.audio.music_state['repeat'])
        before=a.settings['music_volume']; a.handle('+')
        self.assertGreater(a.settings['music_volume'],before)
        a.handle('m'); a.handle('b'); a.tick(.1)
        self.assertFalse(a.settings['sound']); self.assertFalse(a.settings['music'])
        self.assertEqual(self.audio.music_state['mode'],'audition')
        a.win.size=(12,30); a.tick(.1); self.assertTrue(self.audio.suspended)
        a.win.size=(28,64); a.tick(.1); self.assertFalse(self.audio.suspended)
        self.assertEqual(self.audio.music_state['mode'],'audition')
        loaded=Store(self.store.directory); loaded.load()
        self.assertEqual(loaded.settings['music_volume'],a.settings['music_volume'])

    def test_loading_empty_catalog_is_safe_and_later_tracks_become_available(self):
        self.audio.catalog=[]; self.audio.music_state['buffering']=True
        self.open_soundtrack(); a=self.app
        a.handle('\n'); a.handle(' '); a.handle('n'); a.handle('p'); a.handle(curses.KEY_RIGHT)
        with patch('curses.doupdate'): a.draw()
        self.assertIsNone(a.game); self.assertIn('ui_error',self.audio.events)
        self.audio.catalog=soundtrack_catalog(); self.audio.music_state['buffering']=False
        a.handle('\n'); self.assertEqual(self.audio.music_state['track_id'],'cathedral-0')

    def test_global_master_and_music_keys_reach_every_screen(self):
        a=self.app
        for screen in ('hub','profiles','gallery','replays','soundtrack','showcase','help','confirm'):
            a.screen=screen
            for key,name in [('m','sound'),('b','music')]:
                before=a.settings[name]; a.handle(key); self.assertIs(a.settings[name],not before)
        a.win.size=(12,30); before=a.settings['sound']; a.handle('m')
        self.assertIs(a.settings['sound'],not before)

    def test_bus_volumes_load_old_version_validate_ranges_and_retain_master(self):
        for values,expected in [({},(.75,.85)),({'music_volume':.2,'sfx_volume':1},(.2,1)),
                                ({'music_volume':True,'sfx_volume':-1},(.75,.85)),
                                ({'music_volume':float('nan'),'sfx_volume':2},(.75,.85))]:
            self.store.path.write_text(json.dumps(dict(version=1,settings=dict(volume=.3,**values))),encoding='utf-8')
            loaded=Store(self.store.directory); loaded.load()
            self.assertEqual(loaded.settings['volume'],.3)
            self.assertEqual((loaded.settings.get('music_volume'),loaded.settings.get('sfx_volume')),expected)
            loaded.save(); self.assertEqual(json.loads(loaded.path.read_text())['version'],1)

    def test_settings_controls_reach_both_bus_volumes_and_keep_theme_in_sync(self):
        a=self.app; a.screen='settings'; a.setting_selection=0
        for _ in range(5): a.handle(curses.KEY_DOWN)
        before=a.settings['music_volume']; a.handle(curses.KEY_LEFT)
        self.assertLess(a.settings['music_volume'],before)
        a.handle(curses.KEY_DOWN); before=a.settings['sfx_volume']; a.handle(curses.KEY_LEFT)
        self.assertLess(a.settings['sfx_volume'],before)
        a.handle(curses.KEY_DOWN); a.handle('\n'); self.assertEqual(a.screen,'profiles')
        a.profile_selection=0; a.handle(curses.KEY_RIGHT)
        self.assertEqual(a.settings['theme'],self.audio.theme)
        loaded=Store(self.store.directory); loaded.load()
        self.assertEqual(loaded.settings['sfx_volume'],a.settings['sfx_volume'])

    def test_idle_ticks_do_not_flood_audio_command_queue_with_unchanged_theme(self):
        a=self.app; self.audio.calls.clear()
        for _ in range(40): a.tick(.02)
        self.assertEqual(self.audio.calls,[])
        a.settings['theme']='space'; a.tick(.02)
        self.assertEqual(self.audio.calls,[('theme','space')])

    def test_inactive_game_audio_gate_does_not_display_false_audition_pause(self):
        self.open_soundtrack(); a=self.app
        self.audio.music_state.update(mode='game',paused=True)
        with patch('curses.doupdate'): a.draw()
        frame='\n'.join(text for y,x,text in a.win.lines)
        self.assertIn('Stopped / Shuffle OFF / Repeat OFF',frame)


if __name__=='__main__': unittest.main()
