"""저장 이행, 세션 우선순위와 실제 출력 실패 경계."""
import json
import unittest
from unittest.mock import patch

from tests import test_ui
from tests.test_ui import Window, AudioStub
from textris.storage import Store
from textris.ui import App


class DisplayModeTests(unittest.TestCase):
    setUp = test_ui.UITests.setUp

    def app_for(self, platform, encoding, mode='auto', override=None):
        self.store.settings.update(display_mode=mode, ascii=False)
        window = Window(40, 120)
        window.encoding = encoding
        with patch.object(App, '_setup'), patch('textris.ui.sys.platform', platform):
            return App(window, self.store, AudioStub(), display_override=override)

    def test_windows_auto_uses_tiles_even_with_korean_locale(self):
        for encoding in ('cp949', 'utf-8'):
            a = self.app_for('win32', encoding)
            self.assertFalse(a.ascii_mode)
            a.preview('O', 1, 1)
            self.assertTrue(any('██' in text for _, _, text in a.win.lines))

    def test_saved_selection_and_cli_override_priority(self):
        cases = [('auto', None, True), ('unicode', None, False),
                 ('ascii', None, True), ('ascii', 'unicode', False),
                 ('unicode', 'ascii', True)]
        for mode, override, expected in cases:
            with self.subTest(mode=mode, override=override):
                a = self.app_for('linux', 'ascii', mode, override)
                self.assertEqual(a.ascii_mode, expected)
                a.store.save()
                saved = Store(self.store.directory); saved.load()
                self.assertEqual(saved.settings['display_mode'], mode)

    def test_legacy_ascii_migration_preserves_records(self):
        row = dict(score=1, lines=0, level=1, seconds=2, completed=False, date='today')
        for legacy in (False, True):
            self.store.path.write_text(json.dumps(dict(version=1, settings=dict(ascii=legacy),
                records=dict(marathon=[row]))), encoding='utf-8')
            saved = Store(self.store.directory); saved.load()
            self.assertEqual(saved.settings['display_mode'], 'ascii' if legacy else 'auto')
            self.assertEqual(saved.records['marathon'], [row])
        self.store.path.write_text('{"version":1,"settings":{"display_mode":"bad","ascii":true}}')
        saved = Store(self.store.directory); saved.load()
        self.assertEqual(saved.settings['display_mode'], 'ascii')

    def test_settings_cycle_is_saved_and_visible(self):
        a = self.app_for('win32', 'cp949')
        a.screen = 'settings'; a.setting_selection = 3
        for mode in ('unicode', 'ascii', 'auto'):
            a.handle('\n')
            saved = Store(self.store.directory); saved.load()
            self.assertEqual(saved.settings['display_mode'], mode)
            a.win.erase(); a.draw_settings()
            self.assertIn(mode.upper(), ''.join(t for _, _, t in a.win.lines))

    def test_encoding_failure_overrides_unicode_for_following_frames(self):
        class LegacyWindow(Window):
            def addstr(self, y, x, text, attr):
                text.encode('ascii')
                super().addstr(y, x, text, attr)
        a = self.app_for('win32', 'utf-8', 'unicode', 'unicode')
        a.win = LegacyWindow(40, 120)
        with patch('curses.doupdate'):
            a.draw(); a.draw()
        self.assertTrue(a.ascii_mode)
        self.assertTrue(all(text.isascii() for _, _, text in a.win.lines))
        a.win.erase(); a.draw_settings()
        self.assertIn('fallback', ''.join(t for _, _, t in a.win.lines))
