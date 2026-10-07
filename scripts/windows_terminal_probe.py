"""실제 Windows curses wrapper/run/input 큐를 유한 시나리오로 검증한다.

draw 후 화면을 관찰하고 다음 키만 입력 큐에 넣는다. App.run/handle/tick은 교체하지
않는다. 물리 키보드/Windows Terminal 폰트 검사가 아닌 콘솔 버퍼 통합 검사다.
"""
import argparse
import ctypes
import json
import locale
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sound',action='store_true',help='exercise the real audio engine during game input')
    args=parser.parse_args()
    if sys.platform!='win32' or not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error('Run this probe in an interactive Windows console.')
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    import curses
    from textris.__main__ import main as cli
    from textris.ui import App
    from textris.storage import Store
    from textris.art import Palette
    results=[]
    original_draw=App.draw

    def push(keys):
        for key in reversed(keys): curses.unget_wch(key)

    cases=[('default','auto',[],False),('unicode','ascii',['--unicode'],False),
           ('ascii','unicode',['--ascii'],True),('saved-unicode','unicode',[],False),
           ('saved-ascii','ascii',[],True)]
    for name,saved,flags,expected_ascii in cases:
        directory=output/name
        store=Store(directory); store.settings.update(display_mode=saved,ascii=saved=='ascii'); store.save()
        state=dict(name=name,saved=saved,flags=flags,frames=0,checks=[],stage=0)
        began=time.monotonic()

        def capture(app,label):
            h,w=app.win.getmaxyx()
            frame='\n'.join(app.win.instr(y,0,w*4).decode(app.win.encoding,'replace') for y in range(h))
            (output/f'{name}-{label}.txt').write_text(frame,encoding='utf-8')
            state['checks'].append(label)
            return frame

        def draw(app):
            if state['frames']==0:
                curses.resize_term(40,120)
                if args.sound:
                    original_play=app.audio.play
                    state['requested_cues']=[]
                    def observed_play(cue):
                        state['requested_cues'].append(cue)
                        original_play(cue)
                    app.audio.play=observed_play
            original_draw(app)
            state['frames']+=1
            if time.monotonic()-began>18: raise AssertionError(f'timeout {name}: {state}')
            stage=state['stage']
            if stage==0:
                frame=capture(app,'menu')
                assert app.screen=='menu' and app.ascii_mode==expected_ascii
                palette=Palette(); palette.setup(8,8)
                assert all(palette.attr(i)&curses.A_COLOR==curses.color_pair(i-15) for i in (16,17))
                state.update(encoding=app.win.encoding,ascii_mode=app.ascii_mode,
                    palette_native_match=True,input_cp=ctypes.windll.kernel32.GetConsoleCP(),
                    output_cp=ctypes.windll.kernel32.GetConsoleOutputCP())
                push('sss\n'); state['stage']=1
            elif stage==1:
                assert app.screen=='settings'
                frame=capture(app,'settings')
                assert saved.upper() in frame
                if name=='default':
                    push('sssd'); state['stage']='cycle-unicode'
                else:
                    push('\x1bwww\n'); state['stage']=2
            elif stage in ('cycle-unicode','cycle-ascii','cycle-auto'):
                expected=stage.split('-')[1]
                assert app.settings['display_mode']==expected
                assert app.ascii_mode==(expected=='ascii')
                capture(app,stage)
                persisted=Store(directory); persisted.load()
                assert persisted.settings['display_mode']==expected
                if expected=='auto':
                    push('\x1bwww\n'); state['stage']=2
                else:
                    push('d'); state['stage']='cycle-ascii' if expected=='unicode' else 'cycle-auto'
            elif stage==2 and app.screen=='playing':
                frame=capture(app,'playing')
                state.update(block_ascii=frame.count('[]'),block_unicode=frame.count('██'),ghost_unicode=frame.count('░░'))
                assert (frame.count('[]')>0) if expected_ascii else (frame.count('██')>0 and frame.count('░░')>0)
                assert frame.isascii() if expected_ascii else True
                state['before_x']=app.game.active.x
                push('a'); state['stage']=3
            elif stage==3:
                assert app.game.active.x==state['before_x']-1
                state['checks'].append('native-left-input')
                push('cxz '); state['stage']=4
            elif stage==4:
                assert app.game.held is not None and app.game.score>0
                frame=capture(app,'hold-drop')
                assert 'HOLD [C]' in frame and 'NEXT' in frame and 'SCORE' in frame
                push('p'); state['stage']=5
            elif stage==5:
                assert app.screen=='paused'
                state['frozen_time']=app.game.elapsed
                push('h'); state['stage']=6
            elif stage==6:
                assert app.screen=='help' and app.game.elapsed==state['frozen_time']
                capture(app,'help')
                push('\x1bp'); state['stage']=7
            elif stage==7:
                assert app.screen=='playing'
                curses.resize_term(12,45)
                state['frozen_time']=app.game.elapsed
                state['stage']=8
            elif stage==8:
                frame=capture(app,'small')
                assert 'Resize terminal' in frame and app.game.elapsed==state['frozen_time']
                curses.resize_term(40,120)
                state['stage']=9
            elif stage==9:
                frame=capture(app,'resumed')
                assert 'SCORE' in frame
                push('rn'); state['stage']=10
            elif stage==10:
                assert app.screen=='playing'
                push('ry'); state['stage']=11
            elif stage==11:
                assert app.screen=='ready' and app.game.score==0
                capture(app,'restarted')
                if args.sound:
                    state['audio']=dict(app.audio.diagnostics)
                    assert state['audio']['completed_effects']>0
                    assert state['audio']['failure_count']==0
                    assert {'move','rotate','hold','drop','lock'}<=set(state['requested_cues'])
                push('qy'); state['stage']=12

        App.draw=draw
        try:
            mute=[] if args.sound else ['--no-sound']
            state['exit_code']=cli([*mute,'--seed','42','--data-dir',str(directory),*flags])
            assert state['stage']==12 and state['exit_code']==0
            reloaded=Store(directory); reloaded.load()
            assert reloaded.settings['display_mode']==saved
            assert reloaded.settings['sound'] is True
            state['checks'].append('saved-selection-and-sound-preserved')
            state['passed']=True
        finally:
            App.draw=original_draw
            results.append(state)
            (output/'results.json').write_text(json.dumps(dict(platform=sys.platform,
                locale=locale.getpreferredencoding(False),python=sys.version,cases=results),indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=len(results),output=str(output))))
    return 0


if __name__=='__main__': raise SystemExit(main())
