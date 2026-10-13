"""테마 면 표현과 대성당 성취의 의미가 최종 문자에 도달한다."""
from dataclasses import replace
import unittest

from textris.art import ArtCanvas, BoardViewport, RenderContext, battle_viewports, game_layout
from textris.art_director import Cue
from textris.scenes import THEMES
from textris.theme_art import ThemeScene


def geometry(canvas):
    return tuple(sorted((point, ink.glyph, ink.mask) for point, ink in canvas.cells.items()))


class ThemeEnhancementTests(unittest.TestCase):
    def test_explicit_viewport_without_effect_regions_disables_major_art(self):
        viewport=BoardViewport('p1',(49,9,22,22))
        ctx=RenderContext(120,40,viewports=(viewport,))
        scene=ThemeScene()
        for theme in THEMES:
            with self.subTest(theme=theme):
                cue=Cue('bloom',10,12,coords=(18,19,20,21))
                self.assertTrue(scene.render(ctx,11,theme).cells==
                                scene.render(ctx,11,theme,cue).cells)

    def test_low_quality_reduces_dense_ceremony_sampling_and_keeps_span(self):
        class CountingCanvas(ArtCanvas):
            def __init__(self,context):
                super().__init__(context)
                self.samples=0
                self.points=[]

            def curve(self,points,style=3,depth=0):
                points=list(points)
                self.samples+=len(points)
                self.points.extend(points)
                super().curve(points,style,depth)

        for theme,name in (('crt','bloom'),('space','ascension'),
                           ('space','awakening'),('crt','victory')):
            with self.subTest(theme=theme,name=name):
                scene=ThemeScene();cue=Cue(name,10,12,coords=(18,19,20,21))
                low=CountingCanvas(RenderContext(120,40,quality=.15))
                high=CountingCanvas(RenderContext(120,40,quality=1))
                scene.ceremony(low,11,theme,cue,False,1,board=(49,9))
                scene.ceremony(high,11,theme,cue,False,1,board=(49,9))
                self.assertLess(low.samples,high.samples*.6)
                for axis in (0,1):
                    self.assertAlmostEqual(min(p[axis] for p in low.points),
                                           min(p[axis] for p in high.points),delta=.4)
                    self.assertAlmostEqual(max(p[axis] for p in low.points),
                                           max(p[axis] for p in high.points),delta=.4)

    def test_small_window_keeps_each_theme_symbol_in_exposed_margins(self):
        layout=game_layout(64,28)
        ctx=RenderContext(64,28,layout.protected,ascii_mode=True,viewports=layout.viewports)
        scene=ThemeScene();pictures=[]
        for theme in THEMES:
            canvas=scene.render(ctx,11,theme,density=0)
            self.assertGreater(len(canvas.cells),40,theme)
            self.assertFalse(set(canvas.cells)&canvas.blocked,theme)
            pictures.append(geometry(canvas))
        self.assertEqual(len(set(pictures)),6)

    def test_small_window_every_ceremony_changes_exposed_art_without_covering_hud(self):
        layout=game_layout(64,28)
        ctx=RenderContext(64,28,layout.protected,ascii_mode=True,viewports=layout.viewports)
        scene=ThemeScene()
        for theme in THEMES:
            base=geometry(scene.render(ctx,11,theme,density=0))
            for name in ('clear','bloom','ascension','victory','eclipse','awakening'):
                with self.subTest(theme=theme,name=name):
                    cue=Cue(name,10,12,coords=(18,19,20,21))
                    c=scene.render(ctx,11,theme,cue,density=0,flash=False)
                    self.assertTrue(base!=geometry(c),'ceremony hidden in minimum window')
                    self.assertFalse(set(c.cells)&c.blocked)

    def test_unknown_player_major_cue_does_not_use_the_legacy_board(self):
        scene=ThemeScene()
        ctx=RenderContext(120,40,viewports=battle_viewports(120,40))
        for theme in THEMES:
            cue=Cue('bloom',10,12,coords=(18,),player_id='missing')
            self.assertTrue(scene.render(ctx,11,theme).cells==
                            scene.render(ctx,11,theme,cue).cells,theme)

    def test_major_ceremony_stays_in_selected_player_effect_regions(self):
        viewports=battle_viewports(120,40)
        protected=tuple(rect for v in viewports for rect in (v.board_rect,)+v.hud_rects)
        ctx=RenderContext(120,40,protected,viewports=viewports)
        scene=ThemeScene()
        for theme in THEMES:
            base=scene.render(ctx,11,theme)
            cue=Cue('ascension',10,12,coords=(18,19,20,21),player_id='p2')
            canvas=scene.render(ctx,11,theme,cue)
            changed={p for p,ink in canvas.cells.items() if base.cells.get(p)!=ink}
            self.assertTrue(changed,theme)
            self.assertTrue(all(any(x<=px<x+w and y<=py<y+h
                                for x,y,w,h in viewports[1].effect_regions)
                                for px,py in changed),theme)

    def test_spin_is_angular_and_tetris_is_a_distinct_strong_clear(self):
        scene=ThemeScene();ctx=RenderContext(120,40,game_layout(120,40).protected,ascii_mode=True)
        for theme in THEMES:
            cue=Cue('bloom',10,12,coords=(18,19,20,21),variant='tetris')
            tetris=scene.render(ctx,11,theme,cue,flash=False)
            spin=scene.render(ctx,11,theme,replace(cue,variant='spin'),flash=False)
            self.assertTrue(geometry(tetris)!=geometry(spin),theme)

    def test_cathedral_all_six_ceremonies_have_distinct_silhouettes_without_flash(self):
        scene = ThemeScene()
        ctx = RenderContext(120, 40, ((49, 9, 22, 22),), ascii_mode=True)
        pictures = []
        for name in ('clear', 'bloom', 'ascension', 'victory', 'eclipse', 'awakening'):
            cue = Cue(name, 10, 12, coords=(18, 19, 20, 21))
            pictures.append(geometry(scene.render(ctx, 11, 'cathedral', cue, flash=False)))
        self.assertEqual(len(set(pictures)), 6)

    def test_cathedral_geometry_consumes_strength_for_each_semantic_ceremony(self):
        scene = ThemeScene()
        ctx = RenderContext(120, 40, ((49, 9, 22, 22),), ascii_mode=True)
        for name in ('clear', 'bloom', 'ascension', 'victory', 'eclipse', 'awakening'):
            with self.subTest(name=name):
                cue = Cue(name, 10, 12, coords=(18, 19, 20, 21))
                low = scene.render(ctx, 11, 'cathedral', cue, flash=False, intensity=.25)
                high = scene.render(ctx, 11, 'cathedral', cue, flash=False, intensity=1)
                strong = scene.render(ctx, 11, 'cathedral', replace(cue, power=1.6), flash=False, intensity=1)
                self.assertNotEqual(geometry(low), geometry(high))
                self.assertNotEqual(geometry(high), geometry(strong))

    def test_cathedral_strong_clears_follow_actual_board_rows(self):
        scene = ThemeScene()
        ctx = RenderContext(120, 50, ascii_mode=True)
        for name in ('clear', 'bloom', 'ascension'):
            with self.subTest(name=name):
                cue = Cue(name, 10, 12, coords=(18,))
                lower = scene.render(ctx, 11, 'cathedral', cue, board=(49, 9))
                upper = scene.render(ctx, 11, 'cathedral', replace(cue, coords=(8,)), board=(49, 9))
                moved = scene.render(ctx, 11, 'cathedral', cue, board=(49, 5))
                self.assertNotEqual(geometry(lower), geometry(upper))
                self.assertNotEqual(geometry(lower), geometry(moved))

    def test_every_ambient_theme_contains_visible_surface_shading(self):
        scene = ThemeScene()
        for theme in THEMES:
            with self.subTest(theme=theme):
                canvas = scene.render(RenderContext(120, 40), 12.5, theme, density=0)
                # 면 명암은 Braille 선만으로 대체되지 않아야 한다.
                shaded = [ink for ink in canvas.cells.values() if ink.glyph in '░▒▓█']
                self.assertGreater(len(shaded), 20)
                self.assertGreaterEqual(len({ink.glyph for ink in shaded}), 3)

    def test_low_quality_reduces_curve_sampling_without_removing_silhouette(self):
        class CountingCanvas(ArtCanvas):
            def __init__(self, context):
                super().__init__(context)
                self.samples = 0

            def curve(self, points, style=3, depth=0):
                points = list(points)
                self.samples += len(points)
                super().curve(points, style, depth)

        for theme in THEMES[1:]:
            with self.subTest(theme=theme):
                scene = ThemeScene()
                low = CountingCanvas(RenderContext(120, 40, quality=.3))
                high = CountingCanvas(RenderContext(120, 40, quality=1))
                getattr(scene, theme)(low, 12.5)
                getattr(scene, theme)(high, 12.5)
                self.assertLess(low.samples, high.samples * .8)
                self.assertGreater(len(low.cells), 150)

    def test_cathedral_expired_ceremony_and_zero_intensity_are_quiet(self):
        scene = ThemeScene()
        ctx = RenderContext(120, 40)
        cue = Cue('victory', 10, 12)
        for time in (9, 12, 13):
            self.assertEqual(scene.render(ctx, time, 'cathedral').cells,
                             scene.render(ctx, time, 'cathedral', cue).cells)
        self.assertEqual(scene.render(ctx, 11, 'cathedral').cells,
                         scene.render(ctx, 11, 'cathedral', cue, intensity=0).cells)
