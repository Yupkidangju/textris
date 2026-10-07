"""테마마다 다른 실루엣을 갖는 절차적 무대와 공통 성취 연출."""
import math
from .art import ArtCanvas
from .cathedral import CathedralScene

TAU=math.tau


class ThemeScene:
    def __init__(self):
        self.cathedral=CathedralScene()
        self._key=None
        self._ambient=None

    def render(self,context,t,theme,major=None,local=(),board=None,flash=True,
               intensity=.75,density=.75,motion_speed=1.):
        if theme=='cathedral':
            return self.cathedral.render(context,t,major,local,board,flash,intensity,density,motion_speed)
        c=ArtCanvas(context)
        stamp=math.floor(t*motion_speed*12)/12
        key=(context,stamp,theme,density)
        if key!=self._key:
            base=ArtCanvas(context)
            getattr(self,theme)(base,stamp)
            self.motes(base,stamp,theme,density)
            self._key,self._ambient=key,base.cells
        c.cells.update(self._ambient)
        if major: self.ceremony(c,t,theme,major,flash,intensity)
        if board:
            for cue in local: self.cathedral.local_effect(c,board,t,cue,intensity,flash)
        return c

    @staticmethod
    def motes(c,t,theme,density):
        # 무대 골격은 유지하고 밀도 설정은 미세 장식만 조절한다.
        w,h=c.context.width-1,c.context.height
        for i in range(int(48*density*c.context.quality)):
            x=(i*37.17+math.sin(t*.1+i)*2)%w
            y=(i*11.31-t*(.18 if theme=='fire' else .04))%h
            glyph='+' if i%9==0 else ':' if theme=='crt' else '.'
            c.put(x,y,glyph,6 if i%9==0 else 2,10)

    @staticmethod
    def ellipse(c,x,y,rx,ry,t=0,style=3,depth=0,steps=100):
        c.curve(((x+math.cos(a+t)*rx,y+math.sin(a+t)*ry)
                 for a in (i*TAU/steps for i in range(steps+1))),style,depth)

    def cyberpunk(self,c,t):
        w,h=c.context.width-1,c.context.height;cx=w/2;horizon=h*.65
        # 원근 도로와 계단식 초고층 실루엣을 한 소실점에 정렬한다.
        for side in (-1,1):
            for i in range(5):
                x=(2+i*4) if side<0 else w-3-i*4
                roof=h*(.22+((i*7)%5)*.07)
                c.curve(((x,h-4),(x,roof+2),(x+side*2,roof+2),(x+side*2,roof),(x+side*5,roof),(x+side*5,h-4)),
                        3 if i%2 else 6,4+i)
                for y in range(int(roof+3),h-5,3):
                    c.put(x+side,y,'=' if c.context.ascii_mode else '▪',4 if (y+i+int(t))%7==0 else 2,3+i)
            for lane in range(1,7):
                c.line((cx+side*lane*2,horizon),(cx+side*lane*14,h-3),2,8)
            for y in range(3,h-4,7):
                c.line((side*1+cx+side*22,y),(cx+side*26,y-2),7,6)
        for i in range(6):
            p=((i+t*.3)%6)/6
            y=horizon+(h-horizon)*p*p
            c.line((1,y),(w-2,y),6,9)
        for i in range(3):
            r=5+i*2
            points=[]
            for x,y,z in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1),(-1,-1,1)):
                a=t*.12+i*.15;xx=x*math.cos(a)+z*math.sin(a)
                points.append((cx+xx*r,h*.12+y*r*.35+z*.6))
            c.curve(points,4 if i==0 else 7,1+i)

    def space(self,c,t):
        w,h=c.context.width-1,c.context.height;cx=w/2
        # 타원 궤도와 명암 구체는 문자 밀도만으로도 구분된다.
        self.ellipse(c,cx,h*.45,w*.48,h*.39,t*.03,2,8,160)
        self.ellipse(c,cx,h*.45,w*.44,h*.34,-t*.02,6,7,140)
        for side in (-1,1):
            x=cx+side*w*.36;y=h*.51;r=min(12,w*.105)
            self.planet(c,x,y,r,t+side*2)
            for i in range(2):
                tilt=.25+side*.25+i*.15
                points=[]
                for j in range(121):
                    a=j*TAU/120
                    xx=math.cos(a)*r*1.45;yy=math.sin(a)*r*.2
                    points.append((x+xx,y+yy+xx*tilt*.35))
                c.curve(points,9 if i==0 else 3,-2)
            for k in range(10):
                a=k*2.399+t*.025;rstar=(k%4+1)*4
                c.put(x+math.cos(a)*rstar,y+math.sin(a)*rstar*.75,'.' if k%3 else '+',2,9)
        self.ellipse(c,cx,h*.13,10,3.2,t,4,1)
        self.ellipse(c,cx,h*.13,5,4.1,-t,6,2)

    @staticmethod
    def planet(c,cx,cy,r,t):
        shades=' .:-=+*#%@' if c.context.ascii_mode else ' ·░▒▓█'
        for iy in range(-int(r/2),int(r/2)+1):
            for ix in range(-int(r),int(r)+1):
                nx,ny=ix/r,iy*2/r
                rr=nx*nx+ny*ny
                if rr>1: continue
                nz=math.sqrt(1-rr)
                light=max(.08,-nx*.5-ny*.25+nz*.7)
                band=math.sin(ny*20+nx*2+t*.14)*.1
                shade=min(len(shades)-1,max(1,int((light+band)*(len(shades)-1))))
                c.put(cx+ix,cy+iy,shades[shade],5 if light>.85 else 4 if light>.55 else 6 if light>.3 else 2,1-nz)

    def fire(self,c,t):
        w,h=c.context.width-1,c.context.height;cx=w/2
        for side in (-1,1):
            center=cx+side*w*.36
            for tongue in range(9):
                points=[]
                for i in range(49):
                    u=i/48
                    x=center+(tongue-4)*1.8*(1-u)+math.sin(u*7+t*.8+tongue*.3)*u*5
                    y=h-4-u*(h*.8-abs(tongue-4)*2)
                    points.append((x,y))
                c.curve(points,9 if tongue==4 else 4 if tongue%2 else 6,tongue*.1)
            self.ellipse(c,center,h*.6,min(10,w*.085),5,style=8,depth=4)
            for i in range(18):
                u=(t*.1+i*.061)%1
                x=center+math.sin(i*2.4+u*4)*8
                c.put(x,h-4-u*(h-8),'*' if i%4==0 else '.',9 if i%4==0 else 3,5)
        for ring in range(3):
            self.ellipse(c,cx,h*.12,8+ring*2,2.5+ring*.8,style=9 if ring==0 else 6,depth=ring)
        for ray in range(24):
            a=ray*TAU/24+t*.04
            c.line((cx+math.cos(a)*13,h*.12+math.sin(a)*4),
                   (cx+math.cos(a)*17,h*.12+math.sin(a)*6),3,2)

    def crt(self,c,t):
        w,h=c.context.width-1,c.context.height;cx=w/2
        for side in (-1,1):
            x=cx+side*w*.365;r=min(w*.11,13);y=h*.5
            c.curve(((x-r,y-8),(x+r,y-8),(x+r,y+8),(x-r,y+8),(x-r,y-8)),3,4)
            for grid in range(-2,3):
                c.line((x-r,y+grid*3),(x+r,y+grid*3),1,7)
            points=[]
            for i in range(241):
                a=i*TAU/240
                points.append((x+math.sin(a*3+t*.23)*r*.85,y+math.sin(a*2)*6))
            c.curve(points,4,1)
            for k in range(6):
                yy=4+k*5
                c.curve(((x-side*r,yy),(x-side*(r+3),yy),(x-side*(r+3),yy+2),(x-side*(r+6),yy+2)),2,6)
                c.put(x-side*(r+6),yy+2,'o',5,5)
            sweep=(t*4)%(h-8)+4
            c.line((x-r+1,sweep),(x+r-1,sweep),2,5)
        for i in range(3):
            c.curve(((cx-17+j*.4,3+i+math.sin(j*.15+t+i)*.8) for j in range(86)),4 if i==1 else 2,2)

    def mono(self,c,t):
        w,h=c.context.width-1,c.context.height;cx=w/2
        for side in (-1,1):
            x=cx+side*w*.36;y=h*.51;r=min(13,w*.11)
            for k in range(6):
                points=[]
                for i in range(101):
                    a=i*TAU/100
                    radius=r*(.7+.23*math.cos(a*5+k*.56+t*.12))
                    points.append((x+math.cos(a)*radius,y+math.sin(a)*radius*.7+k*.20))
                c.curve(points,5 if k in (0,5) else 6 if k%3 else 3,k*.1)
            for line in range(9):
                yy=h-7+line*.45
                c.line((x-r,yy),(x+r,yy-3),2,8)
        for i in range(5):
            size=5+i*3
            c.curve(((cx,1),(cx+size,5+i*.4),(cx,9+i*.4),(cx-size,5+i*.4),(cx,1)),
                    5 if i==4 else 6,5-i)

    def ceremony(self,c,t,theme,cue,flash,intensity):
        p=cue.phase(t);w,h=c.context.width-1,c.context.height;cx=w/2
        style=9 if flash and .15<p<.65 and intensity>.5 else 3
        if theme=='cyberpunk':
            for i in range(3):
                rx=(.12+p*.5)*w+i*2;ry=rx*.4
                c.curve(((cx-rx,h/2-ry),(cx+rx,h/2-ry),(cx+rx,h/2+ry),(cx-rx,h/2+ry),(cx-rx,h/2-ry)),style if i==0 else 6,-3)
        elif theme=='space':
            self.ellipse(c,cx,h*.48,w*(.15+p*.65),h*(.08+p*.4),style=style,depth=-3,steps=120)
            for i in range(24):
                a=i*TAU/24
                c.line((cx+math.cos(a)*w*.25,h/2+math.sin(a)*h*.3),
                       (cx+math.cos(a)*w*(.25+p*.5),h/2+math.sin(a)*h*(.3+p*.6)),6,-2)
        elif theme=='fire':
            for i in range(32):
                a=i*TAU/32+t*.1;r=w*(.15+p*.4)
                c.line((cx+math.cos(a)*r,h/2+math.sin(a)*r*.4),
                       (cx+math.cos(a)*(r+6),h/2+math.sin(a)*(r+6)*.4),style if i%2 else 4,-3)
        elif theme=='crt':
            y=2+p*(h-5)
            c.line((2,y),(w-3,y),style,-3)
            for side in (-1,1):
                x=cx+side*w*.36
                self.ellipse(c,x,h*.5,3+p*14,2+p*7,style=4,depth=-3)
        else:
            for side in (-1,1):
                x=cx+side*w*.36
                for k in range(3):
                    self.ellipse(c,x,h*.5,4+p*16+k,3+p*8+k*.5,style=5 if k==0 else 6,depth=-3,steps=80)
