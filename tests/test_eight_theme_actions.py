"""8테마 조작·상태의 가시성, 유한 잔상과 플레이어 경계를 검증한다."""
from dataclasses import replace
from types import SimpleNamespace
import unittest

from textris.art import ArtCanvas, RenderContext, battle_viewports, game_layout
from textris.art_director import Cue
from textris.theme_actions import render_local, render_state
from textris.themes import THEMES


ACTIONS = ('drop', 'lock', 'rotate', 'hold', 'focus', 'move')
STATES = ({'danger': True}, {'fever': True}, {'combo': 3}, {'b2b': True}, {'level': 5})


def geometry(canvas):
    return tuple(sorted((position, ink.glyph) for position, ink in canvas.cells.items()))


def visual_state(**values):
    data = dict(player_id='p1', danger=False, fever=False, combo=0, b2b=False, level=1)
    data.update(values)
    return SimpleNamespace(**data)


class RecordingCanvas(ArtCanvas):
    def __init__(self, context):
        super().__init__(context)
        self.writes = []

    def put(self, x, y, glyph, style=3, depth=0):
        self.writes.append(((round(x), round(y)), glyph, style, depth))
        super().put(x, y, glyph, style, depth)


class EightThemeActionTests(unittest.TestCase):
    def local(self, theme, action='rotate', phase=.55, quality=1, intensity=1,
              flash=False, size=(80, 30), power=1):
        layout = game_layout(*size)
        context = RenderContext(*size, layout.protected, True, False, quality, layout.viewports)
        canvas = RecordingCanvas(context)
        cue = Cue(action, 10, 11, power=power, coords=((4, 14), (6, 15)))
        render_local(canvas, layout.board, 10+phase, cue, theme, intensity, flash)
        return canvas

    def test_eight_themes_have_distinct_local_shapes_at_minimum_size_without_color(self):
        self.assertEqual(len(THEMES), 8)
        for action in ACTIONS:
            with self.subTest(action=action):
                images = [geometry(self.local(theme, action, quality=.25, size=(64, 28)))
                          for theme in THEMES]
                self.assertTrue(all(images))
                self.assertEqual(len(set(images)), 8)

    def test_eight_themes_have_distinct_state_shapes_at_minimum_size_without_color(self):
        layout = game_layout(64, 28)
        context = RenderContext(64, 28, layout.protected, True, False, .25, layout.viewports)
        for values in STATES:
            with self.subTest(state=values):
                images = []
                for theme in THEMES:
                    canvas = ArtCanvas(context)
                    render_state(canvas, .2, theme, visual_state(**values), flash=False)
                    images.append(geometry(canvas))
                self.assertTrue(all(images))
                self.assertEqual(len(set(images)), 8)

    def test_late_actions_keep_dim_wakes_behind_primary_without_unbounded_layers(self):
        for theme in THEMES:
            for action in ACTIONS:
                with self.subTest(theme=theme, action=action):
                    canvas = self.local(theme, action)
                    self.assertTrue(canvas.cells)
                    front = min(ink.depth for ink in canvas.cells.values())
                    wakes = [ink for ink in canvas.cells.values() if ink.depth > front]
                    self.assertTrue(wakes)
                    self.assertLessEqual(len({ink.depth for ink in wakes}), 2)
                    self.assertTrue(all(ink.style in (0, 1, 2, 6, 8, 15) for ink in wakes))
                    # 뒤늦게 그린 잔상이 주 문양을 흐리거나 다른 문자로 바꾸지 않는다.
                    primary = {position: (glyph, style) for position, glyph, style, depth
                               in canvas.writes if depth == front}
                    for position, expected in primary.items():
                        ink = canvas.cells[position]
                        self.assertEqual((ink.glyph, ink.style), expected)

    def test_wakes_do_not_spend_budget_before_either_primary_motif(self):
        for theme in THEMES:
            for action in ACTIONS:
                with self.subTest(theme=theme, action=action):
                    canvas = self.local(theme, action, power=10)
                    self.assertTrue(canvas.cells)
                    front = min(ink.depth for ink in canvas.cells.values())
                    first_wake = next((index for index, write in enumerate(canvas.writes)
                                       if write[3] > front), len(canvas.writes))
                    self.assertTrue(all(write[3] == front for write in canvas.writes[:first_wake]))
                    self.assertTrue(all(write[3] > front for write in canvas.writes[first_wake:]))
                    primary_x = [position[0] for position, _, _, depth in canvas.writes
                                 if depth == front]
                    bx = game_layout(80, 30).board[0]
                    self.assertTrue(any(x < bx for x in primary_x))
                    self.assertTrue(any(x > bx+22 for x in primary_x))

    def test_phase_derived_wakes_are_deterministic_and_do_not_mutate_cues(self):
        layout = game_layout(80, 30)
        context = RenderContext(80, 30, layout.protected, True, False, 1, layout.viewports)
        for theme in THEMES:
            cue = Cue('rotate', 10, 11, coords=((4, 8),))
            saved = replace(cue)
            frames = []
            for now in (10.55, 10.8, 10.15, 10.55):
                canvas = ArtCanvas(context)
                render_local(canvas, layout.board, now, cue, theme, 1, False)
                frames.append(canvas.cells)
            self.assertEqual(frames[0], frames[-1], theme)
            self.assertNotEqual(frames[0], frames[1], theme)
            self.assertEqual(cue, saved)

    def test_early_disabled_and_expired_actions_leave_no_wake(self):
        for theme in THEMES:
            early = self.local(theme, phase=0)
            self.assertTrue(early.cells)
            self.assertEqual(len({ink.depth for ink in early.cells.values()}), 1)
            for action in ACTIONS:
                for phase in (-.01, 1, 2):
                    self.assertFalse(self.local(theme, action, phase=phase).cells)
                self.assertFalse(self.local(theme, action, intensity=0).cells)

    def test_quality_reduces_actual_work_with_existing_brush_limits(self):
        for theme in THEMES:
            totals = []
            for quality in (.15, 1):
                total = 0
                for action in ACTIONS:
                    canvas = self.local(theme, action, quality=quality, intensity=10, power=10)
                    self.assertTrue(canvas.cells, (theme, action, quality))
                    self.assertLessEqual(len(canvas.writes), 180)
                    self.assertTrue(all(ink.glyph.isascii() for ink in canvas.cells.values()))
                    self.assertTrue(all(ink.style not in (5, 9, 10, 11)
                                        for ink in canvas.cells.values()))
                    total += len(canvas.writes)
                totals.append(total)
            self.assertLess(totals[0], totals[1], theme)
            canvas = RecordingCanvas(RenderContext(80, 30, ascii_mode=True))
            render_state(canvas, .2, theme, visual_state(danger=True, fever=True, combo=100,
                                                        b2b=True, level=100), flash=False)
            self.assertTrue(canvas.cells)
            self.assertLessEqual(len(canvas.writes), 260)

    def test_new_states_change_with_time_strength_and_recover_to_neutral(self):
        layout = game_layout(80, 30)
        context = RenderContext(80, 30, layout.protected, True, False, 1, layout.viewports)
        for theme in ('abyss', 'aurora'):
            for values in STATES:
                images = []
                for now, intensity in ((.2, 1), (.8, 1), (.2, .25), (.2, 0)):
                    canvas = ArtCanvas(context)
                    render_state(canvas, now, theme, visual_state(**values), intensity=intensity,
                                 flash=False)
                    images.append(geometry(canvas))
                    self.assertTrue(all(ink.style not in (5, 9, 10, 11)
                                        for ink in canvas.cells.values()))
                self.assertTrue(all(images[:3]), (theme, values))
                self.assertEqual(len(set(images[:3])), 3, (theme, values))
                self.assertFalse(images[3])
            neutral = ArtCanvas(context)
            render_state(neutral, .8, theme, visual_state())
            self.assertFalse(neutral.cells)

    def test_local_and_state_wakes_stay_in_owners_region_and_avoid_protected_cells(self):
        for size in ((64, 28), (120, 40)):
            views = battle_viewports(*size)
            protected = tuple(region for view in views for region in view.protected)
            context = RenderContext(*size, protected, True, False, 1, views)
            for view in views:
                for theme in THEMES:
                    with self.subTest(size=size, player=view.player_id, theme=theme):
                        canvas = RecordingCanvas(context)
                        for action in ACTIONS:
                            cue = Cue(action, 0, 1, coords=((4, 14),), player_id=view.player_id)
                            render_local(canvas, view.board, .55, cue, theme, 1, False)
                        render_state(canvas, .55, theme, visual_state(player_id=view.player_id,
                                     danger=True, fever=True, combo=3, b2b=True, level=5), flash=False)
                        self.assertTrue(canvas.cells)
                        for x, y in canvas.cells:
                            self.assertTrue(canvas.accepts(x, y))
                            self.assertTrue(any(a <= x < a+w and b <= y < b+h
                                                for a, b, w, h in view.effect_regions))

    def test_unknown_owner_or_empty_effect_regions_cannot_draw(self):
        views = battle_viewports(120, 40)
        for owners, player in ((views, 'missing'), ((replace(views[0], effect_regions=()),), 'p1')):
            context = RenderContext(120, 40, ascii_mode=True, viewports=owners)
            for theme in THEMES:
                canvas = ArtCanvas(context)
                cue = Cue('drop', 0, 1, coords=((4, 14),), player_id=player)
                render_local(canvas, views[0].board, .55, cue, theme, 1, False)
                render_state(canvas, .55, theme, visual_state(player_id=player, danger=True))
                self.assertFalse(canvas.cells, (player, theme))
