"""실제 Windows curses 버퍼에서 테마 성취·보드/HUD 보호를 대조한다."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if sys.platform!='win32' or not sys.stdin.isatty(): parser.error('interactive Windows console required')
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    import curses
    from textris.art import game_layout
    from textris.scenes import THEMES
    from textris.storage import Store
    from textris.ui import App
    from tests.test_ui import AudioStub
    from tests.test_theme_ceremonies import produce_ceremony, CEREMONIES
    results=[]

    def run(window):
        curses.resize_term(40,120)
        def buffer():
            return [window.instr(y,0,480).decode(window.encoding,'replace') for y in range(40)]
        protected=game_layout(120,40).protected
        for mode in ('unicode','ascii','mono'):
            for theme in THEMES:
                for event in CEREMONIES:
                    store=Store(out/'state')
                    store.settings.update(theme=theme,shake=False,flash=False,color=mode!='mono',
                                          display_mode='ascii' if mode=='ascii' else 'unicode')
                    app=App(window,store,AudioStub(),seed=42)
                    cue=produce_ceremony(app,event)
                    app.now=(cue.start+cue.end)/2
                    app.effects.director.major=None
                    app.draw(); idle=buffer()
                    app.effects.director.major=cue
                    app.draw(); active=buffer()
                    for x,y,w,h in protected:
                        for row in range(max(0,y),min(40,y+h)):
                            assert idle[row][max(0,x):min(119,x+w)]==active[row][max(0,x):min(119,x+w)],(mode,theme,event,row)
                    frame='\n'.join(active)
                    if mode=='ascii': assert frame.isascii()
                    assert 'SCORE' in frame and 'HOLD [C]' in frame and 'NEXT' in frame
                    (out/f'{mode}-{theme}-{event}.txt').write_text(frame,encoding='utf-8')
                    results.append(dict(mode=mode,theme=theme,event=event,protected=True,
                        encoding=window.encoding,sha256=hashlib.sha256(frame.encode()).hexdigest()))
    try:
        curses.wrapper(run)
    finally:
        (out/'results.json').write_text(json.dumps(dict(cases=results,total=len(results),
            scope='native curses buffers with real engine producers; no physical font or keyboard claim'),indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=len(results),output=str(out))))


if __name__=='__main__': main()
