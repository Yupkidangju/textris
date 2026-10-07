"""대성당의 시각 합성 경계와 게임 불변 계약."""
import curses
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests import test_ui


class CanvasTests(unittest.TestCase):
    def test_braille_coordinates_depth_and_protection(self):
        from textris.art import ArtCanvas, RenderContext
        c=ArtCanvas(RenderContext(12,8,protected=((2,2,3,3),)))
        for x,y in ((0,0),(1,0),(0,3),(1,3)):
            c.dot(x/2,y/4,2,depth=1)
        self.assertEqual(c.cells[0,0].glyph,chr(0x2800+1+8+64+128))
        c.put(0,0,'X',4,depth=-1)
        c.dot(0,0,2,depth=2)
        self.assertEqual(c.cells[0,0].glyph,'X')
        c.line((-20,2.5),(20,2.5),2)
        self.assertFalse(any(2<=x<5 and 2<=y<5 for x,y in c.cells))
        self.assertTrue(all(0<=x<11 and 0<=y<8 for x,y in c.cells))

    def test_ascii_and_no_braille_keep_continuous_shapes(self):
        from textris.art import ArtCanvas, RenderContext
        for ascii_mode,braille in ((True,True),(False,False)):
            c=ArtCanvas(RenderContext(20,10,ascii_mode=ascii_mode,braille=braille))
            c.line((1,1),(15,7),2)
            self.assertGreater(len(c.cells),12)
            chars=''.join(v.glyph for v in c.cells.values())
            self.assertFalse(any(0x2800<=ord(v)<=0x28ff for v in chars))
            if ascii_mode: self.assertTrue(chars.isascii())

    def test_scene_is_deterministic_and_respects_all_masks(self):
        from textris.art import RenderContext
        from textris.cathedral import CathedralScene
        ctx=RenderContext(120,40,protected=((49,9,22,22),(29,10,18,20)))
        s=CathedralScene()
        first=s.render(ctx,12.5)
        self.assertEqual(first.cells,s.render(ctx,12.5).cells)
        self.assertGreater(len(first.cells),250)
        self.assertNotEqual(first.cells,s.render(ctx,13.5).cells)
        self.assertFalse(any(49<=x<71 and 9<=y<31 for x,y in first.cells))


class DirectorTests(unittest.TestCase):
    def test_priority_merge_does_not_extend_lifetime(self):
        from textris.art_director import ArtDirector
        d=ArtDirector()
        data=dict(count=4,perfect=True,spin=False,rows=[18,19,20,21],combo=3)
        d.trigger('clear',data,10)
        self.assertEqual(d.major.name,'ascension')
        end=d.major.end
        for i in range(50): d.trigger('clear',data,10+i*.01)
        self.assertEqual(d.major.end,end)
        d.trigger('level',{},10.6)
        self.assertEqual(d.major.name,'ascension')
        d.trigger('win',{},10.7)
        self.assertEqual(d.major.name,'victory')
        for i in range(50): d.trigger('drop',dict(cells=((4,4),),distance=16),10.8+i*.001)
        self.assertLessEqual(len(d.local),8)
        d.update(14)
        self.assertIsNone(d.major)
        self.assertFalse(d.local)

    def test_event_data_is_not_mutated_and_zero_line_spin_works(self):
        from textris.art_director import ArtDirector
        d=ArtDirector(); data=dict(count=0,perfect=False,spin=True,rows=[],combo=-1)
        original=data.copy(); d.trigger('clear',data,1)
        self.assertEqual(data,original)
        self.assertEqual(d.major.name,'bloom')


