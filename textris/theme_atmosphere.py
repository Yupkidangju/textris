"""기존 무대의 얇은 시간층. 잔상은 고정된 나이만 역산하고 프레임을 저장하지 않는다."""
import math

from .theme_surfaces import samples

TAU = math.tau


def render_detail(c, t, theme):
    globals()[theme](c, t)


def cathedral(c, t):
    w, h = c.context.width-1, c.context.height; cx = w/2
    count = samples(c, 24, 6)
    for side in (-1, 1):
        # 아치의 광점은 고정 석재 위를 이동하고, 향 연기는 외곽에서만 솟는다.
        for i in range(3+int(7*c.context.quality)):
            u = ((i*.137+t*.018) % .86)+.07
            x = cx+side*w*.47*(math.sin(u*math.pi/2)**.85)
            y = 1+(h*.56-1)*(1-math.cos(u*math.pi/2))
            c.put(x, y, '+' if i % 4 == 0 else '.', 8 if i % 4 == 0 else 3, 4)
        x = cx+side*w*.43
        for age in ((.4, 0) if c.context.quality > .7 else (0,)):
            c.curve(((x+math.sin(u*7-(t-age)*.55+side)*u*2,
                      h-5-u*h*.29) for u in (i/count for i in range(count+1))),
                    2 if age else 6, 9+age)
        phase = (t*.11+side*.2) % 1
        radius = 2+phase*6
        c.curve(((cx+side*w*.34+math.cos(a)*radius,
                  h*.72+math.sin(a)*radius*.23)
                 for a in (i*TAU/count for i in range(count+1))), 2, 10)


def cyberpunk(c, t):
    w, h = c.context.width-1, c.context.height
    for side in (-1, 1):
        for track in range(2+int(2*c.context.quality)):
            x = 3+track*6 if side < 0 else w-4-track*6
            y = 4+(t*(1+track*.17)+track*5) % max(1, h-12)
            c.curve(((x, y-2), (x, y), (x+side*2, y), (x+side*2, y+1)), 6, 1)
            c.put(x+side*2, y+1, '=', 4, 0)
            c.put(x, y-2.7, ':', 2, 2)
        center = w*(.13 if side < 0 else .87)
        for age in (1, 0):
            offset = math.sin((t-age*.2)*.8+side)*3
            for fragment in range(3):
                xx = center-8+fragment*6+offset
                yy = h-4+age
                c.line((xx, yy), (xx+3+math.sin(t*.4+fragment), yy), 6 if age else 7, 2+age)


def space(c, t):
    w, h = c.context.width-1, c.context.height
    for layer in range(1+int(2*c.context.quality)):
        for side in (-1, 1):
            # 꼬리의 길이와 속도를 거리별로 바꾸며 화면 끝에서 긴 연결선이 생기지 않는다.
            phase = (t*(.035+layer*.012)+layer*.31+(side+1)*.19) % 1
            x = w*(.04 if side < 0 else .79)+phase*w*.16
            y = 3+phase*(h-8)
            tail = 2+layer*1.4
            c.line((x-tail*.6, y-tail*.8), (x, y), 2+layer, 11-layer)
            c.put(x, y, '+' if layer == 2 else '.', 4 if layer == 2 else 3, 9-layer)
    for i in range(4):
        a = i*TAU/4+t*.025
        x = w/2+math.cos(a)*w*.44; y = h*.45+math.sin(a)*h*.34
        c.put(x, y, 'o', 4, 6)
        c.put(w/2+math.cos(a-.045)*w*.44, h*.45+math.sin(a-.045)*h*.34, '.', 2, 7)


def fire(c, t):
    w, h = c.context.width-1, c.context.height
    count = samples(c, 26, 7)
    for side in (-1, 1):
        center = w*(.14 if side < 0 else .86)
        for i in range(2+int(7*c.context.quality)):
            phase = (t*(.085+i*.003)+i*.193+side*.1) % 1
            x = center+math.sin(i*2.4+phase*4)*10
            y = h-5-phase*(h-8)
            c.put(x, y, '*' if phase < .35 else ':' if phase < .65 else '.',
                  9 if phase < .35 else 3 if phase < .65 else 2, 2)
            if c.context.quality > .7:
                c.put(x-.3, y+1.2, '.', 6, 4)
        for edge in (-1, 1):
            c.curve(((center+edge*(10+u*2)+math.sin(u*8-t*.9)*.7,
                      h-6-u*h*.7) for u in (i/count for i in range(count+1))), 2, 8)


def crt(c, t):
    w, h = c.context.width-1, c.context.height
    for side in (-1, 1):
        x = w/2+side*w*.365; r = min(w*.11, 13); y = h*.5
        for age in ((.22, .11, 0) if c.context.quality > .7 else (.11, 0)):
            phase = t-age; a = phase*.8 % TAU
            xx = x+math.sin(a*3+phase*.23)*r*.85
            yy = y+math.sin(a*2)*6
            c.put(xx, yy, '+' if age == 0 else '.', 5 if age == 0 else 6, .5+age)
        for row in range(3):
            yy = 5+(t*2.5+row*9) % max(1, h-10)
            xx = x-r+1+((int(t*1.5)+row) % 3)*r*.35
            c.line((xx, yy), (xx+3, yy), 2, 6)


def mono(c, t):
    w, h = c.context.width-1, c.context.height
    phase = (t*.35) % 3
    for side in (-1, 1):
        x = w/2+side*w*.36; y = h*.51; r = min(13, w*.11)
        for i in range(2+int(5*c.context.quality)):
            yy = y-r*.5+(i+phase)*r*.13
            half = max(0, r*(1-abs(yy-y)/(r*.7)))
            c.line((x-half, yy+.5), (x+half, yy-.5), 6, 1.7)
        for i in range(5):
            a = i*TAU/5+t*.024
            radius = r*(.7+.23*math.cos(a*5+t*.12))
            xx, yy = x+math.cos(a)*radius, y+math.sin(a)*radius*.7
            c.put(xx, yy, '*', 5, -.1)
            if c.context.quality > .7:
                c.put(xx+side, yy+.6, '.', 2, 2.2)
