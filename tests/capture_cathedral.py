"""실제 App.draw의 컬러 셀을 HTML로 보존. --png는 설치된 Pillow를 검토용으로 사용."""
import argparse
import curses
import html
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from textris.ui import App, cell_width
from textris.art import COLORS, BACKS
from textris.effects import Effects
from textris.engine import Piece
from textris.storage import Store
from tests.test_ui import AudioStub

BASE=((0,0,0),(205,49,49),(13,188,121),(229,229,16),(36,114,200),(188,63,188),(17,168,205),(229,229,229))


def rgb(n):
    if n<16: return BASE[n%8]
    if n>=232: return (8+(n-232)*10,)*3
    n-=16; steps=(0,95,135,175,215,255)
    return steps[n//36],steps[(n//6)%6],steps[n%6]


def colors(attr):
    pair=(attr & curses.A_COLOR)>>8
    if pair>=8:
        index=pair-8
        fg,bg=rgb(COLORS[index]),rgb(BACKS[index])
    else:
        fg=BASE[(6,3,5,2,1,4,7)[max(0,pair-1)]] if pair else (205,215,227)
        bg=(0,0,0)
    if attr & curses.A_DIM: fg=tuple(int(v*.6) for v in fg)
    if attr & curses.A_REVERSE: fg,bg=bg,fg
    return fg,bg


class ColorWindow:
    def __init__(self,h=40,w=120): self.size=(h,w); self.erase()
    def getmaxyx(self): return self.size
    def erase(self): self.grid=[[(' ',0)]*self.size[1] for _ in range(self.size[0])]
    def noutrefresh(self): pass
    def addstr(self,y,x,text,attr=0):
        for char in text:
            size=cell_width(char)
            if 0<=y<self.size[0] and 0<=x<self.size[1]: self.grid[y][x]=(char,attr)
            if size==2 and x+1<self.size[1]: self.grid[y][x+1]=('',attr)
            x+=size


def frame_html(grid):
    rows=[]
    for row in grid:
        runs=[]; previous=None; run=''
        for char,attr in row:
            style=colors(attr)
            if style!=previous and run:
                fg,bg=previous; runs.append(f'<span style="color:rgb{fg};background:rgb{bg}">{html.escape(run)}</span>'); run=''
            run+=char; previous=style
        if run:
            fg,bg=previous; runs.append(f'<span style="color:rgb{fg};background:rgb{bg}">{html.escape(run)}</span>')
        rows.append(''.join(runs))
    return '\n'.join(rows)


def png(grid,path):
    from PIL import Image,ImageDraw,ImageFont
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',16)
    dots=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
    im=Image.new('RGB',(len(grid[0])*10,len(grid)*20),(0,0,0)); d=ImageDraw.Draw(im)
    for y,row in enumerate(grid):
        for x,(char,attr) in enumerate(row):
            fg,bg=colors(attr); px,py=x*10,y*20
            d.rectangle((px,py,px+9,py+19),fill=bg)
            if char and char!=' ': d.text((px,py),char,font=dots if 0x2800<=ord(char)<=0x28ff else font,fill=fg)
    im.save(path)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--png',action='store_true'); args=parser.parse_args()
    root=Path(__file__).resolve().parent.parent; out=root/'docs'
    frames=[]; labels=[]
    with tempfile.TemporaryDirectory(dir=root/'.antigravity/archive/cathedral') as temp:
        store=Store(Path(temp)); store.settings.update(language='en',shake=False,theme='cathedral')
        with patch.object(App,'_setup'),patch('curses.init_pair'),patch('curses.color_pair',side_effect=lambda n:n<<8),patch('curses.doupdate'):
            a=App(ColorWindow(),store,AudioStub(),42); a.has_color=True; a.art_palette.setup(256,256); a.art_epoch=90
            a.now=100; a.draw()
            frames.append(frame_html(a.win.grid)); labels.append('Menu')
            if args.png: png(a.win.grid,out/'cathedral-menu.png')
            a.start(); a.screen='playing'; a.game.state='playing'; a.game.active=Piece('T',0,4,9)
            a.game.held='I'; a.game.score=12480; a.game.lines=28; a.game.level=3
            for y in range(17,22):
                for x in range(10):
                    if x not in (4,5) and (x*3+y)%7>1: a.game.board[y][x]='IOTSZJL'[(x//2+y)%7]
            for name,data in (
                ('idle',{}),
                ('drop',dict(cells=((4,2),(4,3),(4,4),(4,5)),distance=15)),
                ('clear',dict(rows=[18,19,20,21],count=4,spin=False,combo=2,b2b=True,perfect=False,points=2400)),
                ('clear',dict(rows=[18,19,20,21],count=4,spin=False,combo=4,b2b=True,perfect=True,points=12000))):
                if data.get('perfect'):
                    a.game.board=[[None]*10 for _ in range(22)]
                    a.game.active=Piece('T',0,4,2)
                a.effects=Effects(); a.effects.configure(a.settings); a.now=100
                a.effects.trigger(name,data,100)
                label='all-clear' if data.get('perfect') else 'tetris' if name=='clear' else name
                for i in range(20):
                    a.now=100+i*.1; a.effects.update(a.now); a.draw()
                    frames.append(frame_html(a.win.grid)); labels.append(f'{label} +{i/10:.1f}s')
                    if args.png and i==4: png(a.win.grid,out/f'cathedral-{label}.png')
            a.game.active=Piece('T',0,4,9)
            for y in range(17,22):
                for x in range(10):
                    if x not in (4,5) and (x*3+y)%7>1: a.game.board[y][x]='IOTSZJL'[(x//2+y)%7]
            for h,w in ((28,64),(30,80),(50,160)):
                a.win=ColorWindow(h,w); a.effects=Effects(); a.now=105; a.draw()
                frames.append(frame_html(a.win.grid)); labels.append(f'{w} x {h}')
                if args.png: png(a.win.grid,out/f'cathedral-{w}x{h}.png')
    payload=json.dumps(dict(frames=frames,labels=labels),ensure_ascii=False).replace('</','<\\/')
    (out/'cathedral-preview.html').write_text('''<!doctype html><html lang="ko"><meta charset="utf-8"><title>TEXTRIS / Cathedral review</title>
<style>body{background:#080c16;color:#b7c7d8;font:14px system-ui;margin:24px}button,input{margin:8px}pre{font:16px/20px 'DejaVu Sans Mono',monospace;white-space:pre;margin:0;background:black;width:max-content;padding:16px}h1{font-size:20px}small{color:#8191a5}</style>
<h1>TEXTRIS / 우주 대성당 컬러 프레임 검토</h1><small>실제 App.draw 출력 · 고정 이벤트 시나리오 · seed 42 · 120×40 · 0.1초 간격 · 마지막 세 프레임은 크기별 비교</small><div><button id="play">재생 / 정지</button><input type="range" id="seek" min="0" value="0"><span id="label"></span></div><pre id="screen"></pre>
<script>const data='''+payload+''';let index=0,playing=false;const seek=document.getElementById('seek');seek.max=data.frames.length-1;function show(){document.getElementById('screen').innerHTML=data.frames[index];document.getElementById('label').textContent=data.labels[index];seek.value=index}seek.oninput=()=>{index=+seek.value;playing=false;show()};document.getElementById('play').onclick=()=>playing=!playing;setInterval(()=>{if(playing){index=(index+1)%data.frames.length;show()}},100);show()</script></html>''',encoding='utf-8')
    print(f'{len(frames)} color frames: {out / "cathedral-preview.html"}')


if __name__=='__main__': main()
