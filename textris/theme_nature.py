"""유한 표본으로 그리는 심해와 설원의 면, 실루엣, 성취 연출."""
import math

from .art import game_layout
from .theme_surfaces import samples, shade

TAU = math.tau


def ellipse(c, x, y, rx, ry, style=4, depth=0, start=0, end=TAU):
    count = samples(c, 64, 12)
    c.curve(((x + math.cos(a)*rx, y + math.sin(a)*ry)
             for a in (start + (end-start)*i/count for i in range(count+1))), style, depth)


def jelly_position(w, h, side, t):
    return (w*(.14 if side < 0 else .86) + math.sin(t*.23 + side)*1.2,
            h*.37 + math.sin(t*.48 + side)*1.1,
            min(11, w*.095)*(1 + .09*math.sin(t*.8 + side)))


def abyss_surface(c, t):
    w, h = c.context.width-1, c.context.height
    step = 1 if c.context.quality > .65 else 2
    for side in (-1, 1):
        x, y, r = jelly_position(w, h, side, t)
        # 발광 갓의 얇은 면은 촉수와 달리 명암 문자 자체로 읽힌다.
        for dy in range(-int(r*.43), 1, step):
            half = r*math.sqrt(max(0, 1-(dy/(r*.46))**2))
            for dx in range(-int(half), int(half)+1):
                light = .25 + .7*(1-abs(dx)/max(1, half))
                shade(c, x+dx, y+dy, light, 4 if light > .55 else 6, 2)
        for ray in range(3):
            source = w*(.19 if side < 0 else .81) + side*ray*3
            for yy in range(2, int(h*.73), 2):
                drift = side*yy*.20 + math.sin(t*.19 + yy*.12 + ray)
                shade(c, source+drift, yy, .25+.25*(1-yy/h), 6, 12+ray)
                if c.context.quality > .6 and (yy+ray) % 3 == 0:
                    shade(c, source+drift+1, yy, .2, 2, 13+ray)
        # 해저의 두 거리층은 화면을 채우지 않는 낮은 능선으로 한정한다.
        center = w*(.14 if side < 0 else .86)
        for dx in range(-int(r*1.5), int(r*1.5)+1, step):
            floor = h-3-2*(.5+.5*math.sin(dx*.31+side))
            for dy in range(3):
                shade(c, center+dx, floor+dy, .25+.19*dy, 2 if dy else 6, 7)


