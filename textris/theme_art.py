"""테마마다 다른 실루엣을 갖는 절차적 무대와 공통 성취 연출."""
import math
from .art import ArtCanvas, game_layout
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
        if major: self.ceremony(c,t,theme,major,flash,intensity,board)
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

    def ceremony(self,c,t,theme,cue,flash,intensity,board=None):
        # 수명은 director가 관리하지만 직접 렌더/seek에서도 오래된 cue가 남지 않는다.
        if not cue.start<=t<cue.end or intensity<=0: return
        p=cue.phase(t)
        strength=(.35+.65*min(1.,intensity))*min(1.6,max(0.,cue.power))*math.sin(math.pi*p)
        style=9 if flash and .15<p<.65 and intensity>.5 else 4
        if cue.name=='clear':
            self.clear_ceremony(c,theme,cue,p,strength,style,board)
            return
        if cue.name not in ('bloom','ascension','victory','eclipse','awakening'): return
        w,h=c.context.width-1,c.context.height
        origin=None
        if cue.name in ('bloom','ascension') and cue.coords:
            _,by=board or game_layout(c.context.width,c.context.height).board
            origin=by+1+sum(cue.coords)/len(cue.coords)-2
        # 좌우 여백의 초점을 공유하되 동작 방향과 실루엣으로 사건의 의미를 전달한다.
        for side in (-1,1):
            x=w/2+side*w*.36
            if cue.name in ('bloom','ascension'):
                getattr(self,cue.name+'_ceremony')(c,theme,x,h,p,strength,style,origin)
            else:
                getattr(self,cue.name+'_ceremony')(c,theme,x,h,p,strength,style)

    def clear_ceremony(self,c,theme,cue,p,strength,style,board):
        bx,by=board or game_layout(c.context.width,c.context.height).board
        reach=(12+p*c.context.width*.32)*strength
        for row in cue.coords or (21,):
            # 엔진 행에는 숨김 2행이 포함되며 보드 테두리 안쪽부터 표시한다.
            y=by+1+row-2
            for side in (-1,1):
                start=bx-2 if side<0 else bx+23
                end=start+side*reach
                if theme=='cyberpunk':
                    for i in range(1+int(4*strength)):
                        x=start+side*(reach*i/(1+int(4*strength)))
                        c.curve(((x,y),(x+side*3,y),(x+side*3,y-.7),(x+side*5,y-.7)),style,-4)
                elif theme=='space':
                    c.line((start,y),(end,y),6,-3)
                    self.ellipse(c,end,y,2+strength*3,.6+strength,style=style,depth=-4,steps=40)
                elif theme=='fire':
                    for i in range(1+int(7*strength)):
                        u=(i+.5)/(1+int(7*strength));x=start+side*reach*u
                        c.curve(((x,y),(x+side*2,y-strength*(1+u)),(x+side*3,y)),style,-4)
                elif theme=='crt':
                    c.line((start,y),(end,y),style,-4)
                    c.line((end,y-strength),(end,y+strength),5,-4)
                    c.line((start,y+.7),(end-side*4,y+.7),6,-3)
                else:
                    for i in range(1+int(8*strength)):
                        x=start+side*reach*i/(1+int(8*strength))
                        c.line((x,y+strength),(x+side*2,y-strength),5,-4)

    def bloom_ceremony(self,c,theme,x,h,p,strength,style,origin=None):
        y=h*.5 if origin is None else origin*(1-p)+h*.5*p
        r=(4+p*15)*strength
        if theme=='cyberpunk':
            for i in range(3):
                d=r+i*2
                c.curve(((x-d,y-d*.5),(x+d,y-d*.5),(x+d,y+d*.5),
                         (x-d,y+d*.5),(x-d,y-d*.5)),style if i==0 else 6,-4+i*.1)
                c.line((x-d,y),(x+d,y),6,-3)
                c.line((x,y-d*.5),(x,y+d*.5),6,-3)
        elif theme=='space':
            self.ellipse(c,x,y,r,r*.5,style=style,depth=-4,steps=64)
            for i in range(16):
                a=i*TAU/16
                c.line((x+math.cos(a)*r*.5,y+math.sin(a)*r*.25),
                       (x+math.cos(a)*r*1.5,y+math.sin(a)*r*.75),5 if i%4==0 else 6,-4)
        elif theme=='fire':
            for i in range(12):
                a=i*TAU/12
                c.curve(((x+math.cos(a)*r*.6,y+math.sin(a)*r*.3),
                    (x+math.cos(a+.12)*r*1.5,y+math.sin(a+.12)*r*.8),
                    (x+math.cos(a+.3)*r*.8,y+math.sin(a+.3)*r*.4)),style if i%2 else 9,-4)
        elif theme=='crt':
            for band in range(-2,3):
                c.curve(((x-r+2*r*j/64,y+band*2+math.sin(j*.5+p*8)*strength*3)
                         for j in range(65)),style if band==0 else 6,-4)
        else:
            for i in range(8):
                a=i*TAU/8;dx,dy=math.cos(a)*r,math.sin(a)*r*.6
                c.curve(((x+dx*.3,y+dy*.3),(x+dx-dy*.4,y+dy+dx*.15),
                         (x+dx*1.6,y+dy*1.6),(x+dx+dy*.4,y+dy-dx*.15),
                         (x+dx*.3,y+dy*.3)),5 if i%2 else 6,-4)

    def ascension_ceremony(self,c,theme,x,h,p,strength,style,origin=None):
        bottom=h-3 if origin is None else origin
        rise=(.25+p*.65)*max(3,bottom-2)*strength
        for i in range(-3,4):
            xx=x+i*2.5;top=bottom-rise*(1-abs(i)*.12)
            if theme=='cyberpunk':
                c.curve(((xx-1,bottom),(xx-1,top),(xx+1,top),(xx+1,bottom)),style if i==0 else 6,-4)
                c.line((xx,top-2*strength),(xx,top),5,-4)
            elif theme=='space':
                c.curve(((xx+math.sin(j*.15+i+p*5)*strength*3,bottom-rise*j/48)
                         for j in range(49)),style if i%2 else 6,-4)
                c.put(xx,top,'+',5,-5)
            elif theme=='fire':
                c.curve(((xx,bottom),(xx+math.sin(i+p*5)*strength*4,top),
                         (xx+2*strength,bottom)),9 if i==0 else style,-4)
            elif theme=='crt':
                c.line((xx,top),(xx,bottom),6,-3)
                for j in range(3):
                    yy=top+j*3*strength
                    c.curve(((xx-1,yy+1),(xx,yy),(xx+1,yy+1)),style,-4)
            else:
                c.line((xx,bottom),(xx-i*.6,top),5 if i%2 else 6,-4)
                c.curve(((xx-1,top+2),(xx,top),(xx+1,top+2)),5,-4)

    def victory_ceremony(self,c,theme,x,h,p,strength,style):
        y=h*.3;r=7+5*strength;lift=3+3*strength
        if theme=='crt':
            # 혼란스러운 폭발 파형과 달리 일정한 주기의 동기 신호가 자리 잡는다.
            c.curve(((x-r+j*r/24,y+math.sin(j*TAU/16)*strength*2)
                     for j in range(49)),5,-4)
            for side in (-1,1):
                xx=x+side*(r+1)
                c.curve(((xx-side*2,y-lift),(xx,y-lift),(xx,y+lift),(xx-side*2,y+lift)),style,-4)
            c.line((x-r,y+lift),(x+r,y+lift),6,-3)
            return
        points=((x-r,y),(x-r,y-lift),(x-r*.5,y-lift*.45),(x,y-lift*1.5),
                (x+r*.5,y-lift*.45),(x+r,y-lift),(x+r,y),(x-r,y))
        if theme=='fire':
            self.ellipse(c,x,y,r,2*strength,style=9,depth=-4,steps=64)
            for i in range(-2,3):
                xx=x+i*r*.4
                c.curve(((xx-2,y),(xx+math.sin(i+p*4)*strength,y-lift*(1.4-abs(i)*.25)),
                         (xx+2,y)),9 if i==0 else style,-4)
        elif theme=='mono':
            c.curve(points,5,-4)
            c.curve(((x-r,y+2),(x,y+lift),(x+r,y+2),(x-r,y+2)),6,-3)
            for i in range(-3,4): c.line((x+i*r/4,y),(x+i*r/4+2,y-2*strength),5,-4)
        else:
            c.curve(points,style,-4)
            if theme=='space':
                for xx,yy in points[:-1]: c.put(xx,yy,'+',5,-5)
                self.ellipse(c,x,y+2,r*1.3,2*strength,style=6,depth=-3,steps=64)
            else:
                c.line((x-r,y+2),(x+r,y+2),5,-4)
                for i in range(-2,3): c.put(x+i*r/3,y+3,'=',style,-4)

    def eclipse_ceremony(self,c,theme,x,h,p,strength,style):
        y=h*.53;r=(3+(1-p)*13)*strength
        if theme=='space':
            # 식의 내부는 어둡게 덮되 보호 마스크는 다른 모든 도형과 동일하다.
            for iy in range(-int(r/2),int(r/2)+1):
                half=math.sqrt(max(0,r*r-(iy*2)**2))
                for ix in range(-int(half),int(half)+1): c.put(x+ix,y+iy,' ',0,-4)
            self.ellipse(c,x,y,r,r*.5,style=6,depth=-5,steps=72)
        elif theme=='cyberpunk':
            for i in range(-3,4):
                xx=x+i*2.5;floor=y+r*.6
                c.curve(((xx-1,floor),(xx-1,floor-r*(1-abs(i)*.1)),
                         (xx+1,floor-r*(1-abs(i)*.1)),(xx+1,floor)),6,-4)
                c.put(xx,floor-r-2+p*4,':',3,-5)
        elif theme=='fire':
            for i in range(-3,4):
                xx=x+i*2
                c.curve(((xx-1,y+r*.4),(xx+math.sin(i)*strength,y-r*.6),
                         (xx+1,y+r*.4)),6,-4)
                c.put(xx,y-r-2,'·' if not c.context.ascii_mode else '.',2,-4)
        elif theme=='crt':
            for i in range(6):
                xx=x-r+i*r/3
                c.line((xx,y+math.sin(i*3)*strength),(xx+r/5,y+math.sin(i*3)*strength),6,-4)
            c.line((x,y-r*.3),(x,y+r*.3),3,-4)
        else:
            for i in range(4):
                d=r*(1-i*.18)
                c.curve(((x-d,y),(x,y-d*.6),(x+d,y),(x,y+d*.6),(x-d,y)),6,-4)
            for i in range(-3,4): c.line((x-r*.5,y+i*.5),(x+r*.5,y+i*.5-r*.3),2,-4)

    def awakening_ceremony(self,c,theme,x,h,p,strength,style):
        y=h*.55;r=(3+p*10)*strength
        if theme=='cyberpunk':
            for i in range(-2,3):
                xx=x+i*3
                c.curve(((xx,y+r*.5),(xx,y-r*.5),(xx-1,y-r*.3),
                         (xx,y-r*.5),(xx+1,y-r*.3)),style,-4)
            c.line((x-7,y+r*.5),(x+7,y+r*.5),5,-4)
        elif theme=='space':
            for tilt in (-.4,.4):
                c.curve(((x+math.cos(a)*r,y+math.sin(a)*r*.4+math.cos(a)*r*tilt)
                         for a in (j*TAU/64 for j in range(65))),style,-4)
            c.put(x+math.cos(p*TAU)*r,y+math.sin(p*TAU)*r*.4,'+',5,-5)
        elif theme=='fire':
            c.curve(((x-r,y+r*.5),(x-r*.4,y-r*.4),(x,y-r),(x+r*.3,y-r*.2),
                     (x+r,y+r*.5),(x,y+r*.8),(x-r,y+r*.5)),style,-4)
            c.line((x,y+r*.5),(x,y-r*.2),9,-5)
        elif theme=='crt':
            c.curve(((x-r,y-r*.5),(x+r,y-r*.5),(x+r,y+r*.5),
                     (x-r,y+r*.5),(x-r,y-r*.5)),6,-4)
            c.line((x-r,y-r*.5+p*r),(x+r,y-r*.5+p*r),style,-5)
            for i in range(1+int(strength*5)): c.put(x-r+2+i*2,y+r*.5-1,'=',5,-5)
        else:
            for scale in (1.,1.3):
                d=r*scale
                c.curve(((x-d,y),(x,y-d*.65),(x+d,y),(x,y+d*.65),(x-d,y)),5,-4)
