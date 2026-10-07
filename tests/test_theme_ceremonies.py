"""성취 의미/강도/삭제 행이 실제 렌더에 도달하는 회귀 검증."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from textris.art import RenderContext, game_layout
from textris.art_director import Cue
from textris.engine import Piece
from textris.scenes import THEMES
from textris.theme_art import ThemeScene


CEREMONIES = ('clear', 'bloom', 'ascension', 'victory', 'eclipse', 'awakening')
OTHER_THEMES = tuple(theme for theme in THEMES if theme != 'cathedral')


def geometry(canvas):
    # 색상만 바꾸는 구현은 섬광 OFF/모노 계약을 충족하지 못한다.
    return tuple(sorted((x, y, ink.glyph, ink.mask) for (x, y), ink in canvas.cells.items()))


def produce_ceremony(app, name):
    """이벤트 주입 없이 실제 키 명령/엔진 판정으로 여섯 성취를 만든다."""
    app.start('sprint' if name == 'victory' else 'marathon')
    app.screen = 'playing'
    app.game.state = 'playing'
    app.now = 100.
    g = app.game
    if name in ('bloom', 'ascension'):
        for y in range(18, 22):
            g.board[y] = ['J'] * 10
            g.board[y][5] = None
        if name == 'bloom':
            g.board[17][0] = 'J'
        g.active = Piece('I', 1, 3, 0)
    elif name == 'eclipse':
        g.board[0][0] = 'J'
    else:
        g.board[21] = ['J'] * 3 + [None] * 4 + ['J'] * 3
        g.board[19][0] = 'J'
        g.active = Piece('I', 0, 3, 0)
        if name == 'victory':
            g.lines = 39
        elif name == 'awakening':
            g.lines = 9
    app.handle(' ')
    app.process_events()
    return app.effects.director.major


class CeremonyTests(unittest.TestCase):
    def setUp(self):
        self.context = RenderContext(120, 40, game_layout(120, 40).protected)
        self.cue = Cue('clear', 100., 102., power=1.2, coords=(18, 19, 20, 21))

    def test_six_meanings_have_distinct_geometry_at_identical_time_and_phase(self):
        for theme in OTHER_THEMES:
            with self.subTest(theme=theme):
                scene = ThemeScene()
                pictures = [geometry(scene.render(self.context, 101., theme,
                    replace(self.cue, name=name), flash=False)) for name in CEREMONIES]
                self.assertEqual(len(set(pictures)), 6)

    def test_intensity_and_power_change_every_ceremony_geometry_without_flash(self):
        for theme in OTHER_THEMES:
            for name in CEREMONIES:
                with self.subTest(theme=theme, cue=name):
                    scene = ThemeScene()
                    cue = replace(self.cue, name=name, power=1.)
                    low = geometry(scene.render(self.context, 101., theme, cue, flash=False, intensity=.25))
                    high = geometry(scene.render(self.context, 101., theme, cue, flash=False, intensity=1.))
                    powerful = geometry(scene.render(self.context, 101., theme,
                        replace(cue, power=1.6), flash=False, intensity=1.))
                    self.assertNotEqual(low, high, 'fx_intensity ignored')
                    self.assertNotEqual(high, powerful, 'Cue.power ignored')

    def test_clear_rows_follow_board_origin_instead_of_screen_center(self):
        # 보드가 옮겨지면 같은 엔진 행의 파동도 정확히 같은 행 수만큼 이동한다.
        context = RenderContext(120, 50, ascii_mode=True)
        for theme in OTHER_THEMES:
            with self.subTest(theme=theme):
                scene = ThemeScene()
                base = scene.render(context, 101., theme).cells
                cue = replace(self.cue, coords=(8,))
                first = scene.render(context, 101., theme, cue, board=(49, 9), flash=False)
                second = scene.render(context, 101., theme, cue, board=(49, 13), flash=False)
                moved_row = scene.render(context, 101., theme, replace(cue, coords=(12,)),
                                         board=(49, 9), flash=False)
                delta = lambda c: {(x, y) for (x, y), ink in c.cells.items() if base.get((x, y)) != ink}
                self.assertTrue(delta(first))
                self.assertEqual({(x, y+4) for x, y in delta(first)}, delta(second))
                self.assertEqual(geometry(second), geometry(moved_row))

    def test_strong_clear_ceremonies_also_consume_their_producer_rows(self):
        for theme in OTHER_THEMES:
            for name in ('bloom', 'ascension'):
                with self.subTest(theme=theme, cue=name):
                    scene = ThemeScene()
                    cue = replace(self.cue, name=name)
                    normal = geometry(scene.render(self.context, 101., theme, cue, board=(49, 9)))
                    upper = geometry(scene.render(self.context, 101., theme,
                        replace(cue, coords=(8, 9, 10, 11)), board=(49, 9)))
                    shifted = geometry(scene.render(self.context, 101., theme, cue, board=(49, 5)))
                    self.assertNotEqual(normal, upper, 'cleared rows ignored')
                    self.assertNotEqual(normal, shifted, 'board origin ignored')

    def test_rowless_clear_preview_still_has_a_visible_ceremony(self):
        for theme in OTHER_THEMES:
            scene = ThemeScene()
            with self.subTest(theme=theme):
                self.assertNotEqual(geometry(scene.render(self.context, 101., theme)),
                    geometry(scene.render(self.context, 101., theme, replace(self.cue, coords=()))))

    def test_ceremonies_are_finite_and_leave_protected_cells_untouched(self):
        for theme in OTHER_THEMES:
            scene = ThemeScene()
            for time in (99., 102., 103.):
                self.assertEqual(scene.render(self.context, time, theme).cells,
                                 scene.render(self.context, time, theme, self.cue).cells, theme)
            for size in ((64, 28), (80, 30), (120, 40), (160, 50)):
                for ascii_mode, braille in ((True, True), (False, True), (False, False)):
                    layout = game_layout(*size)
                    ctx = RenderContext(*size, layout.protected, ascii_mode, braille)
                    for name in CEREMONIES:
                        c = scene.render(ctx, 101., theme, replace(self.cue, name=name), board=layout.board)
                        self.assertTrue(all(0 <= x < size[0]-1 and 0 <= y < size[1]
                                            and (x, y) not in c.blocked for x, y in c.cells))
                        if ascii_mode:
                            self.assertTrue(all(ink.glyph.isascii() for ink in c.cells.values()))


class CeremonyProducerTests(unittest.TestCase):
    def test_real_key_engine_events_render_six_ceremonies_and_preserve_replay_state(self):
        from tests.capture_cathedral import ColorWindow
        from tests.test_ui import AudioStub
        from textris.storage import Store
        from textris.ui import App
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(App, '_setup'), patch('curses.doupdate'):
                for theme in OTHER_THEMES:
                    frames = []
                    for name in CEREMONIES:
                        with self.subTest(theme=theme, cue=name):
                            store = Store(Path(temp) / theme / name)
                            store.settings.update(theme=theme, shake=False, flash=False, color=False)
                            app = App(ColorWindow(40, 120), store, AudioStub(), 42, unicode_art=True)
                            cue = produce_ceremony(app, name)
                            self.assertEqual(cue.name, name)
                            self.assertEqual(app.session.actions[0], [0, 'drop'])
                            if name in ('bloom', 'ascension'):
                                self.assertEqual(cue.coords, (18, 19, 20, 21))
                            state, replay = app.session.checksum(), app.session.replay()
                            # producer payload를 보존한 채 같은 절대 시간/위상에서 비교한다.
                            app.effects.director.major = replace(cue, start=100., end=102.)
                            app.now = 101.
                            app.draw()
                            first = [row.copy() for row in app.win.grid]
                            frames.append(geometry(app.effects._art_cache))
                            app.draw()
                            self.assertEqual(first, app.win.grid)
                            self.assertEqual(state, app.session.checksum())
                            self.assertEqual(replay, app.session.replay())
                            app.now = 102.
                            app.draw()
                            self.assertIsNone(app.effects.director.major)
                    self.assertEqual(len(set(frames)), 6, theme)


if __name__ == '__main__':
    unittest.main()