def abyss(c, t):
    w, h = c.context.width-1, c.context.height
    count = samples(c, 64, 14)
    for band in range(2):
        c.curve(((j*w/count, 2+band*1.6+math.sin(j*9/count-t*.25+band)*.6)
                 for j in range(count+1)), 3 if band == 0 else 2, 9)
    for side in (-1, 1):
        x, y, r = jelly_position(w, h, side, t)
        ellipse(c, x, y, r, r*.46, 4, 0, math.pi, TAU)
        c.curve(((x-r+2*r*j/count, y+math.sin(j*TAU*3/count+t*.8)*.3)
                 for j in range(count+1)), 5, -.1)
        for rib in (-.65, 0, .65):
            c.curve(((x+rib*r*math.sin(j*math.pi/(2*count)),
                      y-r*.45*math.cos(j*math.pi/(2*count)))
                     for j in range(count+1)), 3, .2)
        strands = 5 if c.context.quality > .6 else 3
        for index in range(strands):
            offset = (index/(strands-1)-.5)*r*1.45
            length = h*(.29 + .06*math.cos(index*1.7+side))
            n = samples(c, 40, 10)
            c.curve(((x+offset+math.sin(u*7-t*.8+index)*(.35+u*1.7),
                      y+.5+length*u) for u in (j/n for j in range(n+1))),
                    4 if index == strands//2 else 6, 1+index*.1)
        # 해면의 가지는 해파리 곡선과 반대인 짧고 단단한 분기다.
        for branch in range(4):
            xx = x-r*1.3+branch*r*.85
            base = h-3; top = base-(3+(branch*3 % 5))
            c.curve(((xx, base), (xx-.5*side, top+2), (xx+side, top)), 6, 3)
            for turn in (-1, 1):
                c.curve(((xx, top+3), (xx+turn*2, top+2),
                         (xx+turn*3, top+.5)), 3, 3)
                c.put(xx+turn*3, top+.5, 'o' if c.context.ascii_mode else '°', 4, 2)


def curtain_point(w, h, side, layer, u, t):
    radius = min(25, w*.22)
    x = w*(.17 if side < 0 else .83) + u*radius
    top = 2+layer*1.8+math.sin(u*3+t*.18+side)*1.2
    hem = top + h*(.12+.08*(.5+.5*math.sin(u*4-t*.24+layer)))
    return x, top, hem


def aurora_surface(c, t):
    w, h = c.context.width-1, c.context.height
    count = samples(c, 38, 10)
    layers = 3 if c.context.quality > .65 else 2
    for side in (-1, 1):
        for layer in range(layers-1, -1, -1):
            for i in range(count+1):
                u = 2*i/count-1
                x, top, hem = curtain_point(w, h, side, layer, u, t)
                for row in range(1, 6):
                    v = row/6
                    light = .2+.73*math.sin(v*math.pi)*(.75+.25*math.cos(u*8-t*.4))
                    shade(c, x, top+(hem-top)*v, light, 4 if layer == 0 else 6, 8+layer)
        center = w*(.14 if side < 0 else .86)
        radius = min(16, w*.14)
        # 설산의 밝은 사면과 어두운 사면을 서로 다른 문자 밀도로 채운다.
        base = h*.79; peak = h*.44
        for y in range(int(peak)+1, int(base)+1):
            half = radius*(y-peak)/(base-peak)
            for dx in range(-int(half), int(half)+1, 1 if c.context.quality > .6 else 2):
                light = .35 if dx < 0 else .64 if dx > (y-peak)*.3 else .91
                if (round(dx)+y) % 4 == 0:
                    light *= .65
                shade(c, center+dx, y, light, 6 if dx < 0 else 5, 4)
        for band in range(4):
            yy = h-6+band*1.3
            for dx in range(-int(radius), int(radius)+1, 2):
                if (dx+band) % 3 == 0:
                    continue
                light = .25+.45*(.5+.5*math.sin(dx*.4+t*.5+band))
                shade(c, center+dx+math.sin(t*.2+band), yy, light, 6, 7)


def aurora(c, t):
    w, h = c.context.width-1, c.context.height
    count = samples(c, 64, 12)
    layers = 3 if c.context.quality > .65 else 2
    for side in (-1, 1):
        for layer in range(layers-1, -1, -1):
            edge = [curtain_point(w, h, side, layer, 2*i/count-1, t) for i in range(count+1)]
            c.curve(((x, top) for x, top, hem in edge), 6, 8+layer)
            c.curve(((x, hem) for x, top, hem in edge), 4 if layer == 0 else 3, 7+layer)
            ribs = 12 if c.context.quality > .65 else 5
            for i in range(ribs+1):
                x, top, hem = curtain_point(w, h, side, layer, 2*i/ribs-1, t)
                c.curve(((x, top+.5), (x+.7*side, (top+hem)/2), (x, hem)), 6, 9+layer)
        center = w*(.14 if side < 0 else .86); r = min(16, w*.14)
        for layer in range(2):
            x = center+side*(layer-1)*r*.55
            base = h*(.79-layer*.08); top = h*(.44+layer*.10)
            c.curve(((x-r, base), (x-r*.34, top+(base-top)*.32),
                     (x, top), (x+r*.38, top+(base-top)*.40), (x+r, base)),
                    5 if layer == 0 else 6, 2+layer)
            c.curve(((x, top), (x+r*.15, top+(base-top)*.3),
                     (x-r*.05, top+(base-top)*.54), (x+r*.45, base)), 3, 2+layer)
        for band in range(4):
            yy = h-6+band*1.3; spread = r*(1-band*.12)
            c.curve(((center-spread+2*spread*i/count,
                      yy+math.sin(i*8/count+t*.4+band)*.24)
                     for i in range(count+1)), 3 if band == 0 else 2, 6)
    # 가림 영역 위의 열린 하늘에도 오로라의 긴 하단 곡선을 이어 준다.
    c.curve(((w*j/count, 3+math.sin(j*7/count+t*.18)*1.6)
             for j in range(count+1)), 4, 5)


def motes(c, t, theme, density):
    w, h = c.context.width-1, c.context.height
    for i in range(int(42*max(0, min(1, density))*c.context.quality)):
        layer = i % 3
        x = (i*37.17+math.sin(t*.22+i)*(.6+layer*.5)) % w
        speed = .25+layer*.35
        y = (i*11.31 + t*speed*(1 if theme == 'aurora' else -1)) % h
        if theme == 'abyss':
            glyph = 'o' if layer == 2 else '.' if c.context.ascii_mode else '·'
            c.put(x, y, glyph, 4 if layer == 2 else 2, 6+layer)
            if layer == 2 and c.context.quality > .7:
                c.put(x-.3, y+1.7, '.', 2, 10)
        else:
            c.put(x, y, '+' if layer == 2 else '.', 5 if layer == 2 else 2, 5+layer)
            if layer == 2 and i % 9 == 2 and c.context.quality > .7:
                c.line((x-.8, y), (x+.8, y), 6, 6)
                c.line((x, y-.4), (x, y+.4), 6, 6)


def crystal(c, x, y, r, style, depth=-4, angle=0):
    points = [(x+math.cos(angle+j*TAU/4)*r,
               y+math.sin(angle+j*TAU/4)*r*.6) for j in range(5)]
    c.curve(points, style, depth)


def snowflake(c, x, y, r, angle, style):
    for arm in range(6):
        a = angle+arm*TAU/6
        dx, dy = math.cos(a), math.sin(a)*.5
        c.line((x, y), (x+dx*r, y+dy*r), style, -4)
        for turn in (-1, 1):
            aa = a+turn*.6
            c.line((x+dx*r*.55, y+dy*r*.55),
                   (x+dx*r*.55+math.cos(aa)*r*.30,
                    y+dy*r*.55+math.sin(aa)*r*.15), 5, -4)


def clear(c, theme, rows, board, p, strength, style):
    bx, by = board
    reach = (8+p*c.context.width*.28)*strength
    count = samples(c, 36, 10)
    for row in rows:
        y = by+1+row-2
        for side in (-1, 1):
            start = bx-2 if side < 0 else bx+23
            if theme == 'abyss':
                c.curve(((start+side*reach*u, y+math.sin(u*TAU-p*5)*strength*.6)
                         for u in (j/count for j in range(count+1))), style, -4)
                for j in range(1+int(4*strength)):
                    u = (j+.7)/(1+int(4*strength))
                    ellipse(c, start+side*reach*u, y, .9*strength, .45*strength, 5, -5)
            else:
                for j in range(1+int(6*strength)):
                    u = (j+.5)/(1+int(6*strength)); x = start+side*reach*u
                    crystal(c, x, y, (1.2+.8*u)*strength, style)
                    c.line((x, y), (x+side*2*strength, y-strength*1.7), 5, -5)
                c.line((start, y+strength), (start+side*reach, y+strength), 6, -3)


def spin(c, theme, x, y, p, strength, style, side):
    count = samples(c, 30, 8); r = (4+12*p)*strength
    arms = 4 if theme == 'abyss' else 6
    for arm in range(arms):
        a = arm*TAU/arms+p*TAU*side
        if theme == 'abyss':
            points = [(x+math.cos(a+u*1.8)*r*u,
                       y+math.sin(a+u*1.8)*r*u*.48)
                      for u in (.18+.82*j/count for j in range(count+1))]
            c.curve(points, style if arm % 2 else 6, -4)
            xx, yy = points[-1]
            ellipse(c, xx, yy, 1.2*strength, .55*strength, 5, -5)
        else:
            points = [(x+math.cos(a)*r*.25, y+math.sin(a)*r*.125),
                      (x+math.cos(a+.4)*r*.8, y+math.sin(a+.4)*r*.4),
                      (x+math.cos(a+.9)*r, y+math.sin(a+.9)*r*.5)]
            c.curve(points, style, -4)
            crystal(c, *points[-1], 2*strength, 5, angle=a)


def abyss_ceremony(c, name, x, h, p, s, style, origin):
    count = samples(c, 36, 10)
    if name == 'bloom':
        y = origin*(1-p)+h*.5*p; r = (4+14*p)*s
        for petal in range(8):
            a = petal*TAU/8
            c.curve(((x+math.cos(a+math.sin(u*math.pi)*.4)*r*(.25+u),
                      y+math.sin(a+math.sin(u*math.pi)*.4)*r*(.25+u)*.5)
                     for u in (j/count for j in range(count+1))), style, -4)
            ellipse(c, x+math.cos(a)*r*1.25, y+math.sin(a)*r*.625, s*1.8, s*.8, 5, -5)
        ellipse(c, x, y, r*.45, r*.21, 6, -3)
    elif name == 'ascension':
        rise = (.25+p*.65)*max(3, origin-2)*s
        for strand in range(-2, 3):
            xx = x+strand*3*s; top = origin-rise*(1-abs(strand)*.12)
            c.curve(((xx+math.sin(u*6+p*5+strand)*s, origin+(top-origin)*u)
                     for u in (j/count for j in range(count+1))), 6, -3)
            ellipse(c, xx, top, s*2, s, style, -4)
            c.curve(((xx-s, top+s), (xx-s*1.5, top+s*2.5), (xx, top+s*4)), 5, -4)
    elif name == 'victory':
        y = h*.31; r = (7+p*5)*s
        for side in (-1, 1):
            c.curve(((x+side*math.sin(u*math.pi*.8)*r,
                      y+3*s-u*9*s) for u in (j/count for j in range(count+1))), style, -4)
            for j in range(4):
                u = (j+1)/5; xx = x+side*math.sin(u*math.pi*.8)*r; yy = y+3*s-u*9*s
                c.curve(((xx, yy), (xx+side*2*s, yy-2*s), (xx+side*3*s, yy-2.5*s)), 5, -4)
                c.put(xx+side*3*s, yy-2.5*s, 'o', style, -5)
        ellipse(c, x, y-s, 3*s, 1.5*s, 5, -5)
        ellipse(c, x, y+4*s, r, s, 6, -3)
    elif name == 'eclipse':
        y = h*.49; r = (4+(1-p)*11)*s
        for j in range(4):
            scale = 1-j*.21
            ellipse(c, x+math.sin(p*4+j)*s, y+j*s, r*scale, r*.24*scale, 6, -4-j*.1)
        c.curve(((x-r, y), (x-r*.25, y+r*.45), (x, y+r*.8),
                 (x+r*.25, y+r*.45), (x+r, y)), 2, -4)
    elif name == 'awakening':
        y = h*.57; r = (3+p*11)*s
        ellipse(c, x, y, r, r*.5, style, -4, 0, math.pi)
        for j in range(7):
            a = j*math.pi/6
            c.line((x, y+r*.5), (x+math.cos(a)*r, y-math.sin(a)*r*.45), 6, -4)
        ellipse(c, x, y-r*.18, r*.23, r*.16, 5, -5)
        c.line((x, y-r*.36), (x, y-r), style, -5)


def aurora_ceremony(c, name, x, h, p, s, style, origin):
    if name == 'bloom':
        y = origin*(1-p)+h*.5*p; r = (5+13*p)*s
        for ray in range(8):
            a = ray*TAU/8
            inner = r*.4; outer = r*(.85 if ray % 2 else 1.2)
            c.line((x+math.cos(a)*inner, y+math.sin(a)*inner*.5),
                   (x+math.cos(a)*outer, y+math.sin(a)*outer*.5), style, -4)
            crystal(c, x+math.cos(a)*outer, y+math.sin(a)*outer*.5, 2.5*s, 5, angle=a)
    elif name == 'ascension':
        rise = (.25+p*.65)*max(3, origin-2)*s
        count = samples(c, 32, 8)
        for fold in range(-3, 4):
            xx = x+fold*2.5*s; top = origin-rise*(1-abs(fold)*.1)
            c.curve(((xx+math.sin(u*3+fold+p*3)*s, origin+(top-origin)*u)
                     for u in (j/count for j in range(count+1))), style if fold % 2 else 6, -4)
            crystal(c, xx+math.sin(3+fold+p*3)*s, top, 1.6*s, 5)
    elif name == 'victory':
        y = h*.31; r = (6+p*5)*s
        snowflake(c, x, y, r*.8, -math.pi/2, style)
        c.curve(((x+math.cos(a)*r, y+math.sin(a)*r*.5)
                 for a in (j*TAU/6 for j in range(7))), 5, -4)
        for side in (-1, 1):
            c.curve(((x+side*r*.4, y+r*.65), (x+side*r*.75, y+r*.35),
                     (x+side*r*1.15, y+r*.65), (x+side*r*1.4, y+r*.3)), 6, -3)
    elif name == 'eclipse':
        y = h*.48; r = (4+(1-p)*11)*s
        for shard in range(-3, 4):
            xx = x+shard*r*.3; yy = y+abs(shard)*s+p*3*s
            c.curve(((xx-s, yy-r*.45), (xx+s, yy-r*.12),
                     (xx-s*.7, yy+r*.45), (xx-s, yy-r*.45)), 6, -4)
            c.line((xx-s, yy+r*.6), (xx+s, yy+r*.7), 2, -4)
    elif name == 'awakening':
        y = h*.56; r = (3+p*11)*s
        c.curve(((x-r*1.2, y+r*.3), (x-r*.55, y-r*.3),
                 (x-r*.2, y+r*.05), (x+r*.45, y-r*.55),
                 (x+r*1.2, y+r*.3)), 5, -5)
        ellipse(c, x, y, r, r*.65, style, -4, math.pi, TAU)
        for ray in range(5):
            a = math.pi+ray*math.pi/4
            c.line((x+math.cos(a)*r*1.2, y+math.sin(a)*r*.78),
                   (x+math.cos(a)*r*1.45, y+math.sin(a)*r*.95), 6, -4)


def ceremony(c, t, theme, cue, strength, style, board=None, viewport=None):
    p = cue.phase(t)
    board = board or game_layout(c.context.width, c.context.height).board
    bx, by = board; rows = cue.coords or (21,)
    origin = by+1+sum(rows)/len(rows)-2
    if cue.name == 'clear':
        clear(c, theme, rows, board, p, strength, style)
        return
    for side in (-1, 1):
        x = (bx-9 if side < 0 else bx+31) if viewport else (c.context.width-1)*(.14 if side < 0 else .86)
        if cue.name == 'bloom' and cue.variant == 'spin':
            spin(c, theme, x, origin, p, strength, style, side)
        elif theme == 'abyss':
            abyss_ceremony(c, cue.name, x, c.context.height, p, strength, style, origin)
        else:
            aurora_ceremony(c, cue.name, x, c.context.height, p, strength, style, origin)
