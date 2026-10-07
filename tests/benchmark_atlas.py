"""전체 테마와 갤러리 App.draw 비용. 입력/터미널 전송 시간은 포함하지 않는다."""
import json
import platform
import tempfile
from pathlib import Path
from time import perf_counter
from unittest.mock import patch
from textris.ui import App
from textris.storage import Store
from textris.effects import Effects
from textris.scenes import THEMES,BACKGROUNDS,EFFECTS
from tests.test_ui import AudioStub
from tests.benchmark_cathedral import RenderWindow


def measure(a,frames,step):
    values=[]
    for i in range(frames):
        step(i)
        start=perf_counter();a.draw();values.append((perf_counter()-start)*1000)
    return dict(mean_ms=round(sum(values)/len(values),2),p95_ms=round(sorted(values)[int(len(values)*.95)-1],2),max_ms=round(max(values),2))


def main():
    result=dict(python=platform.python_version(),size=[120,40],includes_terminal_io=False,themes={},gallery={})
    with tempfile.TemporaryDirectory() as temp,patch.object(App,'_setup'),patch('curses.doupdate'):
        store=Store(Path(temp));store.settings.update(shake=False)
        a=App(RenderWindow(40,120),store,AudioStub(),42,unicode_art=True)
        for theme in THEMES:
            a.settings['theme']=theme;a.start();a.screen='playing';a.game.state='playing'
            def step(i):
                a.now=100+i/60
                if i%120==30: a.effects.trigger('clear',dict(count=4,rows=[18,19,20,21],combo=4,perfect=i>120),a.now)
            result['themes'][theme]=measure(a,240,step)
        a.open_gallery()
        for i,name in enumerate(BACKGROUNDS+EFFECTS):
            a.effects=Effects();a.now=100;a.gallery_index=i;a.gallery_trigger()
            result['gallery'][('background/' if i<len(BACKGROUNDS) else 'effect/')+name]=measure(a,60,lambda j:setattr(a,'now',100+j/60))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
