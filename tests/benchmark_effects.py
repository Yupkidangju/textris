"""실제 터미널 전송을 제외한 최대 연출 렌더링 비용: python3 -m tests.benchmark_effects."""
import json
from pathlib import Path
import platform
import tempfile
import time
from unittest.mock import patch
from tests.test_ui import Window,AudioStub
from textris.ui import App
from textris.effects import Effects
from textris.storage import Store
from textris.scenes import BACKGROUNDS


def main():
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
        store=Store(Path(directory)); store.load()
        samples=[]; per_scene={}
        with patch.object(App,'_setup'),patch('curses.doupdate'):
            app=App(Window(40,120),store,AudioStub(),42); app.start(); app.screen='playing'
            for scene in BACKGROUNDS:
                app.effects=Effects(); app.effects.configure(app.settings); app.effects.scene=scene
                data=dict(rows=[18,19,20,21],count=4,spin=False,combo=8,b2b=True,perfect=True,points=4000)
                for _ in range(5): app.effects.trigger('clear',data,100)
                times=[]
                for i in range(30):
                    app.now=100+i/60
                    start=time.perf_counter(); app.effects.update(app.now); app.draw()
                    times.append((time.perf_counter()-start)*1000)
                samples.extend(times); per_scene[scene]=round(sum(times)/len(times),3)
        result=dict(python=platform.python_version(),size=[120,40],frames=len(samples),
                    mean_ms=round(sum(samples)/len(samples),3),max_ms=round(max(samples),3),
                    scenes=per_scene,includes_terminal_io=False)
        print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
