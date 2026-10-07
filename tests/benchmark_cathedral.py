"""대성당 실 프레임 렌더링 비용. 터미널 전송은 별도 PTY 검증에서 측정."""
import json
import platform
from pathlib import Path
import tempfile
from time import perf_counter
from unittest.mock import patch

from textris.ui import App
from textris.effects import Effects
from textris.storage import Store
from tests.test_ui import Window,AudioStub


class RenderWindow(Window):
    def addstr(self,y,x,text,attr): pass


def main():
    root=Path(__file__).resolve().parent.parent
    profiles={}
    with tempfile.TemporaryDirectory(dir=root/'.antigravity/archive/cathedral') as temp:
        store=Store(Path(temp)); store.settings.update(language='en',theme='cathedral',shake=False)
        with patch.object(App,'_setup'),patch('curses.doupdate'):
            a=App(RenderWindow(40,120),store,AudioStub(),42); a.start(); a.screen='playing'; a.game.state='playing'
            for label,quality in (('full',1.),('adaptive',.7)):
                a.effects=Effects(); a.effects.configure(a.settings); a.effects.quality=quality
                samples=[]
                for i in range(360):
                    a.now=100+i/60
                    if i%120==30:
                        a.effects.trigger('clear',dict(count=4,rows=[18,19,20,21],spin=False,perfect=i>120,combo=4,points=4000),a.now)
                    start=perf_counter(); a.effects.update(a.now); a.draw()
                    samples.append((perf_counter()-start)*1000)
                profiles[label]=dict(frames=len(samples),mean_ms=round(sum(samples)/len(samples),3),
                    p95_ms=round(sorted(samples)[int(len(samples)*.95)-1],3),max_ms=round(max(samples),3))
    print(json.dumps(dict(python=platform.python_version(),size=[120,40],includes_terminal_io=False,profiles=profiles),indent=2))


if __name__=='__main__': main()
