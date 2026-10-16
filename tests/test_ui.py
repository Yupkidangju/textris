from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from textris.engine import Game, Piece
from textris.storage import Store
from textris.ui import App, width, clip


class Window:
    encoding = 'utf-8'
    def __init__(self, height=28, columns=64):
        self.size = (height,columns)
        self.lines = []
    def getmaxyx(self): return self.size
    def erase(self): self.lines = []
    def addstr(self,y,x,text,attr):
        assert 0 <= y < self.size[0]
        assert x+width(text) < self.size[1]
        self.lines.append((y,x,text))
    def noutrefresh(self): pass


class AudioStub:
    status = 'audio_bell'
    def __init__(self):
        self.events=[]; self.music=False; self.suspended=False; self.theme=None
        self.catalog=[]; self.calls=[]
        self.music_state=dict(track_id=None,title='',theme='',position=0.,duration=0.,bpm=0.,
                              instruments=[],paused=False,buffering=False,mode='game',
                              shuffle=False,repeat=False,error='')
        import queue
        self.bells=queue.Queue()
    def play(self,name): self.events.append(name)
    def set_music(self,enabled): self.music=enabled
    def set_suspended(self,enabled): self.suspended=enabled
    def set_theme(self,theme): self.theme=theme; self.calls.append(('theme',theme))
    def audition(self,track_id,*,playlist=None,shuffle=False,repeat=False):
        self.calls.append(('audition',track_id,playlist,shuffle,repeat))
        track=next(track for track in self.catalog if track['id']==track_id)
        self.music_state.update(track_id=track_id,mode='audition',position=0.,paused=False,
                                shuffle=shuffle,repeat=repeat,
                                **{key:track[key] for key in ('title','theme','duration','bpm','instruments')})
    def pause_audition(self,paused):
        self.calls.append(('pause',paused)); self.music_state['paused']=paused
    def set_audition_options(self,shuffle=None,repeat=None):
        if shuffle is not None: self.music_state['shuffle']=shuffle
        if repeat is not None: self.music_state['repeat']=repeat
    def seek_music(self,seconds):
        self.calls.append(('seek',seconds))
        self.music_state['position']=max(0.,min(self.music_state['duration'],self.music_state['position']+seconds))
    def next_track(self,direction=1): self.calls.append(('next',direction))
    def stop_audition(self):
        self.calls.append(('stop',)); self.music_state['mode']='game'


class UITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name)); self.store.load()
        self.store.settings['language']='en'
        with patch.object(App,'_setup'):
            self.app=App(Window(),self.store,AudioStub(),seed=42)

    def test_terminal_game_state_is_preserved_after_keyboard_topout(self):
        a=self.app; a.start('marathon'); a.screen='playing'; a.game.state='playing'
        a.game.board[0][0]='I'
        a.handle(' ')
        self.assertEqual(a.game.state,'over')
        a.tick(.01)
        self.assertEqual(a.screen,'result')
        self.assertEqual(a.game.state,'over')
        self.assertEqual(len(self.store.records['marathon']),1)
        a.tick(.5)
        self.assertEqual(len(self.store.records['marathon']),1)

    def test_help_pause_resize_freeze_and_resume(self):
        a=self.app; a.start('ultra'); a.screen='playing'; a.game.state='playing'
        a.tick(.1); before=a.game.elapsed
        a.handle('h'); a.tick(20)
        self.assertEqual(a.game.elapsed,before)
        self.assertFalse(a.audio.music)
        a.handle('\x1b'); a.tick(.1)
        self.assertGreater(a.game.elapsed,before)
        a.win.size=(12,30); before=a.game.elapsed; a.tick(20)
        self.assertEqual(a.game.elapsed,before)
        a.win.size=(28,64); a.tick(.1)
        self.assertTrue(a.audio.music)

    def test_modes_restart_confirmation_and_ready(self):
        a=self.app; a.start('sprint'); a.tick(3)
        self.assertEqual(a.screen,'playing')
        a.handle('r'); a.handle('n')
        self.assertEqual(a.screen,'playing')
        a.handle('r'); a.handle('y')
        self.assertEqual(a.screen,'ready')
        self.assertEqual(a.game.mode,'sprint')
        self.assertEqual(a.game.score,0)
        a.win.size=(10,30); a.tick(20)
        self.assertEqual(a.ready_elapsed,0)

    def test_all_screens_both_languages_minimum_size(self):
        a=self.app; a.start('marathon')
        with patch('curses.doupdate'):
            for lang in ('ko','en'):
                a.settings['language']=lang
                for screen in ('menu','settings','records','ready','playing','paused','help','confirm','result'):
                    a.screen=screen; a.help_return='playing'; a.confirm_return='playing'
                    a.result_since=a.now-1
                    a.draw()
                    self.assertTrue(a.win.lines)
            a.win.size=(5,12); a.draw()
            self.assertTrue(a.win.lines)
        self.assertEqual(width('한A'),3)
        self.assertEqual(clip('한AB',3),'한A')

    def test_keyboard_clear_reaches_director_renderer_banner_and_expires(self):
        a=self.app; a.settings.update(theme='cyberpunk',shake=False,flash=False)
        a.start('marathon'); a.screen='playing'; a.game.state='playing'; a.now=100.
        a.game.board[21]=['J']*3+[None]*4+['J']*3
        a.game.board[19][0]='J'
        a.game.active=Piece('I',0,3,0); a.game.combo=1
        a.handle(' ')
        self.assertIn('clear',[event.name for event in a.game.events])
        a.process_events()
        cue=a.effects.director.major
        self.assertEqual((cue.name,cue.coords,cue.label),('clear',(21,),'SINGLE'))
        self.assertEqual(a.effects.director.local,[])
        self.assertIn('COMBO x2',a.banner)
        self.assertEqual(a.banner_until,101.6)
        checksum,replay=a.session.checksum(),a.session.replay()
        a.now=100.2
        with patch('curses.doupdate'):
            a.draw(); active=a.effects._art_cache.cells.copy()
            self.assertTrue(any(a.banner in text for y,x,text in a.win.lines))
            a.effects.director.major=None
            a.effects.background(a,a.now)
            self.assertNotEqual(active,a.effects._art_cache.cells)
            a.effects.director.major=cue
            a.now=100.56; a.process_events(); a.draw()
            self.assertIsNone(a.effects.director.major)
            a.now=101.61; a.win.erase(); a.draw()
            self.assertFalse(any(a.banner in text for y,x,text in a.win.lines))
        self.assertEqual(checksum,a.session.checksum())
        self.assertEqual(replay,a.session.replay())
        self.assertIn('clear_single',a.audio.events)

    def test_keyboard_drop_landing_cue_shake_and_finite_render_lifecycle(self):
        a=self.app; a.settings.update(theme='cyberpunk',flash=False)
        a.start('marathon'); a.screen='playing'; a.game.state='playing'; a.now=100.
        a.game.active=Piece('I',0,3,0)
        a.handle(' '); a.process_events()
        self.assertEqual([cue.name for cue in a.effects.director.local],['drop'])
        cue=a.effects.director.local[0]
        self.assertEqual(cue.coords,((6,19),(8,19),(10,19),(12,19)))
        self.assertEqual(a.effects.offset(100.02),(1,0))
        a.settings['shake']=False
        self.assertEqual(a.effects.offset(100.02),(0,0))
        a.now=100.1
        a.effects.background(a,a.now); active=a.effects._art_cache.cells.copy()
        a.effects.director.local=[]
        a.effects.background(a,a.now)
        self.assertNotEqual(active,a.effects._art_cache.cells)
        a.effects.director.local=[cue]
        a.now=100.36; a.process_events()
        self.assertEqual(a.effects.director.local,[])
        self.assertEqual(a.effects.offset(a.now),(0,0))

    def test_title_animation_preserves_all_six_logo_rows(self):
        from textris.ui import LOGO
        a=self.app; a.settings['theme']='cyberpunk'; a.now=a.art_epoch+2
        a.draw_menu()
        for y,row in enumerate(LOGO):
            actual={x:text for py,x,text in a.win.lines if py==3+y and len(text)==1}
            left=(a.win.size[1]-len(row))//2
            self.assertEqual(''.join(actual.get(left+x,' ') for x in range(len(row))),row)

    def test_controls_change_piece_and_preferences(self):
        a=self.app; a.start('marathon'); a.screen='playing'; a.game.state='playing'
        a.game.active=Piece('T'); x=a.game.active.x; a.handle('a'); self.assertEqual(a.game.active.x,x-1)
        a.handle('d'); self.assertEqual(a.game.active.x,x)
        a.handle('x'); self.assertEqual(a.game.active.rotation,1)
        a.handle('z'); self.assertEqual(a.game.active.rotation,0)
        a.handle('c'); self.assertIsNotNone(a.game.held)
        a.handle('m'); self.assertFalse(a.settings['sound'])
        a.handle('b'); self.assertFalse(a.settings['music'])
        a.handle('q'); a.handle('n'); self.assertTrue(a.running)
        a.handle('q'); a.handle('y'); self.assertFalse(a.running)


if __name__=='__main__': unittest.main()
