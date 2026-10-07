"""실제 Windows App.run/input/curses와 Audio 감상 경로의 유한 통합 검사.

draw 이후 Windows 콘솔 입력 큐에 키를 넣는다. 제품 handle/tick/run, Audio 및 저장은
교체하지 않는다. 콘솔 버퍼·입력 큐·장치 재생의 증거이며 물리 청취 판정은 아니다.
"""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


class ConsoleInput:
    """PDCurses pushback의 key-code 표시 손실을 피하는 실제 콘솔 입력 레코드."""
    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes,self.wintypes=ctypes,wintypes
        class Character(ctypes.Union):
            _fields_=[('UnicodeChar',wintypes.WCHAR),('AsciiChar',wintypes.CHAR)]
        class KeyEvent(ctypes.Structure):
            _fields_=[('bKeyDown',wintypes.BOOL),('wRepeatCount',wintypes.WORD),
                      ('wVirtualKeyCode',wintypes.WORD),('wVirtualScanCode',wintypes.WORD),
                      ('uChar',Character),('dwControlKeyState',wintypes.DWORD)]
        class Event(ctypes.Union):
            _fields_=[('KeyEvent',KeyEvent),('padding',ctypes.c_byte*16)]
        class InputRecord(ctypes.Structure):
            _fields_=[('EventType',wintypes.WORD),('Event',Event)]
        self.Record=InputRecord
        assert ctypes.sizeof(InputRecord)==20 and ctypes.sizeof(KeyEvent)==16
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.kernel.GetStdHandle.argtypes=[wintypes.DWORD]
        self.kernel.GetStdHandle.restype=wintypes.HANDLE
        self.kernel.WriteConsoleInputW.argtypes=[wintypes.HANDLE,ctypes.POINTER(InputRecord),
                                                wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
        self.kernel.WriteConsoleInputW.restype=wintypes.BOOL
        self.user.VkKeyScanW.argtypes=[wintypes.WCHAR]; self.user.VkKeyScanW.restype=ctypes.c_short
        self.user.MapVirtualKeyW.argtypes=[wintypes.UINT,wintypes.UINT]
        self.user.MapVirtualKeyW.restype=wintypes.UINT
        self.handle=self.kernel.GetStdHandle(-10)

    def push(self,keys):
        import curses
        arrows={curses.KEY_UP:0x26,curses.KEY_DOWN:0x28,curses.KEY_LEFT:0x25,curses.KEY_RIGHT:0x27}
        records=(self.Record*(len(keys)*2))()
        for index,key in enumerate(keys):
            if isinstance(key,int):
                virtual=arrows[key]; char='\0'; modifiers=0x100
            else:
                char='\r' if key=='\n' else key
                mapping=self.user.VkKeyScanW(char)
                if mapping<0: raise ValueError(f'No native key mapping: {key!r}')
                virtual=mapping&0xff; modifiers=0x10 if mapping&0x100 else 0
            for offset,down in enumerate((True,False)):
                record=records[index*2+offset]; record.EventType=1
                event=record.Event.KeyEvent
                event.bKeyDown=down; event.wRepeatCount=1; event.wVirtualKeyCode=virtual
                event.wVirtualScanCode=self.user.MapVirtualKeyW(virtual,0)
                event.uChar.UnicodeChar=char; event.dwControlKeyState=modifiers
        if records:
            written=self.wintypes.DWORD()
            if not self.kernel.WriteConsoleInputW(self.handle,records,len(records),self.ctypes.byref(written)):
                raise self.ctypes.WinError(self.ctypes.get_last_error())
            if written.value!=len(records): raise RuntimeError('Partial console input write')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if sys.platform!='win32' or not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error('Run in an interactive Windows console with no concurrent audio probe.')
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    import curses
    from textris.audio import Audio
    from textris.storage import Store
    from textris.ui import App
    results=[]
    input_diagnostics=[]
    original_draw=App.draw

    def run(window):
        window.keypad(True); window.timeout(1000)
        native_input=ConsoleInput()
        for inject in (curses.unget_wch,curses.ungetch):
            curses.flushinp(); inject(curses.KEY_UP); key=window.get_wch()
            input_diagnostics.append(dict(method=inject.__name__,requested=curses.KEY_UP,
                                          observed=repr(key),type=type(key).__name__))
        curses.flushinp(); native_input.push([curses.KEY_UP])
        key=window.get_wch()
        input_diagnostics.append(dict(method='WriteConsoleInputW',requested=curses.KEY_UP,
                                      observed=repr(key),type=type(key).__name__))
        assert type(key) is int and key==curses.KEY_UP,input_diagnostics
        curses.flushinp()
        for height,columns in ((28,64),(40,120)):
            for mode in ('ascii','mono'):
                name=f'{columns}x{height}-{mode}'
                store=Store(out/name)
                store.settings.update(display_mode='ascii',color=mode!='mono',
                                      theme='mono' if mode=='mono' else 'cathedral')
                assert store.save()
                audio=Audio(store.directory,store.settings)
                curses.resize_term(height,columns)
                app=App(window,store,audio,seed=42)
                state=dict(name=name,stage=0,checks=[],frames=0,passed=False)
                began=time.monotonic(); stage_at=began

                def push(keys):
                    native_input.push(keys)
                    if keys: state['last_input']=[dict(value=repr(key),type=type(key).__name__) for key in keys]

                def advance(stage,keys=()):
                    nonlocal stage_at
                    state['stage']=stage; stage_at=time.monotonic()
                    push(keys)

                def capture(label):
                    h,w=window.getmaxyx()
                    frame='\n'.join(window.instr(y,0,w*4).decode(window.encoding,'replace') for y in range(h))
                    (out/f'{name}-{label}.txt').write_text(frame,encoding='utf-8')
                    assert frame.isascii(),label
                    state['checks'].append(label)
                    return frame

                def draw(current):
                    original_draw(current)
                    state['frames']+=1
                    state['screen']=current.screen
                    assert time.monotonic()-began<45,f'timeout: {state}'
                    assert current.session is None and current.game is None
                    assert not any(store.records.values()) and current.replays.list()==[]
                    music=audio.music_state; stage=state['stage']; age=time.monotonic()-stage_at
                    position=music['position']
                    if stage==0 and len(audio.catalog)==26:
                        state['backend']=audio.status
                        advance(1,['e',curses.KEY_UP,'\n'])
                    elif stage==1:
                        assert current.screen=='soundtrack' and len(current.soundtrack_tracks())==3
                        frame=capture('theme-filter')
                        assert 'Space:' in frame and 'Esc/Q:' in frame and 'BPM' in frame
                        advance(2,['\t'])
                    elif stage==2:
                        assert len(current.soundtrack_tracks())==8
                        assert 'Classic' in capture('classic-filter')
                        advance(3,['\t'])
                    elif stage==3:
                        assert len(current.soundtrack_tracks())==26
                        advance(4,[curses.KEY_DOWN]*25)
                    elif stage==4:
                        assert current.soundtrack_selection==25
                        capture('all-scrolled-last')
                        state['first_track']=current.soundtrack_tracks()[25]['id']
                        advance(5,['\n'])
                    elif stage==5 and music['mode']=='audition' and position>.15 and not music['buffering']:
                        assert music['track_id']==state['first_track']
                        capture('playing'); advance(6,[' '])
                    elif stage==6 and music['paused']:
                        state['paused_at']=position; advance(7)
                    elif stage==7 and age>.2:
                        assert abs(position-state['paused_at'])<.05
                        capture('paused'); advance(8,[' '])
                    elif stage==8 and not music['paused'] and position>state['paused_at']+.1:
                        state['before_seek']=position; advance(9,[curses.KEY_RIGHT])
                    elif stage==9 and not music['buffering'] and position>=state['before_seek']+4.9:
                        capture('seeked'); advance(10,['n'])
                    elif stage==10 and music['track_id']!=state['first_track'] and not music['buffering']:
                        state['next_track']=music['track_id']; capture('next'); advance(11,['p'])
                    elif stage==11 and music['track_id']==state['first_track'] and not music['buffering']:
                        capture('previous'); advance(12,['s','r','+','m'])
                    elif stage==12 and music['shuffle'] and music['repeat']:
                        assert not store.settings['sound'] and store.settings['music_volume']==.8
                        state['muted_at']=position; advance(13)
                    elif stage==13 and age>.2:
                        assert abs(position-state['muted_at'])<.05
                        capture('master-muted'); advance(14,['b','m'])
                    elif stage==14:
                        assert store.settings['sound'] and not store.settings['music']
                        state['music_off_at']=position; advance(15)
                    elif stage==15 and age>.2:
                        assert abs(position-state['music_off_at'])<.05
                        capture('music-off'); advance(16,['b'])
                    elif stage==16 and position>state['music_off_at']+.1:
                        curses.resize_term(12,45); advance(17)
                    elif stage==17:
                        state['small_at']=position; advance(18)
                    elif stage==18 and age>.2:
                        assert abs(position-state['small_at'])<.05
                        assert 'Resize terminal' in capture('small-suspended')
                        curses.resize_term(height,columns); advance(19)
                    elif stage==19 and position>state['small_at']+.1:
                        capture('resumed'); advance(20,['q'])
                    elif stage==20 and music['mode']=='game':
                        assert current.screen=='hub'
                        capture('back-extras'); advance(21,['q'])
                    elif stage==21:
                        assert current.screen=='menu'; advance(22,['q'])
                    elif stage==22:
                        assert not current.running

                App.draw=draw
                try:
                    app.run()
                    assert state['stage']==22
                    loaded=Store(store.directory); loaded.load()
                    assert loaded.settings['music_volume']==.8
                    assert loaded.settings['sound'] and loaded.settings['music']
                    assert not any(loaded.records.values()) and app.replays.list()==[]
                    state.update(passed=True,encoding=window.encoding,
                                 elapsed=round(time.monotonic()-began,3),no_games_or_replays=True)
                except BaseException as exc:
                    state.update(failure=repr(exc),screen=app.screen,music=audio.music_state)
                    raise
                finally:
                    App.draw=original_draw
                    audio.close()
                    results.append(state)
                    (out/'results.json').write_text(json.dumps(dict(cases=results,input_diagnostics=input_diagnostics,
                        scope='real App.run, WriteConsoleInputW key events, native curses, Audio callback, local storage; no physical keyboard/listening claim'),indent=2),encoding='utf-8')
    curses.wrapper(run)
    print(json.dumps(dict(passed=len(results),output=str(out))))
    return 0


if __name__=='__main__': raise SystemExit(main())
