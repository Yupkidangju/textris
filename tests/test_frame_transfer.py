"""변경 셀 전송의 화면 보존과 넓은 문자·오류 복구."""
from pathlib import Path
import tempfile
import curses
import unittest
from unittest.mock import patch
from tests.capture_cathedral import ColorWindow
from tests.test_ui import AudioStub
from textris.storage import Store
from textris.ui import App
from textris.i18n import STRINGS


class CountingWindow(ColorWindow):
    def __init__(self,*args): self.writes=0; self.fail=False; super().__init__(*args)
    def addstr(self,*args):
        self.writes+=1
        if self.fail:
            self.fail=False; raise UnicodeError('probe output encoding')
        super().addstr(*args)


class FrameTransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.win=CountingWindow(28,64)
        with patch.object(App,'_setup'):
            self.app=App(self.win,Store(Path(self.tmp.name)),AudioStub(),42,unicode_art=True)
        self.app.now=100; self.app.art_epoch=90
        translations=patch.dict(STRINGS['en'],{'probe_notice':'temporary notice','probe_wide':'文','probe_narrow':'x'})
        translations.start(); self.addCleanup(translations.stop)

    def draw(self):
        with patch('curses.doupdate'): self.app.draw()

    def test_unchanged_frame_keeps_pixels_without_native_writes(self):
        self.draw(); before=[row[:] for row in self.win.grid]; self.win.writes=0
        self.draw()
        self.assertEqual(self.win.grid,before); self.assertEqual(self.win.writes,0)

    def test_removed_overlay_restores_the_complete_underlying_frame(self):
        self.draw(); baseline=[row[:] for row in self.win.grid]
        self.app.notice='probe_notice'; self.draw()
        self.assertNotEqual(self.win.grid,baseline)
        self.app.notice=''; self.draw()
        self.assertEqual(self.win.grid,baseline)

    def test_wide_overlay_replaced_by_narrow_text_clears_continuation(self):
        self.app.notice='probe_wide'; self.draw()
        self.app.notice='probe_narrow'; self.draw()
        self.assertEqual(self.win.grid[27][31][0],'x')
        self.assertNotEqual(self.win.grid[27][32][0],'')
        self.assertNotIn('文',''.join(ch for row in self.win.grid for ch,attr in row))

    def test_output_error_and_resize_force_a_complete_safe_frame(self):
        self.win.fail=True; self.draw()
        self.assertTrue(self.app.terminal_ascii)
        self.win.writes=0; self.draw(); self.assertGreater(self.win.writes,0)
        self.win.size=(30,80); self.win.erase(); self.draw()
        self.assertEqual(len(self.win.grid),30)
        self.assertTrue(all(ch.isascii() for row in self.win.grid for ch,attr in row))

    def test_native_resize_event_repaints_even_when_dimensions_are_unchanged(self):
        self.app.fx_enabled=False; self.draw()
        baseline=[row[:] for row in self.win.grid]
        self.win.erase(); pending=[curses.KEY_RESIZE]
        def get_key():
            if pending: return pending.pop()
            self.app.running=False; raise curses.error()
        self.win.get_wch=get_key
        with patch('curses.doupdate'): self.app.run()
        self.assertEqual(self.win.grid,baseline)


if __name__=='__main__': unittest.main()
