"""전체 테마가 독립적인 구도와 동일한 합성 계약을 사용한다."""
import unittest
from textris.art import RenderContext
from textris.scenes import THEMES


class ThemeArtTests(unittest.TestCase):
    def test_all_six_compositions_are_distinct_deterministic_and_protected(self):
        from textris.theme_art import ThemeScene
        context=RenderContext(120,40,protected=((45,8,28,24),))
        renderer=ThemeScene(); pictures=[]
        for theme in THEMES:
            a=renderer.render(context,10,theme)
            self.assertGreater(len(a.cells),150,theme)
            self.assertEqual(a.cells,renderer.render(context,10,theme).cells)
            self.assertFalse(any(45<=x<73 and 8<=y<32 for x,y in a.cells),theme)
            pictures.append(tuple(sorted((p,v.glyph) for p,v in a.cells.items())))
        self.assertEqual(len(set(pictures)),6)

    def test_ascii_shapes_and_bounded_cues_for_all_themes(self):
        from textris.theme_art import ThemeScene
        from textris.art_director import ArtDirector
        renderer=ThemeScene();d=ArtDirector();d.trigger('clear',dict(count=4,perfect=True,rows=[18,19,20,21]),10)
        for theme in THEMES:
            c=renderer.render(RenderContext(80,30,ascii_mode=True),10.4,theme,d.major)
            self.assertTrue(all(v.glyph.isascii() for v in c.cells.values()),theme)
            self.assertTrue(all(0<=x<79 and 0<=y<30 for x,y in c.cells),theme)

    def test_density_changes_each_theme_without_touching_protected_cells(self):
        from textris.theme_art import ThemeScene
        renderer=ThemeScene(); context=RenderContext(120,40,protected=((45,8,28,24),))
        for theme in THEMES:
            low=renderer.render(context,10,theme,density=.25)
            high=renderer.render(context,10,theme,density=1)
            self.assertNotEqual(low.cells,high.cells,theme)

    def test_gallery_theme_change_restarts_selected_effect(self):
        from tests.test_ui import UITests
        UITests.setUp(self)
        from textris.scenes import BACKGROUNDS,PROFILES
        a=self.app; a.open_gallery(); a.gallery_index=len(BACKGROUNDS)
        a.gallery_trigger(); a.profile_selection=PROFILES.index('theme'); a.change_profile(1)
        self.assertEqual(a.effects.actions,[('impact',a.now)])

    def test_subcell_line_endpoints_and_protection(self):
        from textris.art import ArtCanvas
        c=ArtCanvas(RenderContext(30,20,protected=((12,0,3,20),)))
        c.line((2,2),(22,12),4)
        self.assertIn((2,2),c.cells);self.assertIn((22,12),c.cells)
        self.assertFalse(any(12<=x<15 for x,y in c.cells))
        for x in range(2,23):
            if not 12<=x<15: self.assertTrue(any(px==x for px,py in c.cells))
