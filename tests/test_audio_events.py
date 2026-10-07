"""효과음 관측은 실제 App -> Session -> Game 입력으로 만든 사건만 사용한다."""
import curses
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from textris.engine import Piece
from textris.replay import Player
from textris.session import STEP
from textris.storage import Store
from textris.ui import App
from tests.test_ui import AudioStub, Window


class AudioEventTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)); self.store.load()
        with patch.object(App,'_setup'):
            self.app=App(Window(),self.store,AudioStub(),seed=42)

    def playing(self,mode='marathon'):
        a=self.app; a.start(mode); a.tick(3)
        a.audio.events.clear(); return a

    def clear_board(self,count,perfect=False):
        g=self.app.game; g.board=[[None]*10 for _ in range(22)]
        if not perfect: g.board[10][0]='T'
        for row in range(22-count,22):
            g.board[row]=['J']*10; g.board[row][4]=None
        g.active=Piece('I',1,2,18); g.last_rotate=False

    def test_countdown_go_pause_resume_and_ui_feedback_follow_actual_transitions(self):
        a=self.app; a.handle(curses.KEY_DOWN); a.handle(curses.KEY_UP)
        self.assertIn('ui_move',a.audio.events)
        a.handle('\n'); self.assertIn('ui_select',a.audio.events)
        self.assertEqual(a.audio.events.count('countdown'),1)
        a.tick(1); a.tick(1); a.tick(1)
        self.assertEqual(a.audio.events.count('countdown'),3); self.assertIn('go',a.audio.events)
        a.handle('p'); self.assertIn('pause',a.audio.events)
        a.handle('p'); self.assertIn('resume',a.audio.events)
        a.handle('h'); a.handle('\x1b'); self.assertIn('ui_back',a.audio.events)
        a.handle('b'); self.assertIn('ui_toggle',a.audio.events)
        self.store.read_only=True; a.audio.events.clear(); a.handle('b')
        self.assertEqual(a.audio.events,['ui_error'])

    def test_successful_actions_only_and_drop_lock_have_individual_cues(self):
        a=self.playing(); a.game.active=Piece('T')
        for key,cue in [('a','move'),('x','rotate'),('c','hold'),(' ','drop')]:
            a.audio.events.clear(); a.handle(key); a.process_events(); self.assertIn(cue,a.audio.events)
        self.assertIn('lock',a.audio.events)
        a.game.active=Piece('I',1,-2,10); a.game.events.clear(); a.audio.events.clear()
        a.handle('a'); a.process_events(); self.assertNotIn('move',a.audio.events)
        a.handle('c'); a.process_events(); a.audio.events.clear()
        a.handle('c'); a.process_events(); self.assertNotIn('hold',a.audio.events)

    def test_line_clear_variants_take_priority_over_drop_and_lock(self):
        for count,cue in [(1,'clear_single'),(2,'clear_double'),(3,'clear_triple'),(4,'tetris')]:
            with self.subTest(count=count):
                a=self.playing(); self.clear_board(count); a.handle(' '); a.process_events()
                self.assertIn(cue,a.audio.events)
                self.assertNotIn('drop',a.audio.events); self.assertNotIn('lock',a.audio.events)
                self.assertNotIn('b2b',a.audio.events)
        a=self.playing(); self.clear_board(4,perfect=True); a.handle(' '); a.process_events()
        self.assertIn('all_clear',a.audio.events); self.assertNotIn('tetris',a.audio.events)

    def test_tspin_combo_and_real_b2b_chain(self):
        a=self.playing(); g=a.game
        g.active=Piece('T',1,3,19)
        for x,y in [(3,19),(5,19),(3,21)]: g.board[y][x]='J'
        a.handle('z'); a.handle(' '); a.process_events()
        self.assertIn('tspin',a.audio.events)
        a=self.playing(); self.clear_board(4); a.handle(' '); a.process_events()
        a.audio.events.clear(); self.clear_board(4); a.handle(' '); a.process_events()
        self.assertIn('combo',a.audio.events); self.assertIn('b2b',a.audio.events)
        self.clear_board(1); a.handle(' '); a.process_events()
        a.audio.events.clear(); self.clear_board(4); a.handle(' '); a.process_events()
        self.assertNotIn('b2b',a.audio.events)

    def test_danger_fever_level_and_terminal_cues_are_transition_only(self):
        a=self.playing(); a.game.active=Piece('O',0,3,2)
        a.game.board[4][4]='J'; a.handle(' '); a.process_events()
        self.assertIn('danger',a.audio.events); a.audio.events.clear(); a.process_events()
        self.assertNotIn('danger',a.audio.events)
        a=self.playing(); a.now=100.
        for _ in range(2): self.clear_board(4); a.handle(' '); a.process_events()
        self.assertEqual(a.audio.events.count('fever_start'),1)
        a.now+=9; a.process_events(); self.assertEqual(a.audio.events.count('fever_end'),1)
        a.process_events(); self.assertEqual(a.audio.events.count('fever_end'),1)
        a.game.lines=9; self.clear_board(1); a.handle(' '); a.process_events()
        self.assertIn('level',a.audio.events)
        a=self.playing('sprint'); a.game.lines=39; self.clear_board(1); a.handle(' '); a.process_events()
        self.assertIn('win',a.audio.events); self.assertEqual(a.screen,'result')
        a=self.playing(); a.game.board[0][0]='I'; a.handle(' '); a.process_events()
        self.assertIn('gameover',a.audio.events); self.assertNotIn('drop',a.audio.events)

    def test_boss_damage_and_break_come_from_finalized_real_clear(self):
        a=self.playing('boss'); self.clear_board(1); a.handle(' '); a.tick(.02)
        self.assertIn('boss_hit',a.audio.events); self.assertNotIn('boss_break',a.audio.events)
        a.audio.events.clear(); self.clear_board(4); a.handle(' '); a.tick(.02)
        self.assertIn('boss_break',a.audio.events); self.assertIn('boss_hit',a.audio.events)

    def test_audio_routing_does_not_change_session_checksum(self):
        a=self.playing(); self.clear_board(4); a.handle(' ')
        before=a.session.checksum(); a.process_events()
        self.assertEqual(a.session.checksum(),before)

    def test_previous_exhibition_pause_does_not_mask_new_game_pause_feedback(self):
        a=self.playing(); a.replay_paused=True; a.auto_paused=True
        a.handle('p'); self.assertIn('pause',a.audio.events)
        a.audio.events.clear(); a.handle('p'); self.assertIn('resume',a.audio.events)

    def test_exhibitions_do_not_play_a_countdown_that_is_never_shown(self):
        a=self.app; a.handle('v')
        self.assertEqual(a.screen,'showcase'); self.assertNotIn('countdown',a.audio.events)
        a.handle('\x1b'); a.audio.events.clear(); a.handle('e')
        for _ in range(4): a.handle(curses.KEY_DOWN)
        a.handle('\n')
        self.assertEqual(a.screen,'autoplay'); self.assertNotIn('countdown',a.audio.events)

    def open_chain_replay(self):
        a=self.app; a.start(); a.screen='playing'; a.game.state='playing'
        g=a.game; g.board=[[None]*10 for _ in range(22)]
        g.board[6][0]='T'
        for row in range(14,22):
            g.board[row]=['J']*10; g.board[row][4]=None
        g.active=Piece('I',1,2,0); g.queue[0]='I'
        initial=deepcopy(a.session)
        a.handle(' '); a.tick(STEP)
        for _ in range(359): a.tick(STEP)
        for key in ('a','x',' '): a.handle(key)
        a.tick(STEP)
        self.assertEqual(a.session.counts['tetris'],2)
        data=a.session.replay()

        # 준비 보드는 체크포인트 픽스처로만 주입하고 명령 재생/seek/검증은 실제 Player를 쓴다.
        class PreparedPlayer(Player):
            def __init__(self,data):
                super().__init__(data)
                self.checkpoints[0]=(deepcopy(initial),0)
                self.seek(0)
        fixture=patch('textris.expansion_ui.Player',PreparedPlayer)
        fixture.start(); self.addCleanup(fixture.stop)
        a.open_replay(data); a.director=False
        return a

    def test_replay_rewind_discards_old_chain_fever_and_danger_without_seek_cues(self):
        a=self.open_chain_replay()
        for _ in range(361): a.tick(STEP)
        self.assertTrue(a.player.verified)
        self.assertTrue(a.audio_events.difficult); self.assertTrue(a.audio_events.fever)
        self.assertFalse(a.audio_events.danger)
        a.audio.events.clear()
        a.handle(curses.KEY_LEFT); a.handle(curses.KEY_LEFT)
        self.assertEqual(a.session.tick,0); self.assertFalse(a.game.b2b)
        self.assertFalse(a.audio_events.difficult)
        self.assertTrue(a.audio_events.danger); self.assertFalse(a.audio_events.fever)
        a.tick(0); self.assertEqual(a.audio.events,[])
        a.tick(STEP)
        self.assertIn('tetris',a.audio.events); self.assertNotIn('b2b',a.audio.events)

    def test_replay_forward_seek_preserves_existing_chain_without_new_danger_cue(self):
        a=self.open_chain_replay(); a.audio.events.clear()
        a.handle(curses.KEY_RIGHT)
        self.assertEqual(a.session.tick,300); self.assertTrue(a.game.b2b)
        self.assertTrue(a.audio_events.difficult)
        self.assertFalse(a.audio_events.danger); self.assertFalse(a.audio_events.fever)
        a.tick(0); self.assertEqual(a.audio.events,[])
        for _ in range(61): a.tick(STEP)
        self.assertIn('tetris',a.audio.events); self.assertIn('b2b',a.audio.events)
        self.assertTrue(a.player.verified)

    def test_analysis_highlight_seek_restores_chain_from_the_target_checkpoint(self):
        a=self.open_chain_replay()
        for _ in range(361): a.tick(STEP)
        a.handle('a'); a.highlight_selection=1; a.audio.events.clear()
        a.handle('\n')
        self.assertEqual(a.screen,'replay'); self.assertEqual(a.session.tick,300)
        self.assertTrue(a.game.b2b); self.assertTrue(a.audio_events.difficult)
        self.assertFalse(a.audio_events.danger); self.assertFalse(a.audio_events.fever)
        self.assertEqual(a.audio.events,['ui_select'])
        a.audio.events.clear()
        for _ in range(61): a.tick(STEP)
        self.assertIn('tetris',a.audio.events); self.assertIn('b2b',a.audio.events)
        self.assertNotIn('fever_end',a.audio.events); self.assertNotIn('danger',a.audio.events)
        self.assertTrue(a.player.verified)


if __name__=='__main__': unittest.main()
