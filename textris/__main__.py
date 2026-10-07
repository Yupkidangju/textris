"""CLI 진입점. curses wrapper가 모든 종료 경로에서 터미널을 복구한다."""
import argparse
from pathlib import Path
import sys

from . import __version__
from .audio import Audio, check_audio
from .i18n import tr
from .storage import Store
from .scenes import THEMES


def main(argv=None):
    parser = argparse.ArgumentParser(description='TEXTRIS - keyboard-driven terminal Tetris')
    parser.add_argument('--version',action='version',version=__version__)
    parser.add_argument('--language',choices=('ko','en'),help=argparse.SUPPRESS)
    parser.add_argument('--no-sound',action='store_true',help='mute this session')
    glyphs=parser.add_mutually_exclusive_group()
    glyphs.add_argument('--ascii',action='store_true',help='ASCII-safe text and art')
    glyphs.add_argument('--unicode',action='store_true',help='enable Unicode art (requires a suitable terminal font)')
    parser.add_argument('--theme',choices=THEMES,help='visual theme for this session')
    parser.add_argument('--seed',type=int,help='reproducible piece sequence')
    parser.add_argument('--data-dir',type=Path,help='settings, records and generated audio directory')
    parser.add_argument('--audio-check',action='store_true',help='test packaged audio playback and report output state, then exit')
    parser.add_argument('--verify-audio-assets',action='store_true',help='verify packaged soundtrack/effect inventory and hashes, then exit')
    args = parser.parse_args(argv)
    if args.verify_audio_assets:
        from .asset_check import verify_audio_assets
        import json
        try:
            print(json.dumps(verify_audio_assets(),sort_keys=True)); return 0
        except ValueError as exc:
            print(str(exc),file=sys.stderr); return 1
    project = Path(__file__).resolve().parent.parent
    is_bundled = getattr(sys, 'frozen', False) or not project.is_dir()
    default_dir = (Path.home() / '.textris-data') if is_bundled else (project / '.textris-data')
    directory = args.data_dir or default_dir
    lang = 'en'
    if args.data_dir is None and not is_bundled and not directory.resolve().is_relative_to(project):
        print(tr(lang,'unsafe_data'),file=sys.stderr); return 1
    if not args.audio_check and (not sys.stdin.isatty() or not sys.stdout.isatty()):
        print(tr(lang,'need_terminal'),file=sys.stderr); return 1
    store = Store(directory); store.load()
    store.settings['language'] = 'en'
    lang = store.settings['language']
    # CLI의 임시 옵션은 종료 시 영구 설정을 덮어쓰지 않는다.
    original_sound = store.settings['sound']
    original_theme=store.settings['theme']
    if args.theme: store.settings['theme']=args.theme
    if args.no_sound: store.settings['sound'] = False
    display_override = 'ascii' if args.ascii else 'unicode' if args.unicode else None
    if args.audio_check:
        result = check_audio(directory,store.settings)
        print(tr(lang,'backend_check',value=result['backend'] or tr(lang,'audio_silent')))
        print(tr(lang,'audio_check_app',muted=result['app_muted'],volume=round(result['app_volume']*100)))
        output=result['os_output']
        print(tr(lang,'audio_check_os',muted=output['master_muted'],volume=round(output['master_volume']*100))
              if output['available'] else tr(lang,'audio_check_os_unknown'))
        print(tr(lang,'audio_check_completion',value='PASS' if result['backend_completed'] else 'FAIL'))
        print(tr(lang,'audio_check_listening'))
        if result['backend_completed']: return 0
        print(tr(lang,'audio_check_failed')); return 1
    try:
        import curses
        from .ui import App
    except ImportError:
        print(tr(lang,'no_curses'),file=sys.stderr); return 1
    audio = Audio(directory,store.settings)
    try:
        curses.wrapper(lambda window: App(window,store,audio,args.seed,display_override=display_override).run())
    except KeyboardInterrupt:
        pass
    except curses.error:
        print(tr(lang,'terminal_error'),file=sys.stderr); return 1
    finally:
        audio.close()
        if args.no_sound:
            store.settings['sound'] = original_sound
        if args.theme:
            store.settings['theme']=original_theme
        store.save()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
