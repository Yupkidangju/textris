"""실제 단일보드와 향후 복수viewport의 읽기 전용 검토 자료."""
import argparse
from contextlib import ExitStack
import curses
import json
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
from scripts.theme_ceremony_probe import png
from tests.capture_cathedral import ColorWindow
from tests.capture_atlas import populate
from tests.test_ui import AudioStub
from textris.art import RenderContext, THEME_COLORS, battle_viewports
from textris.art_director import Cue
from textris.storage import Store
from textris.ui import App
from textris.visual_state import VisualState
from textris.scenes import THEMES
from tests import capture_cathedral as capture


def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,required=True)
    out=p.parse_args().out.resolve(); out.mkdir(parents=True,exist_ok=False)
    results=[]; font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',14)
    with ExitStack() as stack:
        for name,value in [('A_COLOR',0xff00),('A_BOLD',0x200000),('A_DIM',0x100000),('A_REVERSE',0x40000)]:
            stack.enter_context(patch.object(curses,name,value))
        stack.enter_context(patch.object(App,'_setup'))
        stack.enter_context(patch('curses.init_pair'))
        stack.enter_context(patch('curses.color_pair',side_effect=lambda n:n<<8))
        stack.enter_context(patch('curses.doupdate'))
        for theme in THEMES:
            capture.COLORS=THEME_COLORS[theme]
            items=[]
            for name in ('idle','danger','fever','combo','b2b','move','rotate','hold','drop','lock','menu','ready'):
                a=App(ColorWindow(28,64),Store(out/'state'),AudioStub(),42,unicode_art=True)
                a.settings.update(theme=theme,display_mode='unicode',flash=False,shake=False)
                a.has_color=True; a.art_palette.setup(256,256,theme); a.now=100
                populate(a); a.game.level=4
                if name=='danger': a.game.board[3][0]='I'
                if name=='fever': a.effects.fever_until=102
                if name=='combo': a.game.combo=6
                if name=='b2b': a.game.b2b=3
                a.process_events()
                if name in ('move','rotate','hold','drop','lock'):
                    a.effects.trigger(name,dict(cells=((4,8),(5,8),(4,9),(5,9)),distance=9),100)
                    a.now=100+(.06 if name=='move' else .12)
                if name in ('menu','ready'): a.screen=name
                checksum=a.session.checksum(); a.draw()
                assert checksum==a.session.checksum()
                path=out/f'{theme}-{name}-64x28.png'; png(a.win.grid,path); items.append((name,path))
                results.append(dict(theme=theme,case=name,size=[64,28],state_unchanged=True,file=path.name))
            for size in ((64,28),(120,40)):
                w,h=size; views=battle_viewports(w,h)
                protected=tuple(rect for v in views for rect in v.protected)+((0,0,w-1,2),(0,h-2,w-1,2))
                ctx=RenderContext(w,h,protected,viewports=views)
                a=App(ColorWindow(h,w),Store(out/'state'),AudioStub(),42,unicode_art=True)
                a.settings.update(theme=theme,flash=False,shake=False)
                a.has_color=True; a.art_palette.setup(256,256,theme); a.now=101
                states=(VisualState('p1',fever=True,combo=5),VisualState('p2',danger=True))
                cue=Cue('bloom',100,102,coords=(18,19,20,21),player_id='p2',variant='spin')
                a.effects.stage.render(ctx,101,theme,cue,flash=False,state=states).paint(a)
                a.center(0,'FUTURE TWO-BOARD RENDER STUDY',a.art_attr(9))
                for v in views:
                    x,y,ww,hh=v.board_rect
                    a.put(y-2,x,v.player_id.upper()+' / PLACEHOLDER',a.art_attr(5))
                    a.put(y-1,x,'H:I  NEXT:TOSZJ',a.art_attr(6))
                    a.put(y,x,'+'+'-'*20+'+',a.art_attr(3))
                    for row in range(1,21):
                        a.put(y+row,x,'|'+' '*20+'|',a.art_attr(3))
                        if row>=17:
                            a.put(y+row,x+1,'[]'*((row*3)%7+2),a.art_attr(4))
                    a.put(y+21,x,'+'+'-'*20+'+',a.art_attr(3))
                a.center(h-1,'LAYOUT ONLY / NO BATTLE GAME MODE',a.art_attr(6))
                path=out/f'{theme}-future-two-{w}x{h}.png'; png(a.win.grid,path)
                results.append(dict(theme=theme,case='future-layout',size=size,game_mode=False,file=path.name))
            sheet=Image.new('RGB',(1280,((len(items)+1)//2)*310),'#080c16'); draw=ImageDraw.Draw(sheet)
            for i,(name,path) in enumerate(items):
                x,y=(i%2)*640,(i//2)*310; draw.text((x+8,y+3),theme+' / '+name,font=font,fill='#dae5ee')
                with Image.open(path) as im:
                    im.thumbnail((630,280)); sheet.paste(im,(x+5,y+25))
            sheet.save(out/f'{theme}-states.png')
    (out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(dict(out=str(out),frames=len(results),scope='App.draw states and renderer-only future layout; no battle or physical font claim')))


if __name__=='__main__': main()
