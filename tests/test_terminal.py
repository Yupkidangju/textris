import json
from pathlib import Path
import tempfile
import termios
import unittest
from .terminal_harness import Terminal


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)

    def launch(self,*arguments):
        terminal=Terminal(Path(self.tmp.name),arguments)
        self.addCleanup(terminal.close)
        return terminal

    def assertScreen(self,terminal,text):
        self.assertIn(text,terminal.screen.text(),terminal.screen.text())
        self.assertIsNone(terminal.process.poll())

    def test_real_keyboard_play_pause_help_restart_resize_and_quit(self):
        t=self.launch('--language','en','--no-sound','--ascii','--seed','42')
        self.assertScreen(t,'T E X T R I S')
        t.send('\n'); self.assertScreen(t,'READY')
        t.pump(3.1); self.assertScreen(t,'SCORE')
        t.send('cxzadss '); self.assertScreen(t,'HOLD [C]')
        t.send('p'); self.assertScreen(t,'PAUSED')
        t.send('h'); self.assertScreen(t,'Controls')
        t.send('\x1b'); self.assertScreen(t,'PAUSED')
        t.send('p'); t.send('r'); self.assertScreen(t,'Restart this game?')
        t.send('n'); self.assertScreen(t,'SCORE')
        t.send('r'); t.send('y'); self.assertScreen(t,'READY')
        t.resize(12,45); self.assertScreen(t,'Resize terminal')
        t.pump(.2); t.resize(28,64); self.assertScreen(t,'READY')
        t.pump(3.1)
        t.send('q'); self.assertScreen(t,'Quit this game?')
        t.send('y'); t.process.wait(timeout=3); t.pump(.1)
        self.assertEqual(t.process.returncode,0)
        self.assertNotIn(b'Traceback',t.raw)
        after=termios.tcgetattr(t.slave)
        self.assertEqual(after[3] & (termios.ECHO|termios.ICANON), t.original[3] & (termios.ECHO|termios.ICANON))
        self.assertIn(b'\x1b[?1049l',t.raw)
        save=json.loads((Path(self.tmp.name)/'records.json').read_text())
        self.assertTrue(save['settings']['sound'])
        self.assertFalse(save['settings']['ascii'])

    def test_showcase_live_animation_resize_toggle_exit_without_records(self):
        t=self.launch('--language','en','--no-sound')
        self.assertScreen(t,'V: FX SHOWCASE')
        t.send('v',wait=.1)
        self.assertScreen(t,'FX SHOWCASE')
        self.assertScreen(t,'HARD DROP / IMPACT')
        before=t.screen.text()
        t.pump(.25)
        self.assertNotEqual(before,t.screen.text())
        t.pump(1.35)
        self.assertScreen(t,'SINGLE')
        t.send('f')
        self.assertScreen(t,'SCORE')
        t.resize(12,40); self.assertScreen(t,'Resize terminal')
        t.resize(28,64); self.assertScreen(t,'FX SHOWCASE')
        t.send('f'); t.send(' ')
        self.assertScreen(t,'FX SHOWCASE')
        t.send('v'); self.assertScreen(t,'V: FX SHOWCASE')
        t.send('q'); t.process.wait(timeout=3)
        data=json.loads((Path(self.tmp.name)/'records.json').read_text())
        self.assertFalse(any(data['records'].values()))
        self.assertEqual(t.process.returncode,0)
        self.assertNotIn(b'Traceback',t.raw)

    def test_settings_records_korean_and_persistence(self):
        t=self.launch('--language','en')
        t.send('sss\n'); self.assertScreen(t,'Settings')
        t.send('\n'); self.assertScreen(t,'설정')
        t.send('s\n'); self.assertScreen(t,'끔')
        t.send('\x1b'); t.send('s\n'); self.assertScreen(t,'최고 기록')
        t.send('\x1bOC'); self.assertScreen(t,'스프린트')
        t.send('\x1b'); t.send('q'); t.process.wait(timeout=3)
        data=json.loads((Path(self.tmp.name)/'records.json').read_text())
        self.assertEqual(data['settings']['language'],'ko')
        self.assertFalse(data['settings']['sound'])
        self.assertEqual(t.process.returncode,0)

    def test_gameover_saves_and_results_can_restart(self):
        t=self.launch('--language','en','--no-sound','--seed','42')
        t.send('\n'); t.pump(3.1)
        t.send(' '*30,wait=1)
        self.assertScreen(t,'GAME OVER')
        data=json.loads((Path(self.tmp.name)/'records.json').read_text())
        self.assertEqual(len(data['records']['marathon']),1)
        self.assertGreater(data['records']['marathon'][0]['score'],0)
        t.send('\n'); self.assertScreen(t,'READY')
        t.send('q'); t.send('y'); t.process.wait(timeout=3)
        self.assertEqual(t.process.returncode,0)


