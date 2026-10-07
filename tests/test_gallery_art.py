import unittest

from textris.art import RenderContext
from textris.gallery_art import GalleryArt
from textris.scenes import BACKGROUNDS, EFFECTS


class GalleryArtTests(unittest.TestCase):
    def test_catalog_is_distinct_and_deterministic(self):
        renderer = GalleryArt()
        signatures = set()
        for names, age in ((BACKGROUNDS, None), (EFFECTS, .6)):
            for name in names:
                with self.subTest(name=name, age=age):
                    context = RenderContext(96, 32)
                    a = renderer.render(context, 1.25, name, age=age)
                    b = renderer.render(context, 1.25, name, age=age)
                    self.assertGreater(len(a.cells), 15)
                    self.assertEqual(a.cells, b.cells)
                    signature = tuple(sorted((p, ink.glyph, ink.style) for p, ink in a.cells.items()))
                    self.assertNotIn(signature, signatures)
                    signatures.add(signature)

    def test_all_modes_clip_and_protect(self):
        for ascii_mode, braille in ((True, True), (False, True), (False, False)):
            context = RenderContext(64, 28, ((20, 8, 24, 12),), ascii_mode, braille)
            for names, age in ((BACKGROUNDS, None), (EFFECTS, .8)):
                for name in names:
                    with self.subTest(name=name, ascii=ascii_mode):
                        frame = GalleryArt().render(context, 2, name, age=age)
                        for (x, y), ink in frame.cells.items():
                            self.assertTrue(0 <= x < 63 and 0 <= y < 28)
                            self.assertFalse(20 <= x < 44 and 8 <= y < 20)
                            self.assertEqual(len(ink.glyph), 1)
                            if ascii_mode:
                                self.assertTrue(32 <= ord(ink.glyph) < 127)

    def test_effect_lifetime_and_controls(self):
        context = RenderContext(80, 30)
        for name in EFFECTS:
            for age in (-.01, 2, 5):
                self.assertFalse(GalleryArt().render(context, 1, name, age=age).cells)
            self.assertFalse(GalleryArt().render(context, 1, name, age=.5, intensity=0).cells)

    def test_motion_and_resize_are_stateless(self):
        renderer = GalleryArt()
        for name in BACKGROUNDS:
            context = RenderContext(100, 36)
            before = renderer.render(context, .3, name).cells
            renderer.render(RenderContext(64, 28), 3, name)
            self.assertEqual(before, renderer.render(context, .3, name).cells)
            self.assertNotEqual(before, renderer.render(context, 1.7, name).cells)
