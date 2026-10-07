import unittest
from textris.engine import Game, Piece, cells


class EngineTests(unittest.TestCase):
    def game(self, **kw):
        return Game(seed=42, **kw)

    def test_bag_and_seed(self):
        a, b = self.game(), self.game()
        kinds = []
        for _ in range(21):
            kinds.append(a.active.kind)
            self.assertEqual(a.active.kind, b.active.kind)
            a.board = [[None] * 10 for _ in range(22)]
            b.board = [[None] * 10 for _ in range(22)]
            a.hard_drop(); b.hard_drop()
        for i in range(0, 21, 7):
            self.assertEqual(set(kinds[i:i+7]), set('IOTSZJL'))
        self.assertGreaterEqual(len(a.queue), 5)

    def test_four_rotations_and_boundaries(self):
        g = self.game()
        for kind in 'IOTSZJL':
            g.active = Piece(kind, 0, 3, 5)
            before = set(cells(g.active))
            for _ in range(4):
                self.assertTrue(g.rotate(1))
            self.assertEqual(set(cells(g.active)), before)
        g.active = Piece('T', 1, -1, 5)
        self.assertTrue(g.rotate(-1))
        self.assertTrue(all(x >= 0 for x, y in cells(g.active)))
        while g.move(-1, 0):
            pass
        self.assertFalse(g.move(-1, 0))

    def test_floor_kicks_for_t_and_i_use_different_tables(self):
        g=self.game(); g.active=Piece('T',0,3,20)
        self.assertTrue(g.rotate(1))
        self.assertEqual(g.active,Piece('T',1,2,19))
        g.active=Piece('I',0,0,20)
        self.assertTrue(g.rotate(1))
        self.assertEqual(g.active,Piece('I',1,1,18))

    def test_hold_once_until_lock(self):
        g = self.game(); first = g.active.kind
        self.assertTrue(g.hold())
        self.assertEqual(g.held, first)
        self.assertFalse(g.hold())
        g.hard_drop()
        self.assertTrue(g.hold())
        self.assertEqual(g.active.kind, first)
        self.assertEqual(g.active.rotation, 0)

    def test_drop_and_ghost(self):
        g = self.game()
        y = g.ghost_y(); before = g.active.y
        self.assertTrue(g.move(0, 1, soft=True))
        self.assertEqual(g.score, 1)
        g.hard_drop()
        self.assertEqual(g.score, 1 + 2 * (y-before-1))
        self.assertEqual(sum(v is not None for row in g.board for v in row), 4)

    def prepare_clear(self, g, count):
        g.board = [[None] * 10 for _ in range(22)]
        # 다른 블록 하나로 all-clear 보너스를 제외한다.
        g.board[10][0] = 'T'
        for y in range(22-count, 22):
            g.board[y] = ['J'] * 10; g.board[y][4] = None
        g.active = Piece('I', 1, 2, 18)
        g.last_rotate = False

    def test_line_scores_and_level(self):
        for n, points in enumerate((100, 300, 500, 800), 1):
            g = self.game(); self.prepare_clear(g, n)
            g.lock()
            self.assertEqual(g.lines, n)
            self.assertEqual(g.score, points)
            self.assertTrue(any(e.name == 'clear' for e in g.events))
        g = self.game(); g.lines = 9; self.prepare_clear(g, 1); g.lock()
        self.assertEqual(g.level, 2)
        self.assertEqual(g.score, 100)

    def test_b2b_combo_and_all_clear(self):
        g = self.game()
        self.prepare_clear(g, 4); g.lock()
        self.prepare_clear(g, 4); g.lock()
        self.assertEqual(g.score, 800+1200+50)
        g = self.game(); self.prepare_clear(g, 4); g.board[10][0] = None; g.lock()
        self.assertEqual(g.score, 4300)

    def test_tspin_corner_rule(self):
        g = self.game(); g.active = Piece('T', 0, 3, 19)
        for x, y in [(3,19),(5,19),(3,21)]:
            g.board[y][x] = 'J'
        g.last_rotate = True
        g.lock()
        self.assertEqual(g.score, 400)

    def test_lock_delay_and_reset_cap(self):
        g = self.game(); g.active = Piece('O',0,3,20)
        g.update(.3)
        self.assertEqual(sum(v is not None for r in g.board for v in r), 0)
        g.move(1,0); self.assertEqual(g.lock_elapsed, 0)
        for i in range(16):
            g.move(-1 if i % 2 == 0 else 1,0)
        self.assertEqual(g.lock_resets, 15)
        g.update(.51)
        self.assertEqual(sum(v is not None for r in g.board for v in r), 4)

    def test_o_rotation_resets_grounded_lock_delay(self):
        g=self.game(); g.active=Piece('O',0,3,20)
        g.update(.49); self.assertTrue(g.rotate(1)); g.update(.02)
        self.assertEqual(sum(v is not None for r in g.board for v in r),0)
        self.assertEqual(g.lock_resets,1)

    def test_modes_pause_topout(self):
        g = self.game(mode='sprint'); g.lines = 39
        self.prepare_clear(g,1); g.lock(); self.assertEqual(g.state, 'won')
        g = self.game(mode='ultra'); g.update(120)
        self.assertEqual(g.state, 'won')
        g = self.game(); g.state = 'paused'; g.update(50)
        self.assertEqual(g.elapsed, 0)
        g.state = 'playing'; g.board[0][0] = 'I'; g.lock()
        self.assertEqual(g.state, 'over')

    def test_failed_moves_do_not_erase_rotation(self):
        g = self.game(); g.active = Piece('T',0,0,19)
        g.rotate(1)
        while g.move(-1,0):
            pass
        g.last_rotate = True
        self.assertFalse(g.move(-1,0))
        self.assertTrue(g.last_rotate)

    def test_input_validation(self):
        with self.assertRaises(ValueError): Game(mode='invalid')
        with self.assertRaises(ValueError): Game(start_level=0)
        with self.assertRaises(ValueError): self.game().update(-1)


if __name__ == '__main__':
    unittest.main()
