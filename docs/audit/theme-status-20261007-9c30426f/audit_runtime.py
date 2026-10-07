"""읽기 전용 테마 감사: 새 증거 폴더에만 렌더/측정 결과를 보존한다."""
import curses
import hashlib
import json
import platform
import sys
from contextlib import ExitStack
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
from tests.capture_atlas import populate
from tests.capture_cathedral import ColorWindow, colors, frame_html
from tests import capture_cathedral as capture
from tests.test_ui import AudioStub
from tests.benchmark_cathedral import RenderWindow
from textris.art import BRAILLE_BITS, RenderContext, THEME_COLORS, game_layout
from textris.art_director import Cue
from textris.scenes import THEMES
from textris.storage import Store
from textris.theme_art import ThemeScene
from textris.ui import App

OUT = Path(__file__).resolve().parent
FONT = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 16)
SYMBOLS = ImageFont.truetype('C:/Windows/Fonts/seguisym.ttf', 16)


def fresh(path):
    if path.exists():
        raise FileExistsError(path)
    return path


def sig(cells):
    items = sorted((x,y,v.glyph,v.style,round(v.depth,5),v.mask)
                   for (x,y),v in cells.items())
    return hashlib.sha256(json.dumps(items).encode()).hexdigest()


def png(grid, path):
    im = Image.new('RGB', (len(grid[0])*10, len(grid)*20))
    d = ImageDraw.Draw(im)
    for y,row in enumerate(grid):
        for x,(ch,attr) in enumerate(row):
            fg,bg = colors(attr)
            px,py = x*10,y*20
            d.rectangle((px,py,px+9,py+19),fill=bg)
            if not ch or ch == ' ':
                continue
            if 0x2800 <= ord(ch) <= 0x28ff:
                mask = ord(ch)-0x2800
                for dx in range(2):
                    for dy in range(4):
                        if mask & 1 << BRAILLE_BITS[dx][dy]:
                            xx,yy = px+2+dx*5,py+2+dy*5
                            d.ellipse((xx,yy,xx+1,yy+1),fill=fg)
            else:
                d.text((px,py-1),ch,font=FONT if ord(ch)<128 else SYMBOLS,fill=fg)
    im.save(fresh(path))


def make_app(theme, size=(120,40), ascii_mode=False):
    w,h = size
    fixture = OUT / 'fixtures' / f'{theme}-{w}-{h}-{ascii_mode}'
    fixture.mkdir(parents=True,exist_ok=True)
    store = Store(fixture)
    store.settings.update(language='en',shake=False,theme=theme,ascii=ascii_mode)
    app = App(ColorWindow(h,w),store,AudioStub(),42,unicode_art=True)
    app.terminal_ascii = ascii_mode
    app.has_color = True
    app.art_palette.setup(256,256,theme)
    app.art_epoch = 90
    app.now = 100
    populate(app)
    return app


