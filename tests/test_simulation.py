"""실제 입력 경로로 여러 시드의 장기 플레이를 진행하는 규칙 불변조건 검사."""
import random
import unittest
from textris.engine import Game, cells


class SimulationTests(unittest.TestCase):
    def test_many_games_preserve_board_and_piece_invariants(self):
        rng=random.Random(20261007)
        placements=0
        for seed in range(120):
            g=Game(seed=seed,mode=('marathon','sprint','ultra')[seed%3])
            for _ in range(200):
                if g.state!='playing': break
                if rng.random()<.2: g.hold()
                for _ in range(rng.randrange(4)): g.rotate(1)
                for _ in range(rng.randrange(5)):
                    g.move(rng.choice((-1,1)),0)
                self.assertTrue(g.fits(g.active))
                self.assertGreaterEqual(g.ghost_y(),g.active.y)
                for x,y in cells(g.active):
                    self.assertTrue(0<=x<10 and 0<=y<22)
                g.update(rng.random()*.08)
                if g.state=='playing': g.hard_drop(); placements+=1
                self.assertEqual(len(g.board),22)
                self.assertTrue(all(len(row)==10 for row in g.board))
                self.assertTrue(all(v is None or v in 'IOTSZJL' for row in g.board for v in row))
                self.assertGreaterEqual(g.score,0)
                self.assertEqual(g.level,g.start_level+g.lines//10)
                g.events.clear()
            self.assertIn(g.state,('playing','won','over'))
        self.assertGreater(placements,1500)


if __name__=='__main__': unittest.main()
