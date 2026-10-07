"""App.draw의 6개 테마와 44개 갤러리 항목을 오프라인 검토 자료로 보존한다.

실행: python3 -m tests.capture_atlas
Pillow는 검토 도구에서만 필요하다. 성능 수치는 수집하지 않는다.
"""
import json
import re
from pathlib import Path
import tempfile
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from tests import capture_cathedral as capture
from tests.test_ui import AudioStub
from textris.art import THEME_COLORS
from textris.engine import Piece
from textris.expansion_ui import CATALOG
from textris.scenes import BACKGROUNDS, THEMES
from textris.storage import Store
from textris.ui import App


def populate(app):
    app.start()
    app.screen = 'playing'
    app.game.state = 'playing'
    app.game.active = Piece('T', 0, 4, 9)
    app.game.held = 'I'
    app.game.score = 12480
    app.game.lines = 28
    app.game.level = 3
    for y in range(17, 22):
        for x in range(10):
            if x not in (4, 5) and (x*3+y) % 7 > 1:
                app.game.board[y][x] = 'IOTSZJL'[(x//2+y) % 7]


def contact_sheet(items, path, cols, cell_width):
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 14)
    cell_height = round(cell_width * 2 / 3) + 30
    sheet = Image.new('RGB', (cols*cell_width, ((len(items)+cols-1)//cols)*cell_height), '#101723')
    draw = ImageDraw.Draw(sheet)
    for i, (label, source) in enumerate(items):
        x, y = (i % cols)*cell_width, (i//cols)*cell_height
        with Image.open(source) as frame:
            thumbnail = frame.copy()
            thumbnail.thumbnail((cell_width-12, cell_height-34), Image.Resampling.LANCZOS)
            sheet.paste(thumbnail, (x+(cell_width-thumbnail.width)//2, y+28))
        draw.text((x+8, y+6), label, font=font, fill='#cad7e6')
    sheet.save(path, optimize=True)


def main():
    root = Path(__file__).resolve().parent.parent
    out = root / 'docs'
    out.mkdir(exist_ok=True)
    full = Path(tempfile.mkdtemp(prefix='textris-art-atlas-'))
    frames, theme_images, gallery_images = [], [], []
    styles = {}

    def compact_frame(grid):
        def token(match):
            css = match.group(1)
            if css not in styles:
                styles[css] = f"c{len(styles)}"
            return f'class="{styles[css]}"'
        return re.sub(r'style="([^"]+)"', token, capture.frame_html(grid))
    with tempfile.TemporaryDirectory(prefix='textris-art-capture-') as state:
        with patch.object(App, '_setup'), patch('curses.init_pair'), patch('curses.color_pair', side_effect=lambda n: n << 8), patch('curses.doupdate'):
            def snapshot(theme, screen, size=(120, 40), ascii_mode=False, catalog_index=None, event=None):
                w, h = size
                store = Store(Path(state))
                store.settings.update(language='en', shake=False, theme=theme, ascii=ascii_mode,
                                      display_mode='ascii' if ascii_mode else 'unicode')
                app = App(capture.ColorWindow(h, w), store, AudioStub(), 42)
                app.has_color = True
                app.art_palette.setup(256, 256, theme)
                app.art_epoch = 90
                app.now = 100
                kind = 'theme'
                suffix = screen
                if screen == 'playing':
                    populate(app)
                elif screen in ('boss','analysis','ready','result'):
                    populate(app)
                    if screen=='boss':
                        app.start('boss'); app.screen='playing'; app.game.state='playing'
                    else:
                        app.screen=screen
                        if screen=='analysis': app.session.samples=[[0,0,0],[60,200,1],[180,1200,4]]
                        elif screen=='ready': app.ready_elapsed=1
                        else: app.game.state='over';app.result_since=99
                    kind='auxiliary'
                elif screen == 'gallery':
                    app.open_gallery()
                    app.gallery_index = catalog_index
                    app.gallery_trigger()
                    kind = 'background' if catalog_index < len(BACKGROUNDS) else 'effect'
                    suffix = kind + '-' + CATALOG[catalog_index]
                if event:
                    app.effects.trigger('clear',dict(count=4,rows=[18,19,20,21],combo=4,perfect=event=='ascension'),100)
                    suffix=event;kind='ceremony'
                app.now = 100.6
                app.effects.update(app.now)
                app.draw()
                grid = app.win.grid
                assert len(grid) == h and all(len(row) == w for row in grid)
                if ascii_mode:
                    assert all(32 <= ord(glyph) < 127 for row in grid for glyph, _ in row if glyph)
                capture.COLORS = THEME_COLORS[theme]
                mode = 'ASCII' if ascii_mode else 'Unicode'
                label = f'{theme} / {suffix} / {w}x{h} / {mode}'
                filename = f'{theme}-{suffix}-{w}x{h}-{mode.lower()}.png'
                target = full / filename
                capture.png(grid, target)
                frames.append(dict(label=label, category='ASCII' if ascii_mode else kind,
                                   theme=theme, width=w, height=h, html=compact_frame(grid)))
                return target

            for theme in THEMES:
                for screen in ('menu', 'playing'):
                    path = snapshot(theme, screen)
                    theme_images.append((f'{theme} / {screen}', path))
            for theme in THEMES:
                for event in ('tetris','ascension'): snapshot(theme,'playing',event=event)
            for screen in ('boss','analysis','ready','result'): snapshot('cathedral',screen)
            print('Captured themes, ceremonies and auxiliary screens.', flush=True)
            for i, name in enumerate(CATALOG):
                path = snapshot('cathedral', 'gallery', catalog_index=i)
                kind = 'BG' if i < len(BACKGROUNDS) else 'FX'
                gallery_images.append((f'{kind} / {name}', path))
            print('Captured all 44 gallery entries.', flush=True)
            for theme in THEMES:
                for size in ((64, 28), (80, 30), (160, 50)):
                    snapshot(theme, 'playing', size, ascii_mode=True)
            # 최소 크기와 최대 크기의 갤러리 UI도 별도로 확인한다.
            for size, index in (((64, 28), 0), ((80, 30), 18), ((160, 50), 42)):
                snapshot('cathedral', 'gallery', size, ascii_mode=True, catalog_index=index)
    contact_sheet(theme_images, out / 'art-themes.png', 2, 480)
    contact_sheet(gallery_images, out / 'art-gallery.png', 4, 360)
    payload = json.dumps(frames, ensure_ascii=False).replace('</', '<\\/')
    document = '''<!doctype html><html lang="en"><meta charset="utf-8">
<title>TEXTRIS / Terminal art atlas</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{background:#080c16;color:#c5d3e4;font:14px system-ui;margin:24px}h1{font-size:22px}p{max-width:85ch;color:#94a9c0}select,button,input{background:#172338;color:#dbeafe;border:1px solid #34455d;padding:8px;margin:4px}label{display:inline-block}#frame{max-width:min(95vw,780px)}#viewport{overflow:auto;border:1px solid #25354b;padding:12px;margin-top:16px}pre{font:16px/20px 'DejaVu Sans Mono',monospace;white-space:pre;margin:0;background:#000;width:max-content;min-height:1em}#label{font-weight:600;margin-top:16px}a{color:#86c6ee}FRAME_STYLES</style>
<h1>TEXTRIS / Terminal art atlas</h1>
<p>2026-10-07 · Actual App.draw output · Seed 42 · Fixed scene time 100.6s; effect age 0.6s.
Six themes, all 19 backgrounds and 25 effects, plus ASCII size samples. Curses color-pair calls are emulated; application composition is unchanged. Unicode rendering depends on browser fonts. PNGs use DejaVu Sans Mono and DejaVu Sans for Braille.</p>
<p><a href="art-themes.png">Theme contact sheet</a> · <a href="art-gallery.png">Gallery contact sheet</a></p>
<div><label>Group <select id="group"><option value="">All frames</option><option>theme</option><option>background</option><option>effect</option><option>ASCII</option></select></label>
<label>Theme <select id="theme"><option value="">All themes</option></select></label></div>
<div><button id="previous" aria-label="Previous frame">Previous</button><select id="frame" aria-label="Captured frame"></select><button id="next" aria-label="Next frame">Next</button></div>
<div><label>Font size <input id="zoom" type="range" min="8" max="24" value="16"></label><span id="count"></span></div>
<div id="label" aria-live="polite"></div><div id="viewport"><pre id="screen" aria-label="Terminal frame"></pre></div>
<script>const frames=PAYLOAD;const byId=id=>document.getElementById(id);let selected=[];
for(const value of [...new Set(frames.map(f=>f.theme))]){const o=document.createElement('option');o.value=value;o.textContent=value;byId('theme').append(o)}
function show(){const f=selected[+byId('frame').value];if(!f){byId('screen').textContent='No matching frames';byId('label').textContent='';return}byId('screen').innerHTML=f.html;byId('label').textContent=f.label}
function filter(){selected=frames.filter(f=>(!byId('group').value||f.category===byId('group').value)&&(!byId('theme').value||f.theme===byId('theme').value));byId('frame').replaceChildren();selected.forEach((f,i)=>{const o=document.createElement('option');o.value=i;o.textContent=f.label;byId('frame').append(o)});byId('count').textContent=selected.length+' captured frames';show()}
byId('group').onchange=byId('theme').onchange=filter;byId('frame').onchange=show;
function advance(d){if(!selected.length)return;byId('frame').value=(+byId('frame').value+d+selected.length)%selected.length;show()}
byId('previous').onclick=()=>advance(-1);byId('next').onclick=()=>advance(1);
byId('zoom').oninput=()=>{const n=+byId('zoom').value;byId('screen').style.fontSize=n+'px';byId('screen').style.lineHeight=n*1.25+'px'};filter();</script></html>'''.replace('PAYLOAD', payload).replace('FRAME_STYLES', ''.join(f'.{name}{{{css}}}' for css, name in styles.items()))
    (out / 'art-atlas.html').write_text(document, encoding='utf-8')
    print(f'{len(frames)} frames: {out / "art-atlas.html"}')
    print(f'Full PNG frames: {full}')
    print(f'Theme sheet: {out / "art-themes.png"}')
    print(f'Gallery sheet: {out / "art-gallery.png"}')


if __name__ == '__main__':
    main()