def main():
    result = dict(python=platform.python_version(),platform=platform.platform(),
        seed=42,time=100.6,captures=[],contracts={},event_variation={},
        performance={},notes=[
        'Actual App.draw with emulated Linux color-pair bit masks; no terminal IO.',
        'Unicode intentionally enabled. PNG Braille dots drawn from exact cell masks; other glyphs use Windows fonts.',
        'Protected playfield/HUD comparison uses unchanged game state and event cues directly injected.',
        'Original baseline is the current HEAD cathedral, not a pre-upgrade historical version.'])
    html_frames=[]
    images=[]
    with ExitStack() as stack:
        for name,value in [('A_COLOR',0xff00),('A_BOLD',0x200000),('A_DIM',0x100000),('A_REVERSE',0x40000)]:
            stack.enter_context(patch.object(curses,name,value))
        stack.enter_context(patch.object(App,'_setup'))
        stack.enter_context(patch('curses.init_pair'))
        stack.enter_context(patch('curses.color_pair',side_effect=lambda n:n<<8))
        stack.enter_context(patch('curses.doupdate'))
        for theme in THEMES:
            app=make_app(theme)
            app.now=100.6
            app.draw()
            before=[row.copy() for row in app.win.grid]
            capture.COLORS=THEME_COLORS[theme]
            path=OUT/f'{theme}-idle-unicode-120x40.png'
            png(before,path)
            images.append((f'{theme} / idle',path))
            html_frames.append((f'{theme} / idle',frame_html(before)))
            result['captures'].append(path.name)
            app.effects.trigger('clear',dict(count=4,rows=[18,19,20,21],combo=4,perfect=True),100)
            app.effects.update(app.now)
            app.draw()
            after=app.win.grid
            bx,by=game_layout(120,40).board
            protected_same=all(before[y][x][0]==after[y][x][0]
                for x in range(bx+1,bx+21) for y in range(by+1,by+21))
            layout=game_layout(120,40)
            hud_same=all(before[y][x][0]==after[y][x][0]
                for xx,yy,ww,hh in (layout.protected[1],layout.protected[2])
                for x in range(xx,xx+ww) for y in range(yy,yy+hh))
            path=OUT/f'{theme}-all-clear-unicode-120x40.png'
            png(after,path)
            images.append((f'{theme} / all clear +0.6s',path))
            html_frames.append((f'{theme} / all clear +0.6s',frame_html(after)))
            result['captures'].append(path.name)
            context=RenderContext(120,40,layout.protected)
            scene=ThemeScene()
            idle=scene.render(context,100.6,theme)
            event=scene.render(context,100.6,theme,app.effects.director.major)
            mode_checks=[]
            for size in ((64,28),(80,30),(120,40),(160,50)):
                for ascii_mode,braille in ((True,True),(False,True),(False,False)):
                    w,h=size
                    ctx=RenderContext(w,h,game_layout(w,h).protected,ascii_mode,braille)
                    frame=ThemeScene().render(ctx,100.6,theme,app.effects.director.major)
                    mode_checks.append(dict(size=size,ascii=ascii_mode,braille=braille,
                        clipped=all(0<=x<w-1 and 0<=y<h for x,y in frame.cells),
                        protected=all((x,y) not in frame.blocked for x,y in frame.cells),
                        ascii_safe=all(v.glyph.isascii() for v in frame.cells.values()) if ascii_mode else None,
                        glyph_count=len(frame.cells)))
            result['contracts'][theme]=dict(board_glyphs_equal=protected_same,
                hud_glyphs_equal=hud_same,idle_cells=len(idle.cells),
                event_changes_cells=idle.cells!=event.cells,
                palette_distinct=THEME_COLORS[theme]!=THEME_COLORS['cathedral'] if theme!='cathedral' else None,
                size_modes=mode_checks)
            # 같은 절대 시각과 동일 위상에서 이벤트 이름/출력 의미의 영향만 분리한다.
            event_sigs={}
            event_rows=[]
            for name in ('clear','bloom','ascension','victory','eclipse','awakening'):
                cue=Cue(name,100,101.2,4,1.2,(18,19,20,21),name.upper())
                event_sigs[name]=sig(ThemeScene().render(context,100.6,theme,cue).cells)
                app.effects.director.major=cue
                app.effects._art_key=None
                app.draw()
                path=OUT/f'{theme}-{name}-phase050.png'
                png(app.win.grid,path)
                event_rows.append((f'{theme}/{name} phase .5',path))
                html_frames.append((f'{theme}/{name} phase .5',frame_html(app.win.grid)))
                result['captures'].append(path.name)
            result['event_variation'][theme]=dict(signatures=event_sigs,
                distinct_geometry_count=len(set(event_sigs.values())))
            # 실제 ASCII App.draw도 최소/최대 크기에서 전체 출력 경계를 검증한다.
            for size in ((64,28),(160,50)):
                small=make_app(theme,size,True)
                small.now=100.6;small.draw()
                assert all(not c or 32<=ord(c)<127 for row in small.win.grid for c,a in row)
                path=OUT/f'{theme}-ascii-{size[0]}x{size[1]}.png'
                png(small.win.grid,path)
                result['captures'].append(path.name)
                html_frames.append((path.stem,frame_html(small.win.grid)))
        # 기본 BENCH와 같은 240프레임/테마. 색은 위와 동일한 모의 출력.
        for theme in THEMES:
            app=make_app(theme)
            app.win=RenderWindow(40,120)
            values=[]
            for i in range(240):
                app.now=100+i/60
                if i%120==30:
                    app.effects.trigger('clear',dict(count=4,rows=[18,19,20,21],combo=4,perfect=i>120),app.now)
                start=perf_counter();app.draw();values.append((perf_counter()-start)*1000)
            result['performance'][theme]=dict(frames=240,mean_ms=round(sum(values)/240,3),
                p95_ms=round(sorted(values)[227],3),max_ms=round(max(values),3),
                includes_terminal_io=False,unicode=True,color_emulated=True)
    sheet=Image.new('RGB',(1000,6*390),'#080c16')
    d=ImageDraw.Draw(sheet)
    for i,(label,path) in enumerate(images):
        x=(i%2)*500;y=(i//2)*390
        d.text((x+8,y+5),label,font=FONT,fill='#cad7e6')
        with Image.open(path) as im:
            im.thumbnail((492,355))
            sheet.paste(im,(x+4,y+28))
    sheet.save(fresh(OUT/'theme-contact.png'))
    data=json.dumps(html_frames,ensure_ascii=False).replace('</','<\\/')
    doc='''<!doctype html><html lang="en"><meta charset="utf-8"><title>TEXTRIS audit capture</title>
<style>body{background:#0a0e16;color:#dae5ee;font:16px system-ui}select{max-width:95vw}pre{font:16px/20px Consolas,monospace;background:black;width:max-content}</style>
<h1>Read-only theme audit captures</h1><p>HEAD cathedral and current other themes, seed 42; same App.draw. Emulated color pairs. Windows actual glyph/display compatibility is excluded.</p>
<select id="choice"></select><pre id="screen"></pre><script>const data=DATA;const c=document.getElementById('choice');data.forEach((v,i)=>{const o=document.createElement('option');o.value=i;o.textContent=v[0];c.append(o)});function show(){document.getElementById('screen').innerHTML=data[+c.value][1]}c.onchange=show;show();</script></html>'''.replace('DATA',data)
    fresh(OUT/'frames.html').write_text(doc,encoding='utf-8')
    fresh(OUT/'runtime-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(captures=len(result['captures']),contracts=result['contracts'],
        event_variation=result['event_variation'],performance=result['performance']),indent=2))


if __name__=='__main__':
    main()
