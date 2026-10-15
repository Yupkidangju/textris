"""유한한 문자 면·반사·거리층. 시간은 표시 전용이며 캐시는 호출자가 소유한다."""
import math

TAU = math.tau


def samples(canvas, maximum, minimum=12):
    return max(minimum, int(maximum * max(.15, min(1., canvas.context.quality))))


def shade(canvas, x, y, light, style=3, depth=6, hatch=False):
    if not canvas.accepts(round(x), round(y)):
        return
    ramp = ' .:-=+*#@' if canvas.context.ascii_mode else ' ░▒▓█'
    index = max(1, min(len(ramp)-1, int(light*(len(ramp)-1))))
    glyph = ramp[index]
    if hatch and (round(x)+round(y)) % 3 == 0:
        glyph = '/' if round(x) % 2 else '\\'
    canvas.put(x, y, glyph, style, depth)


def render_surfaces(c, t, theme):
    if theme in ('abyss','aurora'):
        from .theme_nature import abyss_surface, aurora_surface
        (abyss_surface if theme=='abyss' else aurora_surface)(c,t)
    else:
        globals()[theme](c, t)
        from .theme_atmosphere import render_detail
        render_detail(c,t,theme)
    if c.context.width < 95 or c.context.height < 34:
        compact(c, t, theme)


def cathedral(c, t):
    w,h=c.context.width-1,c.context.height
    cx,cy=w/2,max(4,h*.20);r=min(w*.21,h*.43)
    # 유리 조각은 납선 뒤에서 색 없이도 면과 방사형 이음새를 남긴다.
    for y in range(max(0,int(cy-r*.48)),min(h,int(cy+r*.48)+1)):
        for x in range(max(0,int(cx-r)),min(w,int(cx+r)+1)):
            dx,dy=(x-cx)/r,(y-cy)/(r*.48)
            d=dx*dx+dy*dy
            if not .06<d<.83 or not c.accepts(x,y): continue
            a=math.atan2(dy,dx);sector=int((a+math.pi)*6/math.pi)
            light=.3+.55*(.5+.5*math.sin(a*3+t*.17))*(1-d*.4)
            shade(c,x,y,light, (3,6,7,8)[sector%4],4)
    # 색유리에서 내려오는 광선과 젖은 석재 반사는 희박한 면으로 제한한다.
    for side in (-1,1):
        center=cx+side*w*.34
        for y in range(int(h*.35),h-4,2):
            for dx in range(-3,4):
                if (dx+y)%3: continue
                x=center+dx+math.sin(y*.12+t*.15)*2
                shade(c,x,y,.25+.4*(1-abs(dx)/4),12 if side<0 else 13,11)
        for y in range(h-6,h-2):
            for dx in range(-7,8):
                if (dx+y)%2: continue
                shade(c,center+dx+math.sin(t*.2+y)*1.5,y,
                      .3+.4*(1-abs(dx)/8),8 if y%2 else 6,8)


def cyberpunk(c,t):
    w,h=c.context.width-1,c.context.height;cx=w/2
    for side in (-1,1):
        for tower in range(4):
            x=(2+tower*5) if side<0 else w-3-tower*5
            roof=int(h*(.24+(tower*3%5)*.055))
            for y in range(roof,h-5):
                for dx in range(4):
                    xx=x+side*dx
                    light=.28+.15*dx
                    lit=(y+int(t*.7)+tower)%6==0 and dx in (1,2)
                    shade(c,xx,y,.95 if lit else light,4 if lit else 6 if dx<2 else 2,6+tower)
            # 광고판은 기하 윤곽과 움직이는 데이터 바를 함께 갖는다.
            yy=roof+4
            c.curve(((x,yy),(x+side*6,yy),(x+side*6,yy+2),(x,yy+2),(x,yy)),7,2)
            for dx in range(1,5):
                c.put(x+side*dx,yy+1,'=' if (dx+int(t*2))%4 else ':',4,1)
            for y in range(h-5,h-1):
                for dx in range(4):
                    if (dx+y+tower)%2:
                        shade(c,x+side*dx+math.sin(y+t)*1.5,y,.3+.2*(h-y)/5,7,5)
    # 비의 거리층은 분산된 결정적 위치와 다른 속도를 사용한다.
    for i in range(samples(c,52,12)):
        x=(i*29.31+t*(.08+i%3*.03))%w
        y=(i*13.7+t*(2+i%3))%h
        c.line((x,y),(x-.35,y+.4+(i%3)*.3),2 if i%3 else 6,10-i%3)


def space(c,t):
    w,h=c.context.width-1,c.context.height
    # 성운은 전경 행성보다 먼 깊이에서 큰 덩어리와 빈 틈을 함께 만든다.
    step=1 if c.context.quality>.65 else 2
    for y in range(2,h-2,step):
        for x in range(1,w,2):
            if not c.accepts(x,y): continue
            wave=math.sin(x*.08+y*.22+t*.025)+math.sin(x*.13-y*.17-t*.04)
            if wave>1.25 and (x+y)%3:
                shade(c,x,y,.25+(wave-1.25)*.55,6 if y<h/2 else 2,14)
    for layer in range(3):
        for i in range(samples(c,24,8)):
            x=(i*41.71+layer*11+t*.04*(layer+1))%w
            y=(i*17.39+layer*7)%h
            c.put(x,y,'+' if layer==2 and i%5==0 else '.',2+layer,12-layer)


