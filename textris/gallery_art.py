"""갤러리의 연속 곡선, 입체 조각, 유한 시간 문자 연출."""
import math
from functools import lru_cache

from .art import ArtCanvas
from .cathedral import CathedralScene
from .scenes import BACKGROUNDS, EFFECTS

TAU = math.tau


def _ring(c, x, y, r, style=4, depth=0, tilt=.48, phase=0, petals=0):
    count = max(32, min(900, int(abs(r) * 14)))
    for i in range(count+1):
        a=i*TAU/count
        rr=r*(1+petals*math.cos(6*a+phase))
        c.dot(x+math.cos(a)*rr,y+math.sin(a)*rr*tilt,style,depth)


def _wave(c, height, width, style, depth):
    for i in range(width*2):
        x=i*.5
        c.dot(x,height(x),style,depth)



@lru_cache(maxsize=24)
def _letters(word):
    # effects가 이 모듈을 불러오는 경우에도 초기화 순환이 생기지 않는다.
    from .effects import art
    return tuple((x, y) for y, row in enumerate(art(word, True))
                 for x, glyph in enumerate(row) if glyph != ' ')


class GalleryArt:
    def __init__(self):
        self.cathedral = CathedralScene()
        self._cached = {}

    def render(self, context, t, name, age=None, intensity=.75, density=.75, flash=True):
        c = ArtCanvas(context)
        if context.width < 3 or context.height < 2:
            return c
        intensity = max(0., min(1., intensity))
        density = max(0., min(1., density))
        if age is not None or name not in BACKGROUNDS:
            if name not in EFFECTS or age is None or not 0 <= age < 2 or intensity == 0:
                return c
            self._effect(c, name, age/2, intensity, density, flash)
        elif name == 'cathedral':
            return self.cathedral.render(context, t, intensity=intensity, density=density, flash=flash)
        else:
            tick = math.floor(t * 12)
            key = (context, tick, density)
            cached = self._cached.get(name)
            if cached is not None and cached[0] == key:
                c.cells = cached[1].copy()
            else:
                self._background(c, name, tick / 12, density)
                self._cached[name] = (key, c.cells.copy())
        return c

    @staticmethod
    def _stars(c, t, density, style=2):
        w, h = c.context.width-1, c.context.height
        for i in range(int(18+65*density)):
            x = (i*47.173 + t*(.08+i%3*.025)) % w
            y = (i*i*7.731) % h
            c.put(x, y, '+' if i%17 == 0 else '.', style if i%7 else 5, 15)

    def _background(self, c, name, t, density):
        w, h = c.context.width-1, c.context.height
        cx, cy, radius = w*.5, h*.48, min(w*.32, h*.72)
        if name in ('cube', 'tetromino', 'torus'):
            self._stars(c, t, density*.3)
            _ring(c, cx, h*.84, radius*1.2, 1, 8, .15)
            if name == 'torus':
                self._torus(c, t, cx, cy, radius)
            else:
                blocks = [(0,0,0)] if name == 'cube' else [(-1,0,0),(0,0,0),(1,0,0),(0,-1,0)]
                for offset in blocks:
                    self._cube(c, t, cx, cy, radius, offset, .95 if name == 'cube' else .43)
        elif name in ('mandelbrot', 'julia', 'metaball', 'plasma'):
            self._field(c, name, t)
        elif name in ('logo', 'reflection'):
            self._stars(c, t, density*.4)
            self._text(c, 'TEXTRIS', cx, cy-4, style=9)
            if name == 'logo':
                for r in (radius*.85, radius, radius*1.15):
                    _ring(c, cx, cy, r, 2, 4, .6, t, .06)
            else:
                for x,y in _letters('TEXTRIS'):
                    c.put(cx-13+x+math.sin(y*1.5+t)*2, cy+5-y*.65, '~' if c.context.ascii_mode else '░', 2, 4)
                for j in range(7):
                    yy=cy+5+j*1.2
                    c.curve(((x,yy+math.sin(x*.16+t+j)*.25) for x in range(int(w*.15),int(w*.85))),1,6)
        elif name == 'rain':
            for i in range(max(8,int(w*.4*density))):
                x = (i*17.7)%w
                head = (t*(3+i%5)+i*9.7)%(h+12)-6
                for j in range(9):
                    c.put(x,head-j,'01:/|+'[(i*3+j)%6],5 if j==0 else 3 if j<3 else 1,2+j*.2)
                c.line((x+.3,head-8),(x+.3,head-2),1,5)
            for j in range(4):
                _ring(c,w*(.15+j*.23),h*.88,2+(t+j)%2*4,2,7,.12)
        elif name in ('grid', 'tunnel', 'warp'):
            if name == 'grid':
                horizon=h*.4
                _ring(c,cx,horizon-3,radius*.36,8,6,.7)
                for i in range(-7,8):
                    c.line((cx+i*.65,horizon),(cx+i*w*.14,h),3 if i%3==0 else 1,7)
                for i in range(9):
                    z=(i+t*.6)%9/9
                    yy=horizon+(h-horizon)*z*z
                    c.line((0,yy),(w,yy),2,6)
            elif name == 'tunnel':
                for j in range(8):
                    r=radius*((j+t*.7)%8/6)**1.7+.5
                    _ring(c,cx,cy,r,3 if j%3==0 else 1,12-j,.6,t*.2,.07)
                for i in range(12):
                    a=i*TAU/12+t*.08
                    c.line((cx+math.cos(a),cy+math.sin(a)),(cx+math.cos(a)*w,cy+math.sin(a)*w*.6),2,15)
            else:
                for i in range(int(25+65*density)):
                    a=i*2.39996
                    r=2+((i*.173+t*.65)%1)**2*w*.65
                    tail=max(1,r*.2)
                    c.line((cx+math.cos(a)*r,cy+math.sin(a)*r*.48),(cx+math.cos(a)*(r-tail),cy+math.sin(a)*(r-tail)*.48),5 if i%6==0 else 3,i%5)
        elif name in ('aurora','fluid','braille'):
            self._stars(c,t,density*.5)
            if name == 'aurora':
                for band in range(8):
                    _wave(c,lambda x:h*.36+math.sin(x*.045+t*.18)*h*.2+math.sin(x*.11-t*.3)*1.8+band*.6,w,(1,2,3,4,5,4,3,2)[band],band)
                for band in range(3):
                    c.curve(((x,h*.88+math.sin(x*.07+band)*2-band*1.8) for x in range(w)),1,10)
            elif name == 'fluid':
                for band in range(10):
                    _wave(c,lambda x:cy+(band-4.5)*1.8+math.sin(x*.065+t*.5+band*.22)*4+math.sin(x*.13-t*.4)*1.5,w,3 if band%4==0 else 1+band%3,band*.2)
            else:
                for layer in range(3):
                    for i in range(1001):
                        a=i*TAU/1000
                        c.dot(cx+radius*math.sin(a*3+t*.15+layer*.09),cy+radius*.49*math.sin(a*4+layer*.16),2+layer%4,layer)
        elif name == 'space':
            self._stars(c,t,density)
            self._sphere(c,cx,cy,radius*.72,t)
            for j in range(3):
                _ring(c,cx,cy,radius*(1.1+j*.12),8 if j==1 else 2,3,.22)
            angle=t*.16
            self._sphere(c,cx+math.cos(angle)*radius*1.6,cy+math.sin(angle)*radius*.5,radius*.15,t)
        elif name == 'city':
            self._stars(c,t,density*.3)
            _ring(c,w*.76,h*.25,h*.13,8,12,.9)
            for layer in range(3):
                bw=5+layer*3
                for i in range(int(w/bw)+2):
                    x=i*bw-(t*(.15+layer*.1))%bw
                    bh=3+((i*17+layer*11)%13)*(layer+1)*.45
                    top=h*.85-bh
                    c.line((x,h*.85),(x,top),2+layer,5-layer)
                    c.line((x,top),(x+bw-1,top),2+layer,5-layer)
                    c.line((x+bw-1,top),(x+bw-1,h*.85),1,5-layer)
                    for yy in range(int(top)+2,int(h*.85),2):
                        for xx in range(int(x)+2,int(x+bw)-1,3):
                            if (xx+yy+i)%4: c.put(xx,yy,':' if c.context.ascii_mode else '▪',8 if layer==2 else 2,4-layer)
                    for j in range(3):
                        c.line((x,h*.89+j),(x+bw*.6,h*.89+j),1,8)

    @staticmethod
    def _project(x,y,z,t,cx,cy,r):
        a,b=t*.35,t*.21+.3
        x,z=x*math.cos(a)-z*math.sin(a),x*math.sin(a)+z*math.cos(a)
        y,z=y*math.cos(b)-z*math.sin(b),y*math.sin(b)+z*math.cos(b)
        scale=r/(3.4+z)
        return cx+x*scale,cy+y*scale*.5,z

    def _cube(self,c,t,cx,cy,r,offset,edge):
        points=[self._project((offset[0]+x)*edge,(offset[1]+y)*edge,(offset[2]+z)*edge,t,cx,cy,r*2) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        for i,a in enumerate(points):
            for bit in (1,2,4):
                j=i^bit
                if i<j:
                    b=points[j]
                    c.line(a[:2],b[:2],5 if (a[2]+b[2])<0 else 2,(a[2]+b[2])/2)
        # 면 내부의 평행 해칭은 회전 중에도 체적을 유지한다.
        for face in ((0,1,2,3),(0,1,4,5),(0,2,4,6)):
            a,b,d,e=(points[i] for i in face)
            for k in range(1,7):
                u=k/7
                p=(a[0]*(1-u)+b[0]*u,a[1]*(1-u)+b[1]*u)
                q=(d[0]*(1-u)+e[0]*u,d[1]*(1-u)+e[1]*u)
                c.line(p,q,1+face[2]%3,1+(a[2]+e[2])/2)

    def _torus(self,c,t,cx,cy,r):
        for i in range(64):
            a=i*TAU/64
            for j in range(24):
                b=j*TAU/24
                x,y,z=self._project((1+.38*math.cos(b))*math.cos(a),.38*math.sin(b),(1+.38*math.cos(b))*math.sin(a),t,cx,cy,r*2)
                light=(math.cos(a-t*.35)*math.cos(b)+math.sin(b)+2)/4
                glyph='.,:;=+*#%@'[min(9,int(light*9))]
                c.put(x,y,glyph,2 if light<.4 else 4 if light<.7 else 5,z)

    @staticmethod
    def _sphere(c,cx,cy,r,t):
        for yy in range(-math.ceil(r*.5),math.ceil(r*.5)+1):
            for xx in range(-math.ceil(r),math.ceil(r)+1):
                q=(xx/r)**2+(yy/(r*.5))**2
                if q>1: continue
                z=math.sqrt(1-q)
                light=max(0,(-xx/r*.5-yy/r*.8+z*.65))
                bands=.1*math.sin(yy*.8+t+z*2)
                level=max(0,min(8,int((light+bands)*8)))
                c.put(cx+xx,cy+yy,'.:-=+*#%@'[level],2 if level<3 else 3 if level<6 else 5,-z)

    @staticmethod
    def _field(c,name,t):
        w,h=c.context.width-1,c.context.height
        shades=' .,:;irsXA253hMHGS#9B&@'
        for y in range(0,h,2):
            ny=(y-h*.5)/(h*.46)
            for x in range(0,w,2):
                nx=(x-w*.5)/(w*.4)
                if name in ('mandelbrot','julia'):
                    zoom=1.5/(1+.12*math.sin(t*.15))
                    z=complex(nx*zoom-.45,ny*zoom)
                    cc=complex(-.745,.186+.02*math.sin(t*.25)) if name=='julia' else z
                    if name=='mandelbrot': z=0j
                    n=0
                    while z.real*z.real+z.imag*z.imag<16 and n<32:
                        z=z*z+cc; n+=1
                    if n==32: continue
                    value=min(1,n/22)
                elif name=='metaball':
                    field=sum(.18/(.035+(nx-math.sin(t*.4+i*2)*.7)**2+(ny-math.cos(t*.3+i*2.5)*.5)**2) for i in range(3))
                    if field<.72: continue
                    value=min(1,(field-.7)*.65)
                else:
                    value=(math.sin(nx*4+t*.5)+math.sin(ny*5-t*.4)+math.sin(math.hypot(nx,ny)*7-t*.6)+3)/6
                    # 등고선 사이를 비워 플라스마 구름의 흐름을 읽을 수 있게 한다.
                    if int(value*20)%4>1: continue
                k=max(1,min(len(shades)-1,int(value*(len(shades)-1))))
                style = 2 if value<.3 else 3 if value<.65 else 5
                c.put(x,y,shades[k],style,3)
                c.put(x+1,y,shades[k],style,3)
                c.put(x,y+1,shades[k],style,3)
                c.put(x+1,y+1,shades[k],style,3)

    @staticmethod
    def _text(c,word,cx,cy,style=5,transform=None):
        width=len(word)*4-1
        for x,y in _letters(word):
            px,py=cx-width/2+x,cy+y
            if transform: px,py=transform(px,py,x,y)
            c.put(px+1,py+1,'.' if c.context.ascii_mode else '░',1,3)
            c.put(px,py,'#' if c.context.ascii_mode else '█',style,-2)

    def _effect(self,c,name,p,intensity,density,flash):
        w,h=c.context.width-1,c.context.height
        cx,cy=w*.5,h*.5
        r=min(w*.35,h*.8)*(.65+.35*intensity)
        strength=intensity*math.sin(math.pi*min(.99,p+.03))
        count=max(8,int((12+30*density)*max(.25,c.context.quality)))
        hot=5 if flash else 3
        if name in ('impact','echoes','ripple','elastic'):
            rings=1 if name=='impact' else 5 if name=='echoes' else 8 if name=='ripple' else 3
            for j in range(rings):
                rr=r*(.08+p)*(1-j*.12)
                if name=='elastic': rr*=1+.25*math.sin(p*20-j)*math.exp(-p*2)
                _ring(c,cx,cy,rr,hot if j==0 else 2+j%3,-1,.42 if name=='ripple' else .58,p*6,.08 if name=='elastic' else 0)
            if name=='impact':
                for i in range(16):
                    a=i*TAU/16
                    c.line((cx+math.cos(a)*r*p,cy+math.sin(a)*r*p*.5),(cx+math.cos(a)*r*(p+.18),cy+math.sin(a)*r*(p+.18)*.5),9,-2)
        elif name in ('typewriter','assemble','odometer','victory','collapse','glitch'):
            word='VICTORY' if name=='victory' else '012345' if name=='odometer' else 'TEXTRIS'
            if name=='typewriter': word=word[:max(1,int(p*12))]
            if name=='odometer': word=''.join(str((int(p*32)+i*3)%10) for i in range(6))
            def transform(px,py,x,y):
                if name=='assemble':
                    d=max(0,1-p*2.4)**2
                    return px+math.sin(x*7+y)*r*d,py+math.cos(x+y*3)*h*.4*d
                if name=='collapse':
                    d=max(0,p-.25)**2
                    return px+(px-cx)*d,py+(y+2)*d*8
                if name=='glitch': return px+(math.sin(int(p*18)+y*7)*5 if y%2 else 0),py
                return px,py
            self._text(c,word,cx,cy-2,9 if name=='victory' else hot,transform)
            if name=='typewriter': c.line((cx+len(word)*2+1,cy-2),(cx+len(word)*2+1,cy+2),9,-3)
            if name=='victory':
                for side in (-1,1):
                    for i in range(9):
                        a=-1+i*.24
                        x=cx+side*(18+3*math.cos(a)); y=cy+math.sin(a)*6
                        c.line((x,y),(x+side*3,y-1.5),9,-1)
                _ring(c,cx,cy,r*(.75+p*.2),8,4,.46)
            if name=='glitch':
                for j in range(6): c.line((cx-r+j*4,cy-7+j*2.5),(cx-r+j*4+7,cy-7+j*2.5),2,0)
        elif name in ('blackhole','vortex','braille'):
            arms=4 if name=='blackhole' else 6 if name=='vortex' else 3
            for arm in range(arms):
                points=[]
                for i in range(100):
                    u=i/99
                    a=u*(TAU*1.8)+arm*TAU/arms+p*5
                    rr=r*(.1+u*.85)*(1-p*.3)
                    if name=='braille': rr*=.65+.3*math.sin(a*3+p*4)
                    points.append((cx+math.cos(a)*rr,cy+math.sin(a)*rr*.5))
                c.curve(points,3+arm%3,arm*.1)
            if name=='blackhole':
                for y in range(int(cy-2),int(cy+3)):
                    for x in range(int(cx-4),int(cx+5)):
                        if ((x-cx)/4)**2+((y-cy)/2)**2<1: c.put(x,y,' ',0,-5)
                _ring(c,cx,cy,5,9,-6,.45)
        elif name in ('lightning','electric','cracks','chain','laser'):
            if name=='laser':
                for k in range(5):
                    yy=cy+(k-2)*.35
                    c.line((cx-r,yy),(cx+r,yy),hot if k==2 else 2,-k)
                for side in (-1,1): _ring(c,cx+side*r,cy,3+strength*3,9,-6,.8)
            else:
                branches=6 if name=='cracks' else 3 if name=='lightning' else 8
                for j in range(branches):
                    a=j*TAU/branches+(0 if name=='cracks' else p*.6)
                    points=[]
                    for k in range(13):
                        u=k/12
                        jitter=math.sin(k*13+j*7+int(p*12))*(1.5 if name!='chain' else .4)
                        rr=r*u*(.3+p)
                        points.append((cx+math.cos(a)*rr+math.sin(a)*jitter,cy+math.sin(a)*rr*.5+math.cos(a)*jitter*.5))
                    c.curve(points,8 if name=='cracks' else hot,-2)
                    if name=='chain':
                        for x,y in points[::2]: _ring(c,x,y,1.5,9,-3,.65)
                    elif name=='electric':
                        _ring(c,*points[-1],2.5,4,-3,.5)
                    else:
                        for k in (5,8):
                            x,y=points[k]
                            c.line((x,y),(x+math.cos(a+.7)*r*.2,y+math.sin(a+.7)*r*.1),2,-1)
        elif name in ('fire','smoke','embers','gold','ice','shatter','ricochet'):
            if name in ('fire','smoke'):
                for j in range(8):
                    base=cx+(j-3.5)*r*.16
                    c.curve(((base+math.sin(u*8+j+p*5)*u*r*.12,cy+r*.3-u*r*.7) for u in (k/60 for k in range(61))),8+j%3 if name=='fire' else 1+j%3,j*.1)
            for i in range(count):
                a=i*2.39996
                speed=.25+(i*7%19)/19
                travel=(.1+p)*r*speed
                x=cx+math.cos(a)*travel
                y=cy+math.sin(a)*travel*.5
                if name in ('embers','fire','smoke'):
                    x=cx+math.sin(i*17+p*4)*r*.5*(1-p*.3)
                    y=cy+r*.25-((i*.137+p*.7)%1)*r*.8
                elif name in ('gold','shatter'): y+=p*p*r*.3
                elif name=='ricochet': x=cx+math.sin(a+p*8)*r*.85; y=cy+math.cos(a+p*5)*r*.35
                if name=='ice':
                    for k in range(3):
                        angle=k*math.pi/3
                        c.line((x-math.cos(angle)*1.8,y-math.sin(angle)*.9),(x+math.cos(angle)*1.8,y+math.sin(angle)*.9),5,-1)
                elif name=='shatter':
                    c.curve(((x,y-1),(x+2,y+.7),(x-1,y+.4),(x,y-1)),3+i%3,-i*.01)
                elif name=='smoke':
                    _ring(c,x,y,1+p*3,1+i%3,i*.01,.45)
                else:
                    c.line((x,y),(x-math.cos(a)*(1+p*2),y-math.sin(a)*(.5+p)),9 if name in ('gold','embers','fire') else 4,-1)
                    if i%5==0: c.put(x,y,'+',hot,-2)
