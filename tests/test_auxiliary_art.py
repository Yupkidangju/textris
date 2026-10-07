"""보스/분석의 서브셀 아트가 게임 정보와 출력 경계를 지키는지 검증한다."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from textris.art import ArtCanvas, game_layout
from textris.storage import Store
from textris.ui import App
from tests.test_ui import AudioStub, Window


class AuxiliaryArtTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        store = Store(Path(temporary.name))
        store.load()
        with patch.object(App, '_setup'):
            self.app = App(Window(40, 120), store, AudioStub(), seed=3, unicode_art=True)
        self.app.start('boss')
        self.app.settings['braille'] = True

    def render(self, function):
        frames = []
        original = ArtCanvas.paint
        def paint(canvas, app):
            frames.append(canvas)
            original(canvas, app)
        with patch.object(ArtCanvas, 'paint', paint):
            function()
        return frames

    def test_boss_art_stays_outside_board_and_hud_and_reflects_damage(self):
        a = self.app
        a.settings['ascii'] = False
        layout = game_layout(120, 40)
        frames = self.render(lambda: a.draw_boss(layout.origin[1]))
        self.assertTrue(frames, 'boss must render its mechanical silhouette through ArtCanvas')
        cells = frames[0].cells
        self.assertGreater(len(cells), 35)
        for x, y in cells:
            self.assertTrue(1 <= x < layout.origin[0] - 1)
            self.assertTrue(layout.origin[1]+5 <= y <= layout.origin[1]+11)
            for px, py, width, height in layout.protected:
                self.assertFalse(px <= x < px+width and py <= y < py+height)
        a.session.boss_hp = [0, 0, 0]
        broken = self.render(lambda: a.draw_boss(layout.origin[1]))[0].cells
        self.assertNotEqual(cells, broken)

    def test_boss_at_minimum_size_keeps_hp_without_drawing_over_hud(self):
        a = self.app
        a.win = Window(28, 64)
        self.assertEqual(self.render(lambda: a.draw_boss(0)), [])
        self.assertTrue(any('60/60/60' in text for _, _, text in a.win.lines))

    def test_analysis_chart_respects_information_rows_and_ascii_mode(self):
        a = self.app
        a.screen = 'analysis'
        a.session.samples = [[0, 0, 0], [60, 80, 1], [180, 240, 3]]
        for ascii_mode in (False, True):
            a.settings['ascii'] = ascii_mode
            a.win = Window(28, 64)
            frames = self.render(a.draw_expansion)
            self.assertTrue(frames, 'analysis must draw a subcell chart')
            cells = frames[0].cells
            self.assertTrue(all(5 <= y <= 13 for x, y in cells))
            self.assertGreater(len(cells), 50)
            if ascii_mode:
                self.assertTrue(all(ink.glyph.isascii() for ink in cells.values()))
            else:
                self.assertTrue(any(0x2800 <= ord(ink.glyph) <= 0x28ff for ink in cells.values()))
            self.assertTrue(any(y == 15 for y, _, _ in a.win.lines))
            self.assertTrue(any(y == 17 for y, _, _ in a.win.lines))


if __name__ == '__main__':
    unittest.main()
