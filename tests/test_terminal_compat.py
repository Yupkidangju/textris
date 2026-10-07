"""영문 문자열, 안전한 최종 출력과 기존 저장 이행 경계."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from tests import test_ui


class TerminalCompatTests(unittest.TestCase):
    setUp=test_ui.UITests.setUp

    def test_all_product_messages_are_ascii_and_old_locale_is_english(self):
        from textris.i18n import STRINGS,tr
        self.assertEqual(set(STRINGS),{'en'})
        self.assertTrue(all(v.isascii() for v in STRINGS['en'].values()))
        self.assertEqual(tr('ko','settings'),'Settings')

    def test_saved_korean_is_migrated_without_losing_records(self):
        from textris.storage import Store
        row=dict(score=100,lines=1,level=1,seconds=2,completed=False,date='2026-10-07')
        self.store.path.write_text(json.dumps(dict(version=1,settings=dict(language='ko'),records=dict(marathon=[row]))))
        s=Store(self.store.directory);s.load()
        self.assertEqual(s.settings['language'],'en')
        self.assertEqual(s.records['marathon'],[row])

    def test_safe_mode_policy(self):
        from textris.terminal import needs_ascii
        for encoding in ('cp949','cp1252','ascii','unknown'):
            self.assertTrue(needs_ascii('linux',encoding))
        self.assertTrue(needs_ascii('win32','utf-8'))
        self.assertFalse(needs_ascii('linux','UTF-8'))
        self.assertFalse(needs_ascii('win32','cp949',unicode_requested=True))

    def test_ascii_output_covers_every_screen_and_dynamic_text(self):
        a=self.app;a.settings['ascii']=True;a.start();a.notice='save_read'
        with patch('curses.doupdate'):
            for theme in ('cathedral','cyberpunk','space','fire','crt','mono'):
                a.settings['theme']=theme
                for screen in ('menu','playing','ready','paused','help','settings','profiles','hub','records','result'):
                    a.screen=screen;a.help_return='playing';a.now=100
                    a.draw()
                    text=''.join(s for y,x,s in a.win.lines)
                    self.assertTrue(text.isascii(),(theme,screen))
        a.win.erase();a.put(1,1,'한글 → █⣿\a')
        self.assertTrue(a.win.lines[0][2].isascii())
        self.assertNotIn('\a',a.win.lines[0][2])

    def test_tick_never_beeps_when_audio_is_unavailable(self):
        a=self.app;a.audio.bells.put(True)
        with patch('curses.beep') as beep:
            a.handle('s');a.tick(.02)
            beep.assert_not_called()

    def test_encoding_failure_switches_to_safe_output(self):
        from tests.test_ui import Window
        class LegacyWindow(Window):
            encoding='utf-8'
            def addstr(self,y,x,text,attr):
                text.encode('cp1252')
                super().addstr(y,x,text,attr)
        a=self.app;a.terminal_ascii=False;a.settings['ascii']=False
        a.win=LegacyWindow(40,120)
        with patch('curses.doupdate'): a.draw()
        self.assertTrue(a.terminal_ascii)
        self.assertTrue(all(text.isascii() for _,_,text in a.win.lines))

    def test_safe_output_encodes_in_legacy_codepages(self):
        from textris.terminal import safe_ascii
        text=safe_ascii('TEXTRIS 한국어 日本語 ·→ █▌⣿ ╭─╮ \a')
        for encoding in ('ascii','cp949','cp1252','cp437','utf-8'):
            self.assertEqual(text.encode(encoding).decode(encoding),text)
        self.assertFalse(any(ord(char)<32 for char in text))
