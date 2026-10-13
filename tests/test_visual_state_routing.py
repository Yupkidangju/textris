"""게임을 변경하지 않는 테마 표시 상태와 캐시 갱신."""
from unittest.mock import patch
import unittest
from tests import test_ui
from dataclasses import replace


class VisualStateRoutingTests(unittest.TestCase):
    setUp=test_ui.UITests.setUp

    def test_status_reaches_theme_scene_and_resets_with_game_state(self):
        a=self.app; a.start(); a.screen='playing'; a.game.state='playing'; a.now=100
        a.game.board[2][0]='I'; a.game.combo=5; a.game.b2b=2; a.game.level=4
        a.effects.fever_until=105
        before=a.session.checksum()
        a.process_events()
        with patch.object(a.effects.stage,'render',return_value=None) as render:
            with patch('curses.doupdate'):
                # 실제 배경 경로의 반환 캔버스만 대체해 전달 계약을 관찰한다.
                from textris.art import ArtCanvas
                render.return_value=ArtCanvas(a.art_context())
                a.draw()
            state=render.call_args.kwargs.get('state')
        self.assertIsNotNone(state)
        self.assertTrue(state.danger and state.fever and state.b2b)
        self.assertEqual((state.combo,state.level),(5,4))
        self.assertEqual(a.session.checksum(),before)
        a.game.board[2][0]=None; a.game.combo=-1; a.game.b2b=0
        a.process_events()
        self.assertFalse(a.effects.danger); self.assertEqual(a.effects.combo,0)

    def test_large_statistics_use_readable_short_numbers_inside_hud(self):
        a=self.app; a.start(); a.screen='playing'; a.game.state='playing'
        a.game.score=10**12
        with patch('curses.doupdate'): a.draw()
        frame='\n'.join(text for y,x,text in a.win.lines)
        self.assertIn('1e+12',frame)

    def test_successful_move_has_short_cue_but_failed_move_has_none(self):
        a=self.app; a.start(); a.screen='playing'; a.game.state='playing'; a.now=100
        a.handle('a'); a.process_events()
        cue=a.effects.director.local[-1]
        self.assertEqual(cue.name,'move'); self.assertAlmostEqual(cue.end-cue.start,.12)
        while a.game.move(-1,0): pass
        a.game.events.clear(); a.effects.director.local.clear()
        a.handle('a'); a.process_events()
        self.assertFalse(a.effects.director.local)

    def test_frame_budget_degrades_and_recovers_bounded_quality(self):
        effects=self.app.effects
        for _ in range(200): effects.observe_frame_cost(.04)
        self.assertEqual(effects.quality,.4)
        for _ in range(200): effects.observe_frame_cost(.001)
        self.assertEqual(effects.quality,1.)

    def test_board_drawing_uses_the_layout_contract(self):
        from textris.art import game_layout
        from textris.engine import Piece,cells,HIDDEN
        a=self.app; a.start(); a.screen='playing'; a.game.state='playing'
        a.terminal_ascii=True; a.settings['shake']=False
        a.game.active=Piece('O',0,3,4)
        layout=replace(game_layout(64,28),board=(20,3))
        with patch('textris.ui.game_layout',return_value=layout),patch('curses.doupdate'):
            a.draw()
        grid={(x+dx,y):ch for y,x,text in a.win.lines for dx,ch in enumerate(text)}
        for x,y in cells(a.game.active):
            self.assertEqual(grid[(21+2*x,4+y-HIDDEN)],'[')


if __name__=='__main__': unittest.main()
