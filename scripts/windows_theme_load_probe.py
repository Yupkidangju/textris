"""유한 시간 실제 curses 출력 부하. 입력/음원 검사는 별도 도구의 영역이다."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))


def main():
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=120.)
    p.add_argument('--adaptive',action='store_true',help='use the same quality policy as App.run')
    args=p.parse_args()
    if sys.platform!='win32' or not sys.stdin.isatty(): p.error('interactive Windows console required')
    if not 6<=args.seconds<=600: p.error('seconds must be 6..600')
    out=args.output.resolve(); out.mkdir(parents=True,exist_ok=False)
    import curses
    from textris.scenes import THEMES
    from textris.ui import App
    from textris.storage import Store
    from tests.test_ui import AudioStub
    from tests.test_theme_ceremonies import CEREMONIES,produce_ceremony
    report=dict(seconds=args.seconds,adaptive=args.adaptive,scope='native curses drawing/output with real engine-produced fixtures; no physical keyboard/font or audio claim',cases=[])
    def run(window):
        curses.resize_term(40,120)
        for theme in THEMES:
            store=Store(out/'state'); store.settings.update(theme=theme,display_mode='unicode',shake=False,flash=False)
            app=App(window,store,AudioStub(),42)
            start=time.monotonic(); cycle=start; frames=0; timings=[]; next_event=0
            while time.monotonic()-start<args.seconds/len(THEMES):
                now=time.monotonic()
                if frames==0 or now-cycle>=2:
                    quality=app.effects.quality
                    cue=produce_ceremony(app,CEREMONIES[next_event%6]); next_event+=1; cycle=now
                    # fixture는 새 게임을 만들지만 실제 연속 사건의 품질 정책은 이어 간다.
                    if args.adaptive: app.effects.quality=quality
                    app.effects.fever_until=110; app.effects.combo=5; app.effects.b2b=True
                app.now=100+(now-cycle)
                if frames%7==0:
                    app.effects.trigger(('move','rotate','hold','drop')[frames//7%4],
                        dict(cells=((4,8),(5,8),(4,9),(5,9)),distance=9),app.now)
                checksum=app.session.checksum()
                begin=time.perf_counter(); app.draw(); timings.append((time.perf_counter()-begin)*1000)
                if args.adaptive: app.effects.observe_frame_cost(timings[-1]/1000)
                assert checksum==app.session.checksum()
                assert len(app.effects.director.local)<=8
                if frames%30==0:
                    frame='\n'.join(window.instr(y,0,480).decode('utf-8','strict') for y in range(40))
                    assert 'SCORE' in frame and 'HOLD [C]' in frame and 'NEXT' in frame
                frames+=1
                time.sleep(max(0,1/60-(time.perf_counter()-begin)))
            ordered=sorted(timings)
            report['cases'].append(dict(theme=theme,frames=frames,elapsed=round(time.monotonic()-start,3),
                mean_ms=round(sum(timings)/frames,3),p95_ms=round(ordered[int(frames*.95)-1],3),
                max_ms=round(max(timings),3),final_quality=round(app.effects.quality,3),checksum_unchanged=True,includes_terminal_output=True))
            (out/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    curses.wrapper(run)
    assert len(report['cases'])==len(THEMES)
    print(json.dumps(dict(passed=len(THEMES),frames=sum(c['frames'] for c in report['cases']),output=str(out))))


if __name__=='__main__': main()
