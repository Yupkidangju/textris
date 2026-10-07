"""감사 2 성취 수정의 실제 App.draw 캡처/보호/성능 증거. 기존 결과는 덮어쓰지 않는다.

python -m scripts.theme_ceremony_probe --out .antigravity/audit-2-fix-themes/runtime
Pillow는 검토용 도구에서만 사용하며 터미널 폰트/물리적 입력 검증을 대신하지 않는다.
"""
import argparse
from contextlib import ExitStack
import curses
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import platform
from time import perf_counter
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
from tests import capture_cathedral as capture
from tests.benchmark_cathedral import RenderWindow
from tests.capture_cathedral import ColorWindow, colors, frame_html
from tests.test_theme_ceremonies import CEREMONIES, geometry, produce_ceremony
from tests.test_ui import AudioStub
from textris.art import BRAILLE_BITS, RenderContext, THEME_COLORS, game_layout
from textris.art_director import Cue
from textris.scenes import THEMES
from textris.storage import Store
from textris.theme_art import ThemeScene
from textris.ui import App


def digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()


def png(grid, path):
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 16)
    symbols = ImageFont.truetype('C:/Windows/Fonts/seguisym.ttf', 16)
    im = Image.new('RGB', (len(grid[0])*10, len(grid)*20))
    draw = ImageDraw.Draw(im)
    for y, row in enumerate(grid):
        for x, (char, attr) in enumerate(row):
            fg, bg = colors(attr)
            px, py = x*10, y*20
            draw.rectangle((px, py, px+9, py+19), fill=bg)
            if not char or char == ' ':
                continue
            if 0x2800 <= ord(char) <= 0x28ff:
                for dx in range(2):
                    for dy in range(4):
                        if ord(char)-0x2800 & 1 << BRAILLE_BITS[dx][dy]:
                            xx, yy = px+2+dx*5, py+2+dy*5
                            draw.ellipse((xx, yy, xx+1, yy+1), fill=fg)
            else:
                draw.text((px, py-1), char, font=font if ord(char)<128 else symbols, fill=fg)
    im.save(path)