if __name__=='__main__': unittest.main()

class ExpansionTerminalTests(unittest.TestCase):
    setUp=TerminalTests.setUp
    launch=TerminalTests.launch
    assertScreen=TerminalTests.assertScreen
    def test_gallery_profiles_boss_auto_and_replay_navigation(self):
        t=self.launch('--language','en','--no-sound','--seed','42')
        t.send('e'); self.assertScreen(t,'Extras')
        t.send('\n'); self.assertScreen(t,'FX Gallery')
        t.send(' '*2+'ad'); self.assertScreen(t,'FX Gallery')
        t.send('\x1b'); t.send('s\n'); self.assertScreen(t,'Effects & themes')
        t.send('d'); self.assertScreen(t,'Cyberpunk')
        t.send('\x1b'); t.send('s\n'); self.assertScreen(t,'READY')
        t.pump(3.1); self.assertScreen(t,'BOSS HP')
        t.send('p'); self.assertScreen(t,'PAUSED')
        t.send('p'); t.send(' '*30,wait=.8); self.assertScreen(t,'GAME OVER')
        t.send('a'); self.assertScreen(t,'Session analysis')
        t.send('\x1b'); t.send('\x1b'); t.send('e'); t.send('sss\n')
        self.assertScreen(t,'Replays')
        t.send('\n'); self.assertScreen(t,'REPLAY')
        t.send('p'); t.send('\x1bOC'); t.send('\x1bOD'); t.send('a')
        self.assertScreen(t,'Session analysis')
        t.send('\x1b'); t.send('\x1b'); t.send('\x1b'); t.send('s\n')
        self.assertScreen(t,'AUTO EXHIBITION')
        t.send('p'); t.resize(12,40); self.assertScreen(t,'Resize terminal')
        t.resize(28,64); self.assertScreen(t,'AUTO EXHIBITION')
        t.send('\x1b'); t.send('\x1b'); t.send('q'); t.process.wait(timeout=3)
        self.assertEqual(t.process.returncode,0)
        self.assertNotIn(b'Traceback',t.raw)
        data=json.loads((Path(self.tmp.name)/'records.json').read_text())
        self.assertEqual(len(data['records']['boss']),1)
        self.assertFalse(data['records']['marathon'])

class CathedralTerminalTests(unittest.TestCase):
    setUp=TerminalTests.setUp
    def test_session_theme_restores_existing_choice_and_terminal(self):
        from textris.storage import Store
        store=Store(Path(self.tmp.name)); store.settings['theme']='fire'; store.save()
        t=Terminal(Path(self.tmp.name),('--theme','cathedral','--language','en','--no-sound'),rows=40,cols=120)
        self.addCleanup(t.close)
        self.assertIn('C O S M I C',t.screen.text())
        t.send('v'); t.pump(.25)
        self.assertIn('HOLD [C]',t.screen.text())
        self.assertTrue(any(byte>127 for byte in t.raw))
        t.send('v'); t.send('q'); t.process.wait(timeout=3)
        self.assertEqual(t.process.returncode,0)
        self.assertEqual(json.loads(store.path.read_text())['settings']['theme'],'fire')
        after=termios.tcgetattr(t.slave)
        self.assertEqual(after[3] & (termios.ECHO|termios.ICANON),t.original[3] & (termios.ECHO|termios.ICANON))
