"""캐시된 구형 모듈이나 빠진 활성 모듈을 빌드 성공으로 인정하지 않는다."""
from contextlib import redirect_stderr,redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from scripts import build


class PackageInventoryTests(unittest.TestCase):
    def check_archive(self,entries):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); package=root/'textris'; package.mkdir()
            (package/'__init__.py').write_text('')
            (package/'active.py').write_text('VALUE = 1\n')
            archive=root/'candidate.pyz'
            with zipfile.ZipFile(archive,'w') as stream:
                for name in entries: stream.writestr(name,'')
            with patch.object(build,'ROOT_DIR',root),redirect_stderr(StringIO()),redirect_stdout(StringIO()):
                return build.verify_module_inventory(archive,True)

    def test_current_inventory_passes(self):
        self.assertTrue(self.check_archive(['textris/__init__.py','textris/active.py']))

    def test_missing_active_module_fails(self):
        self.assertFalse(self.check_archive(['textris/__init__.py']))

    def test_stale_removed_module_fails(self):
        self.assertFalse(self.check_archive(['textris/__init__.py','textris/active.py','textris/removed.py']))

    def native_check(self,uv=False,returncode=0):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'textris').mkdir()
            (root/'textris'/'__init__.py').write_text('')
            (root/'textris'/'active.py').write_text('')
            frontend=root/'pyinstaller.exe'; viewer=root/'pyi-archive_viewer.exe'; viewer.touch()
            command=['uv','run','--with','pyinstaller','pyinstaller'] if uv else [str(frontend)]
            result=SimpleNamespace(returncode=returncode,stdout=' textris\n textris.active\n',stderr='probe failure')
            with patch.object(build,'ROOT_DIR',root),patch.object(build,'get_pyinstaller_cmd',return_value=command), \
                 patch.object(build.subprocess,'run',return_value=result) as run, \
                 redirect_stderr(StringIO()),redirect_stdout(StringIO()):
                valid=build.verify_module_inventory(root/'candidate.exe')
            return valid,run.call_args,command,viewer

    def test_path_pyinstaller_uses_its_own_archive_viewer(self):
        valid,call,_,viewer=self.native_check()
        self.assertTrue(valid)
        self.assertEqual(call.args[0][0],str(viewer))

    def test_uv_pyinstaller_uses_same_isolated_environment(self):
        valid,call,command,_=self.native_check(uv=True)
        self.assertTrue(valid)
        self.assertEqual(call.args[0][:5],command[:-1]+['pyi-archive_viewer'])

    def test_failed_native_inspection_does_not_pass(self):
        valid,_,_,_=self.native_check(uv=True,returncode=1)
        self.assertFalse(valid)


if __name__=='__main__':unittest.main()
