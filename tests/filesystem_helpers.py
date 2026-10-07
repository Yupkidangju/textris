"""권한 부족을 제품 오류와 구분하되 실제 경로 경계 검사는 보존한다."""
import sys
import unittest


def symlink_or_skip(link, target, directory=False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        if sys.platform == 'win32' and exc.winerror == 1314:
            raise unittest.SkipTest('Windows symlink privilege unavailable (WinError 1314)') from exc
        raise
