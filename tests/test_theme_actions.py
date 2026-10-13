"""조작/상태의 형태, 수명, 허용영역 계약을 실제 캔버스로 검증한다."""
import unittest
from types import SimpleNamespace
from textris.art import ArtCanvas, RenderContext
from textris.art_director import Cue

THEMES=('cathedral','cyberpunk','space','fire','crt','mono')
ACTIONS=('drop','lock','rotate','hold','focus','move')


def picture(canvas):
    return tuple(sorted((pos, ink.glyph) for pos, ink in canvas.cells.items()))


def state(**values):
    defaults=dict(player_id='p1',danger=False,fever=False,combo=0,b2b=False,level=1)
    defaults.update(values)
    return SimpleNamespace(**defaults)


class ThemeActionTests(unittest.TestCase):
    def local(self,theme,action,t=.2,intensity=.8,quality=1,flash=False,coords=((4,14),(6,15))):
        from textris.theme_actions import render_local
        c=ArtCanvas(RenderContext(80,30,((29,3,22,22),),True,False,quality))
        render_local(c,(29,3),t,Cue(action,0,1,coords=coords),theme,intensity,flash)
        return c

    def test_each_action_has_six_distinct_visible_shapes_without_flash(self):
        for action in ACTIONS:
            images=[picture(self.local(theme,action)) for theme in THEMES]
            self.assertTrue(all(images),action)
            self.assertEqual(len(set(images)),6,action)

    def test_each_theme_separates_actions_and_moves_over_cue_lifetime(self):
        for theme in THEMES:
            self.assertEqual(len({picture(self.local(theme,a)) for a in ACTIONS}),6,theme)
            for action in ACTIONS:
                self.assertNotEqual(picture(self.local(theme,action,.15)),picture(self.local(theme,action,.65)),(theme,action))

    def test_local_cues_expire_and_zero_intensity_draws_nothing(self):
        for theme in THEMES:
            for action in ACTIONS:
                self.assertFalse(self.local(theme,action,1).cells)
                self.assertFalse(self.local(theme,action,-.1).cells)
                self.assertFalse(self.local(theme,action,intensity=0).cells)
                self.assertNotEqual(picture(self.local(theme,action,intensity=.25)),picture(self.local(theme,action,intensity=1)))

    def test_ascii_protection_low_quality_budget_and_landing_coordinates(self):
        for theme in THEMES:
            for action in ACTIONS:
                low=self.local(theme,action,quality=.25);high=self.local(theme,action)
                self.assertTrue(low.cells)
                self.assertLessEqual(len(low.cells),len(high.cells))
                self.assertTrue(all(ink.glyph.isascii() for ink in high.cells.values()))
                self.assertTrue(all(not (29<=x<51 and 3<=y<25) for x,y in high.cells))
                self.assertLess(len(high.cells),200)
            self.assertNotEqual(picture(self.local(theme,'lock')),picture(self.local(theme,'lock',coords=((4,4),))))

    def test_state_regions_isolate_players_and_neutral_recovers(self):
        from textris.theme_actions import render_state
        regions=((2,4,8,20),(55,4,8,20))
        viewport=SimpleNamespace(player_id='p1',effect_regions=regions)
        for theme in THEMES:
            c=ArtCanvas(RenderContext(80,30,((4,12,2,3),),True))
            original=c.context
            render_state(c,.2,theme,state(danger=True,fever=True,combo=3,b2b=True,level=4),viewport)
            self.assertIs(c.context,original)
            self.assertTrue(c.cells,theme)
            self.assertTrue(all(any(a<=x<a+w and b<=y<b+h for a,b,w,h in regions) for x,y in c.cells))
            self.assertTrue(all(not (4<=x<6 and 12<=y<15) for x,y in c.cells))
            neutral=ArtCanvas(original);render_state(neutral,.2,theme,state(),viewport)
            self.assertFalse(neutral.cells)
            other=ArtCanvas(original);render_state(other,.2,theme,state(player_id='p2'),viewport)
            self.assertFalse(other.cells)

    def test_each_state_has_distinct_shape_and_time_response_for_each_theme(self):
        from textris.theme_actions import render_state
        viewport=SimpleNamespace(player_id='p1',effect_regions=((2,3,12,22),(65,3,12,22)))
        for theme in THEMES:
            images=[]
            for values in (dict(danger=True),dict(fever=True),dict(combo=3),dict(b2b=True),dict(level=5)):
                frames=[]
                for t in (.2,.8):
                    c=ArtCanvas(RenderContext(80,30,ascii_mode=True));render_state(c,t,theme,state(**values),viewport)
                    self.assertTrue(c.cells,(theme,values));frames.append(picture(c))
                self.assertNotEqual(*frames,(theme,values))
                images.append(frames[0])
            self.assertEqual(len(set(images)),5,theme)

    def test_empty_regions_and_tiny_windows_are_safe(self):
        from textris.theme_actions import render_local, render_state
        for theme in THEMES:
            c=ArtCanvas(RenderContext(4,3,ascii_mode=True,quality=.25))
            render_state(c,2,theme,state(danger=True),SimpleNamespace(player_id='p1',effect_regions=()))
            self.assertFalse(c.cells)
            render_local(c,(1,1),.2,Cue('drop',0,1),theme,1,False)
            self.assertTrue(all(0<=x<3 and 0<=y<3 for x,y in c.cells))

    def test_low_quality_reduces_each_themes_local_detail(self):
        for theme in THEMES:
            low=sum(len(self.local(theme,a,quality=.15).cells) for a in ACTIONS)
            high=sum(len(self.local(theme,a,quality=1).cells) for a in ACTIONS)
            self.assertLess(low,high,theme)

    def test_two_viewports_keep_local_events_in_owners_regions(self):
        from textris.art import battle_viewports
        from textris.theme_actions import render_local
        viewports=battle_viewports(120,40)
        protected=tuple(v.board_rect for v in viewports)+tuple(r for v in viewports for r in v.hud_rects)
        for v in viewports:
            for theme in THEMES:
                c=ArtCanvas(RenderContext(120,40,protected,True,False,1,viewports))
                cue=Cue('drop',0,1,coords=((4,14),),player_id=v.player_id)
                render_local(c,v.board,.3,cue,theme,1,False)
                self.assertTrue(c.cells,(v.player_id,theme))
                self.assertTrue(all(any(a<=x<a+w and b<=y<b+h for a,b,w,h in v.effect_regions) for x,y in c.cells))
                self.assertFalse(any(any(a<=x<a+w and b<=y<b+h for a,b,w,h in protected) for x,y in c.cells))

    def test_minimum_layout_keeps_each_action_visible(self):
        from textris.art import game_layout
        from textris.theme_actions import render_local
        layout=game_layout(64,28)
        for theme in THEMES:
            for action in ACTIONS:
                c=ArtCanvas(RenderContext(64,28,layout.protected,True,False,.25,layout.viewports))
                render_local(c,layout.board,.2,Cue(action,0,1,coords=((4,15),)),theme,1,False)
                self.assertTrue(c.cells,(theme,action))

    def test_quality_reduces_actual_writes_and_combined_state_is_bounded(self):
        from textris.theme_actions import render_local,render_state
        class CountingCanvas(ArtCanvas):
            def __init__(self,context):
                super().__init__(context);self.writes=0
            def put(self,*args,**kwargs):
                self.writes+=1
                super().put(*args,**kwargs)
        for theme in THEMES:
            counts=[]
            for quality in (.15,1):
                total=0
                for action in ACTIONS:
                    c=CountingCanvas(RenderContext(80,30,ascii_mode=True,quality=quality))
                    render_local(c,(29,3),.2,Cue(action,0,1,coords=((4,14),)),theme,10,False)
                    self.assertLessEqual(c.writes,180)
                    total+=c.writes
                counts.append(total)
            self.assertLess(counts[0],counts[1],theme)
            c=CountingCanvas(RenderContext(80,30,ascii_mode=True))
            viewport=SimpleNamespace(player_id='p1',effect_regions=((2,2,12,26),(65,2,12,26)))
            render_state(c,.2,theme,state(danger=True,fever=True,combo=100,b2b=True,level=100),viewport)
            self.assertLessEqual(c.writes,260)

    def test_all_six_themes_separate_each_state_without_color(self):
        from textris.theme_actions import render_state
        viewport=SimpleNamespace(player_id='p1',effect_regions=((2,3,12,22),(65,3,12,22)))
        for values in (dict(danger=True),dict(fever=True),dict(combo=3),dict(b2b=True),dict(level=5)):
            images=[]
            for theme in THEMES:
                c=ArtCanvas(RenderContext(80,30,ascii_mode=True))
                render_state(c,.2,theme,state(**values),viewport)
                images.append(picture(c))
            self.assertEqual(len(set(images)),6,values)


    def test_minimum_layout_keeps_each_state_visible_and_distinct(self):
        from textris.art import game_layout
        from textris.theme_actions import render_state
        layout=game_layout(64,28)
        for values in (dict(danger=True),dict(fever=True),dict(combo=3),dict(b2b=True),dict(level=5)):
            images=[]
            for theme in THEMES:
                c=ArtCanvas(RenderContext(64,28,layout.protected,True,False,.25,layout.viewports))
                render_state(c,.2,theme,state(**values),layout.viewports[0])
                self.assertTrue(c.cells,(theme,values))
                images.append(picture(c))
            self.assertEqual(len(set(images)),6,values)

    def test_actual_two_viewports_states_keep_own_regions_and_remain_visible(self):
        from textris.art import battle_viewports
        from textris.theme_actions import render_state
        viewports=battle_viewports(120,40)
        protected=tuple(v.board_rect for v in viewports)+tuple(r for v in viewports for r in v.hud_rects)
        for v in viewports:
            for theme in THEMES:
                c=ArtCanvas(RenderContext(120,40,protected,True,False,.25,viewports))
                render_state(c,.2,theme,state(player_id=v.player_id,danger=True,fever=True,combo=3,b2b=True,level=4),v)
                self.assertTrue(c.cells,(v.player_id,theme))
                self.assertTrue(all(any(a<=x<a+w and b<=y<b+h for a,b,w,h in v.effect_regions) for x,y in c.cells))

    def test_omitted_viewport_resolves_players_context_region_and_rejects_unknown(self):
        from textris.art import battle_viewports
        from textris.theme_actions import render_state
        viewports=battle_viewports(120,40)
        protected=tuple(v.board_rect for v in viewports)+tuple(r for v in viewports for r in v.hud_rects)
        context=RenderContext(120,40,protected,True,False,1,viewports)
        c=ArtCanvas(context)
        render_state(c,.2,'fire',state(player_id='p2',danger=True))
        self.assertTrue(c.cells)
        regions=viewports[1].effect_regions
        self.assertTrue(all(any(a<=x<a+w and b<=y<b+h for a,b,w,h in regions) for x,y in c.cells))
        unknown=ArtCanvas(context)
        render_state(unknown,.2,'fire',state(player_id='missing',danger=True))
        self.assertFalse(unknown.cells)

    def test_successful_move_is_finite_distinct_visible_and_protected_at_minimum(self):
        from textris.art import game_layout
        from textris.theme_actions import render_local
        layout=game_layout(64,28)
        images=[]
        for theme in THEMES:
            context=RenderContext(64,28,layout.protected,True,False,.25,layout.viewports)
            cue=Cue('move',0,.12,coords=((8,8),),player_id='p1')
            c=ArtCanvas(context);render_local(c,layout.board,.03,cue,theme,.75,False)
            self.assertTrue(c.cells,theme)
            self.assertTrue(all(c.accepts(x,y) for x,y in c.cells))
            self.assertLessEqual(len(c.cells),180)
            images.append(picture(c))
            late=ArtCanvas(context);render_local(late,layout.board,.12,cue,theme,.75,False)
            self.assertFalse(late.cells)
            later=ArtCanvas(context);render_local(later,layout.board,.09,cue,theme,.75,False)
            self.assertNotEqual(picture(c),picture(later))
        self.assertEqual(len(set(images)),6)

    def test_state_obeys_intensity_and_flash_settings_without_losing_low_geometry(self):
        from textris.art import game_layout
        from textris.theme_actions import render_state
        layout=game_layout(80,30)
        for theme in THEMES:
            context=RenderContext(80,30,layout.protected,True,False,1,layout.viewports)
            outputs=[]
            for intensity in (0,.25,1):
                c=ArtCanvas(context)
                render_state(c,.2,theme,state(danger=True,fever=True,combo=3,b2b=True,level=5),intensity=intensity,flash=False)
                self.assertTrue(all(ink.style not in (5,9,10,11) for ink in c.cells.values()))
                outputs.append(c)
            self.assertFalse(outputs[0].cells)
            self.assertTrue(outputs[1].cells)
            self.assertNotEqual(picture(outputs[1]),picture(outputs[2]),theme)
            self.assertLess(len(outputs[1].cells),len(outputs[2].cells),theme)
