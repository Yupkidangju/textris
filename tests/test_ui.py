from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from textris.engine import Game, Piece
from textris.storage import Store
from textris.ui import App, width, clip


class Window:
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
    def __init__(self): self.events=[]; self.music=False; import queue; self.bells=queue.Queue()
    def play(self,name): self.events.append(name)
    def set_music(self,enabled): self.music=enabled


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

    def test_drop_clear_particles_banner_and_animation_expiry(self):
        a=self.app; a.settings['theme']='cyberpunk'; a.start('marathon'); a.screen='playing'; a.game.state='playing'; a.now=100.
        a.game.emit('drop',cells=((4,2),(4,3),(4,4),(4,5)),distance=12)
        a.game.emit('clear',rows=[21],count=1,spin=False,combo=2,b2b=False,perfect=False,points=200)
        a.process_events()
        self.assertEqual(len(a.trails),1)
        self.assertEqual(len(a.particles),6)
        self.assertEqual(a.flash_until,100.24)
        self.assertIn('COMBO ×2',a.banner)
        with patch('curses.doupdate'):
            a.draw(); before=a.win.lines[:]
            a.now=100.6; a.process_events(); a.draw()
        self.assertEqual(a.trails,[])
        self.assertEqual(a.particles,[])
        self.assertNotEqual(before,a.win.lines)
        self.assertIn('clear',a.audio.events)

    def test_title_animation_preserves_all_six_logo_rows(self):
        from textris.ui import LOGO
        a=self.app; a.settings['theme']='cyberpunk'; a.now=.1
        a.draw_menu()
        rows=[y for y,x,text in a.win.lines if text in LOGO]
        self.assertEqual(len(rows),6)
        self.assertEqual(len(set(rows)),6)

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
