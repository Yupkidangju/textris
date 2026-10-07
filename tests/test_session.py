import unittest
from textris import session
from textris.engine import Game, Piece


class SessionTests(unittest.TestCase):
    def test_fixed_tick_commands_match_engine(self):
        s=session.Session(seed=42)
        g=Game(seed=42)
        for command in ('left','cw','drop','hold','right','drop'):
            s.command(command); s.step()
            {'left':lambda:g.move(-1,0),'right':lambda:g.move(1,0),
             'cw':lambda:g.rotate(1),'drop':g.hard_drop,'hold':g.hold}[command]()
            g.update(1/60)
        self.assertEqual(s.game.board,g.board)
        self.assertEqual(s.game.score,g.score)
        self.assertEqual(list(s.game.queue),list(g.queue))
        self.assertEqual(len(s.actions),6)

    def test_boss_damage_overflow_timeout_topout_priority(self):
        s=session.Session(seed=1,mode='boss')
        s.game.emit('clear',rows=[21]*4,count=4,spin=True,perfect=True,combo=0,b2b=False,points=0)
        s.step()
        self.assertEqual(s.boss_hp,[0,0,50])
        s.game.emit('clear',rows=[21]*4,count=4,spin=False,perfect=False,combo=0,b2b=False,points=0)
        s.step(); self.assertEqual(s.game.state,'won')
        s=session.Session(seed=1,mode='boss'); s.tick=10799; s.step()
        self.assertEqual(s.game.state,'over')
        s=session.Session(seed=1,mode='boss'); s.game.state='over'
        s.game.emit('clear',count=4,spin=True,perfect=True,combo=0,points=0)
        s.boss_hp=[0,0,1]; s.step(); self.assertEqual(s.game.state,'over')

    def test_replay_roundtrip_seek_and_verify(self):
        s=session.Session(seed=42)
        for i in range(350):
            if i%22==0: s.command('drop')
            if i%11==0: s.command('left')
            s.step(); s.game.events.clear()
        data=s.replay()
        from textris.replay import Player
        p=Player(data); p.seek(100); p.seek(20); p.seek(data['end_tick'])
        self.assertEqual(p.session.checksum(),s.checksum())
        self.assertTrue(p.verified)
        self.assertTrue(s.samples)
        self.assertIn("max_combo",s.counts)

    def test_capture_limit_preserves_play(self):
        s=session.Session(seed=1)
        s.max_actions=2
        for _ in range(3): s.command('left'); s.step()
        self.assertTrue(s.warning)
        self.assertLessEqual(len(s.actions),2)
        self.assertEqual(s.tick,3)

    def test_analytics_real_clear_and_replay_rates_preserve_source(self):
        from copy import deepcopy
        from textris.replay import Player
        s=session.Session(seed=42)
        for i in range(1000):
            if i%18==0: s.command('drop')
            s.step(); s.game.events.clear()
        data=s.replay(); original=deepcopy(data)
        for batch in (1,2,4):
            p=Player(data)
            while not p.finished:
                for _ in range(batch): p.step()
                p.session.game.events.clear()
            self.assertTrue(p.verified)
        self.assertEqual(data,original)
        s=session.Session(seed=1)
        s.game.board[21]=['J']*6+[None]*4
        s.game.active=Piece('I',0,6,20)
        s.command('drop'); s.step()
        self.assertEqual(len(s.highlights),1)
        self.assertEqual(s.highlights[0]['kind'],'perfect')
        self.assertEqual(s.counts['perfect'],1)

    def test_corrupt_replay_and_changed_checksum_are_detected(self):
        from textris.replay import Player
        s=session.Session(seed=3); s.command('drop'); s.step()
        data=s.replay(); data['checksum']='0'*64
        p=Player(data); p.seek(1)
        self.assertFalse(p.verified); self.assertEqual(p.warning,'replay_mismatch')
        data['actions']=[[2,'drop']]
        with self.assertRaises(ValueError): Player(data)

    def test_early_observation_cannot_change_boss_tick_outcome(self):
        a=session.Session(seed=42,mode='boss'); b=session.Session(seed=42,mode='boss')
        for s in (a,b):
            s.boss_hp=[0,0,1]
            s.game.board[21]=['J']*6+[None]*4
            s.game.active=Piece('I',0,6,20)
            s.command('drop')
        a.observe(); a.step(); b.step()
        self.assertEqual(a.game.state,'won')
        self.assertEqual(a.checksum(),b.checksum())

    def test_observation_without_ticks_does_not_add_samples(self):
        s=session.Session(seed=42)
        for _ in range(100): s.observe()
        self.assertFalse(s.samples)
        for _ in range(60): s.step()
        for _ in range(100): s.observe()
        self.assertEqual(len(s.samples),1)

    def test_early_observation_then_same_tick_topout_is_deterministic(self):
        a=session.Session(seed=42,mode='boss'); b=session.Session(seed=42,mode='boss')
        for s in (a,b):
            s.game.board[21]=['J']*6+[None]*4
            s.game.active=Piece('I',0,6,20); s.command('drop')
        a.observe()
        for s in (a,b):
            for _ in range(20): s.command('drop')
            s.step()
        self.assertEqual(a.game.state,'over')
        self.assertEqual(a.checksum(),b.checksum())