def make_app(out, theme, size=(120, 40), mode='unicode', name='clear'):
    store = Store(out / 'fixtures' / f'{theme}-{size[0]}-{size[1]}-{mode}-{name}')
    store.settings.update(theme=theme, shake=False, flash=False, ascii=mode=='ascii',
                          display_mode='ascii' if mode=='ascii' else 'unicode', color=mode!='mono')
    app = App(ColorWindow(size[1], size[0]), store, AudioStub(), 42, unicode_art=mode!='ascii')
    app.terminal_ascii = mode == 'ascii'
    app.has_color = mode != 'mono'
    app.art_palette.setup(256, 256, theme)
    app.art_epoch = 90.
    cue = produce_ceremony(app, name)
    app.now = (cue.start+cue.end)/2
    return app, cue


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path('.antigravity/audit-2-fix-themes/runtime'))
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    results = dict(python=platform.python_version(), platform=platform.platform(), seed=42,
        notes=['Real App.draw; OS curses setup/output and color attributes emulated.',
               'Actual hard-drop input handler and engine produce each semantic cue.',
               'PNG uses exact Braille masks and Windows fonts; not a native terminal font capture.',
               'Performance excludes terminal transfer and physical keyboard input.',
               'Shared Windows host with concurrent remediation agents; timing is not an isolated benchmark.'],
        producer={}, semantics={}, matrix={}, performance={}, source_hashes={})
    for source in ('textris/theme_art.py', 'tests/test_theme_ceremonies.py', __file__):
        results['source_hashes'][Path(source).name] = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    frames = []
    with ExitStack() as stack:
        for name, value in [('A_COLOR',0xff00),('A_BOLD',0x200000),('A_DIM',0x100000),('A_REVERSE',0x40000)]:
            stack.enter_context(patch.object(curses, name, value))
        stack.enter_context(patch.object(App, '_setup'))
        stack.enter_context(patch('curses.init_pair'))
        stack.enter_context(patch('curses.color_pair', side_effect=lambda n:n<<8))
        stack.enter_context(patch('curses.doupdate'))
        layout = game_layout(120, 40)
        context = RenderContext(120, 40, layout.protected)
        for theme in THEMES:
            capture.COLORS = THEME_COLORS[theme]
            producer = []
            for name in CEREMONIES:
                app, cue = make_app(out, theme, name=name)
                checksum, replay = app.session.checksum(), app.session.replay()
                app.effects.director.major = None
                app.draw()
                idle = [row.copy() for row in app.win.grid]
                app.effects.director.major = cue
                app.draw()
                board = (layout.board[0]+1, layout.board[1]+1, 20, 20)
                stable = all(idle[y][x][0] == app.win.grid[y][x][0]
                    for xx, yy, ww, hh in (board, layout.protected[1], layout.protected[2])
                    for x in range(xx, xx+ww) for y in range(yy, yy+hh))
                filename = f'{theme}-{name}.png'
                png(app.win.grid, out / filename)
                frames.append((f'{theme} / {name} / engine producer midpoint', frame_html(app.win.grid)))
                producer.append(dict(cue=cue.name, label=cue.label, coords=cue.coords,
                    duration=round(cue.end-cue.start, 3), protected_glyphs_equal=stable,
                    checksum_unchanged=checksum==app.session.checksum(),
                    replay_unchanged=replay==app.session.replay(), capture=filename))
            results['producer'][theme] = producer
            scene = ThemeScene()
            cue = Cue('clear', 100., 102., power=1., coords=(18,19,20,21))
            semantic = {}
            for name in CEREMONIES:
                actual = replace(cue, name=name)
                common = dict(board=layout.board, flash=False)
                normal = geometry(scene.render(context, 101., theme, actual, intensity=1., **common))
                low = geometry(scene.render(context, 101., theme, actual, intensity=.25, **common))
                powerful = geometry(scene.render(context, 101., theme, replace(actual,power=1.6), intensity=1., **common))
                semantic[name] = dict(signature=digest(normal), intensity_changes_geometry=normal!=low,
                                      power_changes_geometry=normal!=powerful)
                if name in ('clear', 'bloom', 'ascension'):
                    changed_rows = geometry(scene.render(context,101.,theme,
                        replace(actual,coords=(8,9,10,11)),intensity=1.,**common))
                    semantic[name]['rows_change_geometry'] = normal!=changed_rows
            semantic['distinct_count'] = len({semantic[n]['signature'] for n in CEREMONIES})
            semantic['clear_rows_change_geometry'] = geometry(scene.render(context,101.,theme,cue,board=layout.board)) != geometry(
                scene.render(context,101.,theme,replace(cue,coords=(8,)),board=layout.board))
            results['semantics'][theme] = semantic
            matrix = []
            for size in ((64,28),(80,30),(120,40),(160,50)):
                for mode in ('unicode', 'ascii', 'mono'):
                    w, h = size
                    for name in CEREMONIES:
                        app, cue = make_app(out, theme, size, mode, name)
                        state = app.session.checksum()
                        app.draw()
                        canvas = app.effects._art_cache
                        entry = dict(size=size, mode=mode, cue=name,
                            protected=not any(point in canvas.blocked for point in canvas.cells),
                            clipped=all(0<=x<w-1 and 0<=y<h for x,y in canvas.cells),
                            ascii_safe=mode!='ascii' or all(not ch or ch.isascii() for row in app.win.grid for ch,_ in row),
                            state_unchanged=state==app.session.checksum())
                        assert all(entry[key] for key in ('protected','clipped','ascii_safe','state_unchanged')), entry
                        matrix.append(entry)
                    if size == (64,28):
                        png(app.win.grid, out/f'{theme}-awakening-{mode}-64x28.png')
            results['matrix'][theme] = matrix
            # 매 40프레임 새 실제 사건을 발생시키며 6종 모두 240프레임에 포함한다.
            timings = []
            for index in range(240):
                if index % 40 == 0:
                    app, cue = make_app(out, theme, name=CEREMONIES[index//40])
                    app.win = RenderWindow(40,120)
                app.now = cue.start+(cue.end-cue.start)*(index%40)/40
                begin = perf_counter()
                app.draw()
                timings.append((perf_counter()-begin)*1000)
            results['performance'][theme] = dict(frames=len(timings), mean_ms=round(sum(timings)/240,3),
                p95_ms=round(sorted(timings)[227],3), max_ms=round(max(timings),3), samples_ms=timings)
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
    for theme in THEMES:
        sheet = Image.new('RGB',(1200,3*430),'#080c16')
        draw = ImageDraw.Draw(sheet)
        for index, name in enumerate(CEREMONIES):
            x, y = (index%2)*600, (index//2)*430
            draw.text((x+10,y+6),f'{theme} / {name}',font=font,fill='#dae5ee')
            with Image.open(out/f'{theme}-{name}.png') as frame:
                frame.thumbnail((590,395))
                sheet.paste(frame,(x+5,y+28))
        sheet.save(out/f'{theme}-contact.png')
    data = json.dumps(frames, ensure_ascii=False).replace('</','<\\/')
    html = '''<!doctype html><meta charset="utf-8"><title>TEXTRIS ceremony verification</title>
<style>body{background:#101723;color:#dae5ee;font:16px system-ui}pre{font:16px/20px Consolas,monospace;width:max-content}</style>
<h1>Engine-produced ceremony frames</h1><p>App.draw; emulated colors. Braille PNG masks are exact. Native terminal font compatibility is excluded.</p>
<select id="choice"></select><pre id="screen"></pre><script>const frames=DATA;const choice=document.getElementById('choice');
frames.forEach((frame,i)=>{const option=document.createElement('option');option.value=i;option.textContent=frame[0];choice.append(option)});
function show(){document.getElementById('screen').innerHTML=frames[+choice.value][1]}choice.onchange=show;show();</script>'''.replace('DATA',data)
    (out/'frames.html').write_text(html,encoding='utf-8')
    (out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(dict(out=str(out),producer_checks=36,matrix_checks=432,
        semantics={theme:results['semantics'][theme]['distinct_count'] for theme in THEMES},
        performance={theme:{k:v for k,v in item.items() if k!='samples_ms'} for theme,item in results['performance'].items()}),indent=2))


if __name__ == '__main__':
    main()
