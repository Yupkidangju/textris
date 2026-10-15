"""심해와 설원 장면의 형상·시간·플레이어 경계 계약을 검증한다."""
from dataclasses import replace
import unittest

from textris.art import ArtCanvas, RenderContext, battle_viewports, game_layout
from textris.art_director import Cue
from textris.theme_art import ThemeScene


NATURE_THEMES = ('abyss', 'aurora')
EXISTING_THEMES = ('cathedral', 'cyberpunk', 'space', 'fire', 'crt', 'mono')
CEREMONIES = ('clear', 'bloom', 'ascension', 'victory', 'eclipse', 'awakening')


def geometry(canvas):
    return tuple(sorted((p, ink.glyph, ink.mask) for p, ink in canvas.cells.items()))


class CountingCanvas(ArtCanvas):
    def __init__(self, context):
        super().__init__(context)
        self.curve_samples = 0

    def curve(self, points, style=3, depth=0):
        points = tuple(points)
        self.curve_samples += len(points)
        super().curve(points, style, depth)


class EightThemeSceneTests(unittest.TestCase):
    def test_new_scenes_keep_distinct_geometry_and_tonal_surfaces_without_color(self):
        scene = ThemeScene()
        for ascii_mode, braille in ((True, True), (False, True), (False, False)):
            pictures = []
            for theme in EXISTING_THEMES + NATURE_THEMES:
                with self.subTest(theme=theme, ascii=ascii_mode, braille=braille):
                    ctx = RenderContext(120, 40, ascii_mode=ascii_mode, braille=braille)
                    c = scene.render(ctx, 12.5, theme, density=0)
                    self.assertGreater(len(c.cells), 250)
                    if ascii_mode:
                        self.assertTrue(all(ink.glyph.isascii() for ink in c.cells.values()))
                    elif theme in NATURE_THEMES:
                        shades = [ink.glyph for ink in c.cells.values() if ink.glyph in '░▒▓█']
                        self.assertGreater(len(shades), 20)
                        self.assertGreaterEqual(len(set(shades)), 3)
                    pictures.append(geometry(c))
            self.assertEqual(len(set(pictures)), 8)

    def test_new_ceremonies_and_spin_have_distinct_silhouettes_at_same_phase(self):
        ctx = RenderContext(120, 40, game_layout(120, 40).protected, ascii_mode=True)
        pictures = []
        for theme in NATURE_THEMES:
            scene = ThemeScene()
            base = geometry(scene.render(ctx, 11, theme, density=0))
            for name in CEREMONIES + ('spin',):
                cue = Cue('bloom' if name == 'spin' else name, 10, 12,
                          coords=(18, 19, 20, 21), variant='spin' if name == 'spin' else '')
                result = geometry(scene.render(ctx, 11, theme, cue, flash=False, density=0))
                self.assertNotEqual(base, result, (theme, name))
                pictures.append(result)
        self.assertEqual(len(set(pictures)), 14)

    def test_every_new_ceremony_consumes_phase_power_and_intensity_without_flash(self):
        ctx = RenderContext(120, 40, ascii_mode=True)
        for theme in NATURE_THEMES:
            for name in CEREMONIES:
                with self.subTest(theme=theme, name=name):
                    cue = Cue(name, 10, 12, coords=(18, 19, 20, 21))
                    def draw(time=11, power=1, intensity=1):
                        c = ArtCanvas(ctx)
                        ThemeScene().ceremony(c, time, theme, replace(cue, power=power),
                                              False, intensity, (49, 9))
                        return geometry(c)
                    high = draw()
                    self.assertTrue(high)
                    self.assertNotEqual(high, draw(time=10.6))
                    self.assertNotEqual(high, draw(power=1.6))
                    self.assertNotEqual(high, draw(intensity=.25))
                    self.assertEqual(draw(power=0), ())
                    self.assertEqual(draw(intensity=0), ())

    def test_row_ceremonies_follow_shifted_board_and_producer_rows(self):
        ctx = RenderContext(120, 50, ascii_mode=True)
        for theme in NATURE_THEMES:
            for name, variant in (('clear', ''), ('bloom', ''), ('bloom', 'spin'), ('ascension', '')):
                with self.subTest(theme=theme, name=name, variant=variant):
                    cue = Cue(name, 10, 12, coords=(8,), variant=variant)
                    def draw(rows, board):
                        c = ArtCanvas(ctx)
                        ThemeScene().ceremony(c, 11, theme, replace(cue, coords=rows), False, 1, board)
                        return c
                    first = draw((8,), (49, 9))
                    shifted = draw((8,), (49, 13))
                    moved_row = draw((12,), (49, 9))
                    self.assertTrue(first.cells)
                    self.assertNotEqual(geometry(first), geometry(shifted))
                    self.assertEqual(geometry(shifted), geometry(moved_row))
                    if name == 'clear':
                        self.assertEqual({(x, y + 4) for x, y in first.cells}, set(shifted.cells))

    def test_new_scenes_and_events_survive_minimum_size_low_quality_and_ascii(self):
        layout = game_layout(64, 28)
        ctx = RenderContext(64, 28, layout.protected, ascii_mode=True, quality=.15,
                            viewports=layout.viewports)
        for theme in NATURE_THEMES:
            scene = ThemeScene()
            base = scene.render(ctx, 11, theme, density=0)
            self.assertGreater(len(base.cells), 40)
            for name in CEREMONIES + ('spin',):
                with self.subTest(theme=theme, name=name):
                    cue = Cue('bloom' if name == 'spin' else name, 10, 12,
                              coords=(18, 19, 20, 21), variant='spin' if name == 'spin' else '')
                    c = scene.render(ctx, 11, theme, cue, flash=False, density=0)
                    self.assertNotEqual(geometry(base), geometry(c))
                    self.assertFalse(set(c.cells) & c.blocked)
                    self.assertTrue(all(ink.glyph.isascii() for ink in c.cells.values()))

    def test_all_new_events_are_confined_to_the_owning_viewport(self):
        viewports = battle_viewports(120, 40)
        protected = tuple(rect for v in viewports for rect in v.protected)
        ctx = RenderContext(120, 40, protected, viewports=viewports)
        for theme in NATURE_THEMES:
            scene = ThemeScene()
            base = scene.render(ctx, 11, theme)
            for viewport in viewports:
                for name in CEREMONIES:
                    with self.subTest(theme=theme, player=viewport.player_id, name=name):
                        cue = Cue(name, 10, 12, coords=(18, 19, 20, 21), player_id=viewport.player_id)
                        c = scene.render(ctx, 11, theme, cue, flash=False)
                        changed = {p for p, ink in c.cells.items() if base.cells.get(p) != ink}
                        self.assertTrue(changed)
                        self.assertFalse(set(c.cells) & c.blocked)
                        self.assertTrue(all(any(x <= px < x+w and y <= py < y+h
                                                for x, y, w, h in viewport.effect_regions)
                                            for px, py in changed))

    def test_time_can_freeze_seek_and_repeat_without_retaining_old_frames(self):
        ctx = RenderContext(120, 40, game_layout(120, 40).protected)
        for theme in EXISTING_THEMES + NATURE_THEMES:
            with self.subTest(theme=theme):
                scene = ThemeScene()
                first = geometry(scene.render(ctx, 2, theme, density=0))
                self.assertNotEqual(first, geometry(scene.render(ctx, 9, theme, density=0)))
                scene.render(ctx, 10000, theme)
                self.assertEqual(first, geometry(scene.render(ctx, 2, theme, density=0)))
                self.assertEqual(geometry(scene.render(ctx, 2, theme, motion_speed=0)),
                                 geometry(scene.render(ctx, 9, theme, motion_speed=0)))
                self.assertLessEqual(len(scene.cathedral._layers), 6)

    def test_new_scene_low_quality_reduces_work_but_preserves_silhouette(self):
        scene = ThemeScene()
        for theme in NATURE_THEMES:
            low = CountingCanvas(RenderContext(120, 40, quality=.15))
            high = CountingCanvas(RenderContext(120, 40, quality=1))
            getattr(scene, theme)(low, 12.5)
            getattr(scene, theme)(high, 12.5)
            self.assertGreater(len(low.cells), 150, theme)
            self.assertLess(low.curve_samples, high.curve_samples * .6, theme)

    def test_new_events_expire_and_ignore_unknown_or_empty_owner_regions(self):
        ctx = RenderContext(120, 40, viewports=battle_viewports(120, 40))
        for theme in NATURE_THEMES:
            scene = ThemeScene()
            cue = Cue('bloom', 10, 12, coords=(18,), player_id='p2')
            for time in (9, 10, 12, 13):
                self.assertEqual(scene.render(ctx, time, theme).cells,
                                 scene.render(ctx, time, theme, cue).cells)
            self.assertEqual(scene.render(ctx, 11, theme).cells,
                             scene.render(ctx, 11, theme, replace(cue, player_id='missing')).cells)
            empty = replace(ctx, viewports=tuple(replace(v, effect_regions=()) for v in ctx.viewports))
            self.assertEqual(scene.render(empty, 11, theme).cells,
                             scene.render(empty, 11, theme, cue).cells)


if __name__ == '__main__':
    unittest.main()
