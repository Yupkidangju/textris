"""작은 창의 테마 공간과 향후 보드별 렌더 경계의 계약."""
from dataclasses import replace
from unittest.mock import patch
import unittest

from textris.art import ArtCanvas, RenderContext, game_layout, protected_cells
from textris.art_director import ArtDirector


class ViewportTests(unittest.TestCase):
    def test_small_layout_leaves_theme_space_and_preserves_board_origin(self):
        layout=game_layout(64,28)
        self.assertEqual(layout.board,(21,3))
        context=RenderContext(64,28,layout.protected)
        self.assertGreater(63*28-len(protected_cells(context)),300)
        for y in range(4,24):
            for x in range(22,42): self.assertIn((x,y),protected_cells(context))

    def test_future_two_boards_fit_and_have_disjoint_effect_regions(self):
        from textris.art import battle_viewports
        for width,height in ((64,28),(80,30),(120,40),(160,50)):
            first,second=battle_viewports(width,height)
            self.assertEqual((first.player_id,second.player_id),('p1','p2'))
            fields=[]; areas=[]
            for viewport in (first,second):
                x,y,w,h=viewport.board_rect
                self.assertEqual((w,h),(22,22))
                self.assertTrue(0<=x and x+w<=width-1 and 0<=y and y+h<=height)
                fields.append({(xx,yy) for yy in range(y,y+h) for xx in range(x,x+w)})
                areas.append({(xx,yy) for x,y,w,h in viewport.effect_regions
                              for yy in range(y,y+h) for xx in range(x,x+w)})
            self.assertFalse(fields[0]&fields[1]); self.assertFalse(areas[0]&areas[1])

    def test_clip_rect_still_respects_existing_protected_cells(self):
        context=RenderContext(30,20,protected=((2,2,2,2),),clip_rect=(0,0,10,10))
        c=ArtCanvas(context); c.line((0,0),(28,18),4)
        self.assertTrue(c.cells)
        self.assertTrue(all(x<10 and y<10 and (x,y) not in c.blocked for x,y in c.cells))

    def test_ascii_subcell_lines_preserve_direction_and_density(self):
        horizontal=ArtCanvas(RenderContext(20,15,ascii_mode=True))
        vertical=ArtCanvas(RenderContext(20,15,ascii_mode=True))
        horizontal.line((1,2),(15,2)); vertical.line((2,1),(2,12))
        self.assertIn('-', {ink.glyph for ink in horizontal.cells.values()})
        self.assertIn('|', {ink.glyph for ink in vertical.cells.values()})
        self.assertTrue(all(ink.glyph.isascii() for ink in horizontal.cells.values()))

    def test_equal_priority_clear_uses_latest_semantics_without_extending_lifetime(self):
        d=ArtDirector()
        d.trigger('clear',dict(count=4,spin=False,rows=[18,19,20,21]),100)
        end=d.major.end
        d.trigger('clear',dict(count=1,spin=True,rows=[8],combo=4),100.1)
        self.assertEqual(d.major.label,'T SPIN'); self.assertEqual(d.major.coords,(8,))
        self.assertEqual(d.major.variant,'spin'); self.assertEqual(d.major.end,end)
        d.trigger('win',{},100.2)
        d.trigger('clear',dict(count=1,rows=[21]),100.3)
        self.assertEqual(d.major.label,'VICTORY')

    def test_equal_priority_different_kind_and_owner_are_updated(self):
        d=ArtDirector(); d.trigger('boss_break',{},100)
        end=d.major.end
        d.trigger('level',dict(player_id='p2'),100.1)
        self.assertEqual((d.major.name,d.major.variant,d.major.player_id),('awakening','level','p2'))
        self.assertEqual(d.major.end,end)

    def test_lower_quality_reduces_subpixel_work_and_preserves_line_endpoints(self):
        original=ArtCanvas._subpixel; counts=[]
        for quality in (1.,.7,.4):
            count=[0]
            def observed(canvas,*args):
                count[0]+=1; return original(canvas,*args)
            canvas=ArtCanvas(RenderContext(30,20,quality=quality))
            with patch.object(ArtCanvas,'_subpixel',observed): canvas.line((1,1),(25,17))
            self.assertIn((1,1),canvas.cells); self.assertIn((25,17),canvas.cells)
            counts.append(count[0])
        self.assertGreater(counts[0],counts[1]); self.assertGreater(counts[1],counts[2])


if __name__=='__main__': unittest.main()
