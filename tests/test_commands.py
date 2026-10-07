from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CommandTests(unittest.TestCase):
    def test_help_and_version_without_terminal(self):
        for arg,text in [('--help','--audio-check'),('--version','1.0.0')]:
            result=subprocess.run([sys.executable,'-m','textris',arg],capture_output=True,text=True)
            self.assertEqual(result.returncode,0)
            self.assertIn(text,result.stdout)

    def test_noninteractive_launch_explains_requirement_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'data'
            result=subprocess.run([sys.executable,'-m','textris','--language','en','--data-dir',str(target)],
                                  capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertIn('interactive terminal',result.stderr)
            self.assertFalse(target.exists())


if __name__=='__main__': unittest.main()

class ThemeCommandTests(unittest.TestCase):
    def test_theme_option_lists_cathedral(self):
        result=subprocess.run([sys.executable,'-m','textris','--help'],capture_output=True,text=True)
        self.assertIn('--theme',result.stdout)
        self.assertIn('cathedral',result.stdout)