class CathedralUITests(unittest.TestCase):
    setUp=test_ui.UITests.setUp

    def test_new_default_and_existing_theme_roundtrip(self):
        from textris.storage import Store
        self.assertEqual(self.store.settings['theme'],'cathedral')
        for theme in ('cathedral','cyberpunk','mono'):
            self.store.settings['theme']=theme; self.store.save()
            other=Store(Path(self.tmp.name)); other.load()
            self.assertEqual(other.settings['theme'],theme)

    def test_playfield_and_hud_are_unchanged_by_peak_effect(self):
        from textris.engine import Piece, cells, HIDDEN
        from textris.art import game_layout
        a=self.app; a.start(); a.screen='playing'; a.game.state='playing'; a.now=100
        a.settings['shake']=False
        a.win.size=(40,120); a.game.board[21][0]='T'; a.game.active=Piece('I')
        with patch('curses.doupdate'):
            a.draw(); before=list(a.win.lines)
            a.effects.trigger('clear',dict(count=4,rows=[18,19,20,21],combo=4,spin=False,perfect=True,points=4000),100)
            a.now=100.4; a.draw()
        def grid(lines):
            result={}
            for y,x,text in lines:
                for dx,c in enumerate(text): result[x+dx,y]=c
            return result
        old,new=grid(before),grid(a.win.lines)
        bx,by=game_layout(120,40).board
        for x,y in cells(a.game.active):
            if y>=HIDDEN:
                for dx in (0,1): self.assertEqual(old[bx+1+2*x+dx,by+1+y-HIDDEN],new[bx+1+2*x+dx,by+1+y-HIDDEN])
        for y in range(by+1,by+21):
            for x in range(bx+1,bx+21): self.assertEqual(old[x,y],new[x,y])

    def test_cathedral_resizes_and_respects_character_preferences(self):
        a=self.app; a.start(); a.screen='playing'; a.game.state='playing'
        with patch('curses.doupdate'):
            for size in ((28,64),(30,80),(40,120),(50,160)):
                a.win.size=size
                for ascii_mode,braille in ((True,True),(False,False),(False,True)):
                    a.settings.update(ascii=ascii_mode,braille=braille,flash=False,shake=False)
                    a.draw()
                    chars=''.join(text for y,x,text in a.win.lines)
                    if not braille or ascii_mode:
                        self.assertFalse(any(0x2800<=ord(c)<=0x28ff for c in chars))
                    if ascii_mode: self.assertTrue(chars.replace('·','').isascii())
                    self.assertIn('SCORE',chars)

    def test_palette_fallback_never_uses_unallocated_pair(self):
        from textris.art import Palette
        for colors,pairs in ((256,64),(8,8),(0,0)):
            unit=curses.A_COLOR & -curses.A_COLOR
            with patch('curses.init_pair') as init, patch('curses.color_pair',side_effect=lambda n:n*unit):
                p=Palette(); p.setup(colors,pairs)
                for style in range(16):
                    attr=p.attr(style,True)
                    self.assertLessEqual((attr & curses.A_COLOR)//unit,max(0,pairs-1))
                self.assertTrue(all(call.args[0]<pairs for call in init.call_args_list))
                self.assertEqual(p.attr(3,False)&curses.A_COLOR,0)

class ArtTimingTests(unittest.TestCase):
    def test_cached_scene_is_independent_of_call_order(self):
        from textris.art import RenderContext,game_layout
        from textris.cathedral import CathedralScene
        ctx=RenderContext(120,40,game_layout(120,40).protected)
        s=CathedralScene(); expected=s.render(ctx,10.2).cells.copy()
        s.render(ctx,11.4); s.render(ctx,1)
        self.assertEqual(expected,s.render(ctx,10.2).cells)

    def test_speed_changes_duration_and_minor_cue_expires(self):
        from textris.art_director import ArtDirector
        d=ArtDirector(); d.trigger('drop',{},10,speed=2)
        self.assertAlmostEqual(d.local[0].end,10.175)
        d.update(10.2); self.assertFalse(d.local)

    def test_flash_disabled_does_not_brighten_ceremony(self):
        from textris.art import RenderContext
        from textris.art_director import Cue
        from textris.cathedral import CathedralScene
        c=RenderContext(120,40)
        cue=Cue('ascension',10,11.8,4)
        s=CathedralScene()
        on=s.render(c,10.6,cue,flash=True)
        off=s.render(c,10.6,cue,flash=False)
        self.assertNotEqual(on.cells,off.cells)
        on_bright=sum(v.style==9 for v in on.cells.values())
        off_bright=sum(v.style==9 for v in off.cells.values())
        self.assertLess(off_bright,on_bright)

class CathedralReviewTests(unittest.TestCase):
    setUp=test_ui.UITests.setUp

    def test_replay_open_and_seek_clear_all_presentation_state(self):
        from textris.session import Session
        a=self.app; a.now=100
        s=Session(seed=42); s.command('drop'); s.step()
        a.effects.configure(a.settings); a.effects.trigger('win',{},a.now)
        a.open_replay(s.replay())
        self.assertIsNone(a.effects.director.major)
        a.effects.trigger('win',{},a.now); a.handle('d')
        self.assertIsNone(a.effects.director.major)
        self.assertFalse(a.effects.director.local)
        self.assertEqual(a.effects.headline,'')

    def test_gallery_f_toggle_keeps_selected_effect_visible(self):
        from textris.scenes import BACKGROUNDS
        a=self.app; a.now=100; a.open_gallery(); a.gallery_index=len(BACKGROUNDS)
        a.gallery_trigger(); a.handle('f'); a.handle('f')
        self.assertTrue(a.effects.actions)
        a.win.erase(); a.effects.draw(a,22,4,100.1)
        self.assertTrue(a.win.lines)

    def test_headline_belongs_to_accepted_cue(self):
        a=self.app; a.effects.configure(a.settings)
        a.effects.trigger('clear',dict(count=4,rows=[18,19,20,21],spin=False,perfect=False,points=800),10)
        a.effects.trigger('level',{},11.21)
        self.assertEqual(a.effects.director.major.name,'awakening')
        self.assertEqual(a.effects.director.major.label,'LEVEL UP')
        a.effects.trigger('clear',dict(count=1,rows=[21],spin=False,perfect=False),11.22)
        self.assertEqual(a.effects.director.major.label,'LEVEL UP')

    def test_background_cache_uses_canonical_time(self):
        from textris.effects import Effects
        a=self.app; a.win.size=(40,120); a.screen='gallery'; a.game=None
        a.effects.scene='cathedral'
        a.effects.background(a,10.0417); a.effects.background(a,10.0767)
        expected=a.effects._art_cache.cells.copy()
        a.effects=Effects(); a.effects.scene='cathedral'; a.effects.background(a,10.0767)
        self.assertEqual(expected,a.effects._art_cache.cells)

    def test_achievement_does_not_overwrite_mode_title(self):
        a=self.app; a.win.size=(40,120); a.start(); a.screen='playing'; a.now=100
        a.effects.configure(a.settings)
        a.effects.trigger('clear',dict(count=4,rows=[18,19,20,21],perfect=True,spin=False,points=4000),100)
        a.now=100.4
        with patch('curses.doupdate'): a.draw()
        self.assertTrue(any('T E X T R I S' in text and 'Marathon' in text for y,x,text in a.win.lines))

class CathedralDangerTests(unittest.TestCase):
    setUp=test_ui.UITests.setUp
    def test_monochrome_danger_has_text_not_only_border_color(self):
        a=self.app; a.start(); a.screen='playing'; a.settings['color']=False
        a.effects.danger=True
        with patch('curses.doupdate'): a.draw()
        self.assertTrue(any('DANGER' in text for y,x,text in a.win.lines))

class BasicPaletteTests(unittest.TestCase):
    def test_limited_pairs_preserve_piece_color_identity(self):
        from textris.art import Palette
        unit=curses.A_COLOR & -curses.A_COLOR
        with patch('curses.init_pair'),patch('curses.color_pair',side_effect=lambda n:n*unit):
            p=Palette(); p.setup(8,8)
            self.assertEqual(p.attr(16)&curses.A_COLOR,unit)
            self.assertEqual(p.attr(17)&curses.A_COLOR,2*unit)