def fire(c,t):
    w,h=c.context.width-1,c.context.height;cx=w/2
    for side in (-1,1):
        center=cx+side*w*.36;radius=min(13,w*.12)
        step=1 if c.context.quality>.6 else 2
        for y in range(3,h-3,step):
            u=(h-3-y)/max(1,h-6)
            width=radius*(1-u)**.6
            sway=math.sin(u*9-t*.9+side)*u*5
            for dx in range(-int(width),int(width)+1):
                if not c.accepts(round(center+dx+sway),y): continue
                core=1-abs(dx)/max(1,width)
                noise=math.sin(dx*1.3+y*.7-t*2)*.12
                heat=max(.1,core*(1-u*.65)+noise)
                if heat<.18: continue
                shade(c,center+dx+sway,y,heat,9 if heat>.8 else 4 if heat>.5 else 6,3)
        # 용암의 밝은 갈라짐은 분출하는 화염과 다른 수평 흐름이다.
        for y in range(h-4,h-1):
            for dx in range(-int(radius),int(radius)+1):
                heat=.3+.6*(.5+.5*math.sin(dx*.6+t*.6+y))
                shade(c,center+dx,y,heat,9 if heat>.75 else 6,2)
        c.curve(((center+math.sin(j*.35+t)*2,h*.3+j*.4)
                 for j in range(samples(c,45))),2,8)


def crt(c,t):
    w,h=c.context.width-1,c.context.height;cx=w/2
    n=samples(c,100,24)
    # 과거 프레임 버퍼를 쌓지 않는 3개의 고정 나이 인광층은 seek도 결정적이다.
    for side in (-1,1):
        x=cx+side*w*.365;r=min(w*.11,13);y=h*.5
        for age in (0.36,.18,0):
            phase=t-age
            for j in range(n):
                a=j*TAU/n
                xx=x+math.sin(a*3+phase*.23)*r*.85
                yy=y+math.sin(a*2)*6
                shade(c,xx,yy,.3 if age>.2 else .55 if age else .95,
                      2 if age else 4,2+age)
        sweep=(t*4)%max(1,h-8)+4
        for yy in range(int(sweep)-2,int(sweep)+1):
            for xx in range(int(x-r+1),int(x+r)):
                if (xx+yy)%2:
                    shade(c,xx,yy,.3+(yy-int(sweep)+2)*.22,3,5)


def mono(c,t):
    w,h=c.context.width-1,c.context.height;cx=w/2
    for side in (-1,1):
        center=cx+side*w*.36;cy=h*.51;r=min(13,w*.11)
        # 접힌 판화 면의 명암은 색상이 없어도 잉크 밀도와 교차 해칭으로 유지된다.
        for y in range(int(cy-r*.65),int(cy+r*.65)+1):
            half=max(0,r*(1-abs(y-cy)/(r*.7)))
            for dx in range(-int(half),int(half)+1):
                light=.3+.6*(dx+half)/max(1,2*half)
                shade(c,center+dx, y,light,5 if dx>0 else 6,2,hatch=True)
        offset=math.sin(t*.15)*1.5
        c.curve(((center-r+offset,cy),(center+offset,cy-r*.7),
                 (center+r+offset,cy),(center+offset,cy+r*.7),(center-r+offset,cy)),2,4)


def compact(c,t,theme):
    """작은 창의 열 0/마지막 여백과 상하 띠에서 큰 장면의 미술 언어를 유지한다."""
    w,h=c.context.width-1,c.context.height
    patterns={
        'cathedral':('/\\','<>','||','/\\'), 'cyberpunk':('[]','==','|:','[]'),
        'space':('.*','()','+.', '()'), 'fire':('/^','^^','~^','~~'),
        'crt':('+-','|=','-+','::'), 'mono':('/\\','##','\\/','//'),
        'abyss':('()','~~',':o',')('), 'aurora':('/\\','*+','|:', '\\/'),
    }
    motif=patterns[theme]
    for side in (-1,1):
        x=0 if side<0 else w-2
        for y in range(3,h-3):
            text=motif[(y//3+int(t*.2))%len(motif)]
            for dx,ch in enumerate(text): c.put(x+dx,y,ch,6 if y%3 else 4,0)
    # 상단 문장은 HUD 보호 영역 사이의 빈 곳에만 나타난다.
    for x in range(max(0,w//2-12),min(w,w//2+13)):
        c.put(x,2,motif[(x//2)%len(motif)][x%2],4,0)


def spin_ceremony(c,t,theme,cue,board,strength,style,viewport=None):
    """강한 삭제의 회전 변주는 같은 행의 일제 분출과 다른 각운동을 갖는다."""
    from .art import game_layout
    bx,by=board or game_layout(c.context.width,c.context.height).board
    rows=cue.coords or (21,)
    y=by+1+sum(rows)/len(rows)-2
    p=cue.phase(t);r=(4+12*p)*strength
    for side in (-1,1):
        x=(bx-9 if side<0 else bx+31) if viewport else (c.context.width-1)*(.14 if side<0 else .86)
        for j in range(6):
            a=j*TAU/6+p*TAU*side
            points=[]
            n=samples(c,24,8)
            for k in range(n+1):
                u=k/n;radius=r*(.3+.7*u);angle=a+u*.9
                points.append((x+math.cos(angle)*radius,y+math.sin(angle)*radius*.45))
            c.curve(points,style if j%2 else 6,-4)
            xx,yy=points[-1]
            c.put(xx,yy,{'cyberpunk':'=','space':'+','fire':'^','crt':'|','mono':'/'}[theme],5,-5)
