"""CLI 진입점. curses wrapper가 모든 종료 경로에서 터미널을 복구한다."""
import argparse
from pathlib import Path
import subprocess
import sys

from . import __version__
from .audio import Audio, audio_path, command, find_backend, synthesize
from .i18n import tr
from .storage import Store
from .scenes import THEMES


def main(argv=None):
    parser = argparse.ArgumentParser(description='TEXTRIS — keyboard-driven terminal Tetris')
    parser.add_argument('--version',action='version',version=__version__)
    parser.add_argument('--language',choices=('ko','en'),help='display language')
    parser.add_argument('--no-sound',action='store_true',help='mute this session')
    parser.add_argument('--ascii',action='store_true',help='ASCII block glyphs')
    parser.add_argument('--theme',choices=THEMES,help='visual theme for this session')
    parser.add_argument('--seed',type=int,help='reproducible piece sequence')
    parser.add_argument('--data-dir',type=Path,help='settings, records and generated audio directory')
    parser.add_argument('--audio-check',action='store_true',help='synthesize and test audio playback, then exit')
    args = parser.parse_args(argv)
    project = Path(__file__).resolve().parent.parent
    is_bundled = getattr(sys, 'frozen', False) or not project.is_dir()
    default_dir = (Path.home() / '.textris-data') if is_bundled else (project / '.textris-data')
    directory = args.data_dir or default_dir
    lang = args.language or 'ko'
    if args.data_dir is None and not is_bundled and not directory.resolve().is_relative_to(project):
        print(tr(lang,'unsafe_data'),file=sys.stderr); return 1
    if not args.audio_check and (not sys.stdin.isatty() or not sys.stdout.isatty()):
        print(tr(lang,'need_terminal'),file=sys.stderr); return 1
    store = Store(directory); store.load()
    if args.language: store.settings['language'] = args.language
    lang = store.settings['language']
    # CLI의 임시 옵션은 종료 시 영구 설정을 덮어쓰지 않는다.
    original_sound,original_ascii = store.settings['sound'],store.settings['ascii']
    original_theme=store.settings['theme']
    if args.theme: store.settings['theme']=args.theme
    if args.no_sound: store.settings['sound'] = False
    if args.ascii: store.settings['ascii'] = True
    if args.audio_check:
        backend = find_backend()
        print(tr(lang,'backend_check',value=backend[0] if backend else tr(lang,'audio_bell')))
        if backend:
            try:
                path = audio_path(directory,'check.wav'); synthesize('tetris',path,.5)
                result = subprocess.run(command(backend,path),stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
                if result.returncode == 0:
                    return 0
            except (OSError,ValueError,subprocess.TimeoutExpired):
                pass
        print(tr(lang,'audio_check_failed')); return 1
    try:
        import curses
        from .ui import App
    except ImportError:
        print(tr(lang,'no_curses'),file=sys.stderr); return 1
    audio = Audio(directory,store.settings)
    try:
        curses.wrapper(lambda window: App(window,store,audio,args.seed).run())
    except KeyboardInterrupt:
        pass
    except curses.error:
        print(tr(lang,'terminal_error'),file=sys.stderr); return 1
    finally:
        audio.close()
        if args.no_sound:
            store.settings['sound'] = original_sound
        if args.ascii:
            store.settings['ascii'] = original_ascii
        if args.theme:
            store.settings['theme']=original_theme
        store.save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
