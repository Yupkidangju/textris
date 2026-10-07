"""연출 수명/부하 제한과 게임 상태 독립성을 검증한다."""
import unittest
from unittest.mock import patch
from tests import test_ui


class EffectsTests(unittest.TestCase):
    def setUp(self):
        test_ui.UITests.setUp(self)
        self.app.settings['theme']='cyberpunk'
    def test_impact_moves_board_then_settles_and_debris_expires(self):
        a=self.app; a.start(); a.now=100
        a.game.emit('drop',cells=((4,2),(4,3),(4,4),(4,5)),distance=14)
        a.process_events()
        self.assertTrue(any(a.effects.offset(100+t) != (0,0) for t in (.02,.05,.1)))
        self.assertTrue(a.effects.debris)
        self.assertTrue(a.effects.rings)
        self.assertEqual(a.effects.offset(102),(0,0))
        a.effects.update(103)
        self.assertFalse(a.effects.debris)
        self.assertFalse(a.effects.rings)

    def test_clear_storm_is_bounded_and_does_not_change_engine(self):
        a=self.app; a.start(); a.now=100
        before=[row[:] for row in a.game.board]
        data=dict(rows=[18,19,20,21],count=4,spin=False,combo=5,b2b=True,perfect=True,points=6000)
        for _ in range(50):
            a.game.emit('clear',**data)
        a.process_events()
        self.assertGreater(len(a.effects.debris),40)
        self.assertLessEqual(len(a.effects.debris),600)
        self.assertLessEqual(len(a.effects.rings),12)
        self.assertLessEqual(len(a.effects.labels),8)
        self.assertEqual(a.game.board,before)
        self.assertEqual(a.game.score,0)
        a.start(); self.assertFalse(a.effects.debris)

    def test_showcase_cycles_without_time_records_and_returns(self):
        a=self.app; a.handle('v')
        self.assertEqual(a.screen,'showcase')
        a.tick(.1)
        first=a.banner
        a.now+=1.7; a.tick(1.7)
        self.assertNotEqual(a.banner,first)
        self.assertTrue(a.effects.debris)
        self.assertEqual(a.game.elapsed,0)
        self.assertFalse(any(self.store.records.values()))
        with patch('curses.doupdate'):
            a.draw()
        a.handle(' '); self.assertEqual(a.game.score,0)
        a.handle('\x1b'); self.assertEqual(a.screen,'menu')

    def test_real_drop_lock_sequence_retains_drop_impact(self):
        a=self.app; a.start(); a.screen='playing'; a.game.state='playing'; a.now=100
        a.game.hard_drop(); a.process_events()
        self.assertGreaterEqual(a.effects.strength,1.5)

    def test_victory_art_has_visible_final_letter(self):
        from textris.effects import art
        rows=art('VICTORY',True)
        self.assertTrue(any('#' in row[-3:] for row in rows))

    def test_every_event_and_zero_line_spin_render_in_both_languages(self):
        a=self.app; a.start(); a.screen='playing'; a.now=100
        with patch('curses.doupdate'):
            for lang in ('ko','en'):
                a.settings['language']=lang
                for ascii_mode in (False,True):
                    a.settings['ascii']=ascii_mode
                    for name,data in (
                        ('lock',dict(cells=((4,20),(4,21),(5,20),(5,21)))),
                        ('rotate',{}),('hold',{}),('level',dict(level=2)),
                        ('clear',dict(rows=[],count=0,spin=True,combo=-1,b2b=False,perfect=False,points=400)),
                        ('gameover',{}),('win',{})):
                        a.effects.trigger(name,data,a.now)
                        for age in (.01,.2,.7,1.2):
                            a.effects.update(a.now+age)
                            a.effects.draw(a,22,4,a.now+age)
            self.assertTrue(a.win.lines)

    def test_background_changes_and_ascii_effects_clip_at_all_sizes(self):
        a=self.app; a.start(); a.screen='playing'; a.now=100
        a.game.emit('clear',rows=[21],count=1,spin=False,combo=0,b2b=False,perfect=False,points=100)
        a.process_events()
        with patch('curses.doupdate'):
            for size in ((28,64),(40,120)):
                a.win.size=size
                for ascii_mode in (False,True):
                    a.settings['ascii']=ascii_mode
                    for age in (0,.1,.3,.8):
                        a.now=100+age; a.draw()
                        self.assertTrue(a.win.lines)
            backgrounds=[]
            for now in (0,10,20,30):
                a.win.erase(); a.effects.background(a,now)
                self.assertTrue(a.win.lines)
                backgrounds.append(a.win.lines[:])
            self.assertEqual(len({str(frame) for frame in backgrounds}),4)
        a.handle('f'); self.assertFalse(a.fx_enabled)
        a.start(); self.assertFalse(a.fx_enabled)


if __name__=='__main__': unittest.main()
