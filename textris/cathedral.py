"""극좌표 장미창·천체 조각·빛 커튼으로 구성한 문자 대성당."""
import math
from .art import ArtCanvas, game_layout
from .theme_surfaces import render_surfaces, samples

TAU=math.tau


class CathedralScene:
    def __init__(self):
        self._layers={}

    def layer(self,context,key,draw):
        cache_key=(context,key)
        slot=key[:2] if key[0]=='orbit' else key[:1]
        cached=self._layers.get(slot)
        if cached is None or cached[0]!=cache_key:
            canvas=ArtCanvas(context)
            draw(canvas)
            self._layers[slot]=(cache_key,canvas.cells)
        return self._layers[slot][1]

    @staticmethod
    def merge(canvas,layer):
        for point,ink in layer.items():
            old=canvas.cells.get(point)
            if old is None or ink.depth<=old.depth: canvas.cells[point]=ink

    def render(self,context,t,major=None,local=(),board=None,flash=True,intensity=.75,density=.75,motion_speed=1.):
        c=ArtCanvas(context)
        w,h=context.width-1,context.height
        cx=w/2
        major=major if major and major.start<=t<major.end and intensity>0 else None
        phase=major.phase(t) if major else 0
        envelope=math.sin(math.pi*phase)*major.power*intensity if major else 0
        pulse=envelope if flash else 0
        opening=envelope if major and major.name in ('bloom','ascension','victory') else 0
        # 갱신 위상을 분산해 한 프레임에 모든 절차적 장면을 다시 계산하지 않는다.
        motion=t*motion_speed
        surface_time=math.floor(motion*8)/8
        self.merge(c,self.layer(context,('surfaces',surface_time),
            lambda layer:render_surfaces(layer,surface_time,'cathedral')))
        self.merge(c,self.layer(context,('arches',),lambda layer:self.arches(layer,cx,h,w,0,0)))
        radius=min(w*.21,h*.43)
        rose_time=math.floor(motion*12)/12
        rose_open=round(opening*8)/8
        self.merge(c,self.layer(context,('rose',rose_time,rose_open),
            lambda layer:self.rose(layer,cx,max(4,h*.20),radius,rose_time,rose_open,context.quality)))
        if w>=95 and h>=34:
            for side in (-1,1):
                x=cx+side*w*.365
                orbit_time=(math.floor(motion*12+(side+3)/6)-(side+3)/6)/12
                def ornament(layer,x=x,side=side,orbit_time=orbit_time):
                    self.orbits(layer,x,h*.52,min(15,w*.125),orbit_time*side,context.quality,0)
                    self.curtain(layer,x,h,w,orbit_time,side,context.quality)
                self.merge(c,self.layer(context,('orbit',side,orbit_time),ornament))
        floor_time=math.floor(motion*6+.25)/6
        self.merge(c,self.layer(context,('floor',floor_time),lambda layer:self.floor(layer,cx,h,w,floor_time)))
        self.dust(c,w,h,motion,density,context.quality)
        if major:
            self.ceremony(c,cx,h,w,t,major,opening,pulse,board,intensity,flash)
        if board:
            for cue in local:
                self.local_effect(c,board,t,cue,intensity,flash)
        return c

    def arches(self,c,cx,h,w,t,opening):
        steps=max(30,int(48*c.context.quality))
        for layer in range(4):
            rx=w*(.47-layer*.035)+opening*layer
            top=1+layer*1.3
            spring=h*.56
            for side in (-1,1):
                points=[]
                for i in range(steps+1):
                    u=i/steps
                    # 첨두 아치의 꼭짓점을 중앙에 맞춘다.
                    x=cx+side*rx*(math.sin(u*math.pi/2)**.85)
                    y=top+(spring-top)*(1-math.cos(u*math.pi/2))
                    points.append((x,y))
                c.curve(points,2 if layer%2 else 6,depth=5+layer)
                x=cx+side*rx
                c.line((x,spring),(x,h-5),2,5+layer)
                c.line((x+side*.8,spring),(x+side*.8,h-5),1,6+layer)
                for yy in (spring,h-6):
                    c.put(x,yy,'+' if c.context.ascii_mode else '◆',8,4)
        # 네 모서리만 강조해 밝은 외곽선이 시선을 분산시키지 않게 한다.
        for x,sign in ((2,1),(w-3,-1)):
            c.line((x,2),(x+sign*5,2),8,2)
            c.line((x,2),(x,4),8,2)
            c.line((x,h-4),(x+sign*5,h-4),8,2)

    def rose(self,c,cx,cy,r,t,opening,quality):
        count=max(120,int(300*quality))
        spin=t*.035
        # 가로 2:세로 1 비율로 투영해 터미널 셀의 종횡비를 보정한다.
        for ring in range(3):
            radius=r*(.80+ring*.09+opening*.025)
            c.curve(((cx+math.cos(i*TAU/count)*radius,
                      cy+math.sin(i*TAU/count)*radius*.48) for i in range(count+1)),
                    8 if ring==1 else 2,3)
        for petal in range(12):
            angle=petal*TAU/12+spin
            points=[]
            petal_count=samples(c,48)
            for i in range(petal_count+1):
                a=i*TAU/petal_count
                radius=r*(.48+.28*math.cos(a))*(1+opening*.13)
                theta=angle+.17*math.sin(a)
                points.append((cx+math.cos(theta)*radius,cy+math.sin(theta)*radius*.48))
            c.curve(points,3 if petal%2 else 6,2)
            theta=angle+math.pi/12
            c.line((cx+math.cos(theta)*r*.24,cy+math.sin(theta)*r*.12),
                   (cx+math.cos(theta)*r*.78,cy+math.sin(theta)*r*.375),2,3)
            c.put(cx+math.cos(angle)*r*.9,cy+math.sin(angle)*r*.432,
                  '+' if c.context.ascii_mode else '◇',8,1)
        for k in range(2):
            c.curve(((cx+math.cos(a)*r*(.17+.045*math.cos(8*a+t*.13+k)),
                      cy+math.sin(a)*r*(.085+.0225*math.cos(8*a+t*.13+k)))
                     for a in (i*TAU/samples(c,160,32) for i in range(samples(c,160,32)+1))),4 if k else 7,1)

    def orbits(self,c,cx,cy,r,t,quality,pulse):
        count=max(60,int(128*quality))
        tilt=t*.15
        # 같은 곡선을 이전 시각에도 그려 유한한 빛의 잔상을 만든다.
        trails=1 if quality>.8 else 0
        for trail in range(trails,-1,-1):
            age=trail*.09
            for ring in range(3):
                beta=ring*TAU/3+tilt-age
                rotation=.5+math.sin(t*.08)*.25
                cr,sr=math.cos(rotation),math.sin(rotation)
                cb,sb=math.cos(beta),math.sin(beta)
                for i in range(count):
                    a=i*TAU/count
                    x=math.cos(a)*r
                    y=math.sin(a)*r*cb
                    z=math.sin(a)*r*sb
                    xx=x*cr-y*sr
                    yy=x*sr+y*cr
                    perspective=1/(1+z/(r*5))
                    sx=cx+xx*perspective; sy=cy+yy*perspective*.48
                    style=(2 if z>0 else (9 if ring==0 else 4 if ring==1 else 7)) if trail==0 else 1
                    c.dot(sx,sy,style,depth=z/r+trail*.15)
        # 문자 밀도와 윤곽으로 빛을 받은 팔면체의 입체감을 전달한다.
        vertices=[]
        for x,y,z in ((0,-1,0),(1,0,0),(0,0,1),(-1,0,0),(0,0,-1),(0,1,0)):
            a=t*.3; xx=x*math.cos(a)+z*math.sin(a); zz=-x*math.sin(a)+z*math.cos(a)
            vertices.append((cx+xx*r*.31,cy+y*r*.24,zz))
        for i,j in ((0,1),(0,2),(0,3),(0,4),(5,1),(5,2),(5,3),(5,4),(1,2),(2,3),(3,4),(4,1)):
            a,b=vertices[i],vertices[j]
            c.line(a[:2],b[:2],5 if a[2]+b[2]<0 else 6,-2+(a[2]+b[2])*.1)
        for y in range(-3,4):
            half=max(0,3-abs(y))
            for x in range(-half,half+1):
                c.put(cx+x,cy+y*.6,':=*'[min(2,abs(x+y)%3)] if c.context.ascii_mode else '░▒▓'[min(2,abs(x+y)%3)],
                      6 if x<0 else 3,-1.5)

    def curtain(self,c,cx,h,w,t,side,quality):
        # 성긴 디더링과 위아래 반블록으로 어둠이 비치는 얇은 광막을 만든다.
        for y in range(5,h-6,1 if quality>.65 else 2):
            yy=y/h
            center=cx+math.sin(yy*5+t*.18+side)*3
            for dx in range(-4,5):
                if (dx+y)%3: continue
                strength=(1-abs(dx)/5)*math.sin(yy*math.pi)**2
                if strength<.25: continue
                c.put(center+dx,y,'.' if c.context.ascii_mode else '▀' if y%2 else '▄',
                      12 if side<0 else 13,10)

    def floor(self,c,cx,h,w,t):
        horizon=h*.75
        for i in range(-5,6):
            c.line((cx+i*2,horizon),(cx+i*w*.12,h-3),1,9)
        for i in range(4):
            f=((i+t*.12)%4)/4
            y=horizon+(h-3-horizon)*f*f
            c.line((3,y),(w-3,y),1,9)

    def dust(self,c,w,h,t,density,quality):
        count=int(26*density*quality)
        for i in range(count):
            x=(i*43.71)%w
            y=(i*17.33-t*.18*(1+i%3))%max(1,h-4)+2
            c.put(x,y,'.' if c.context.ascii_mode else '·',2,12)

    def ceremony(self,c,cx,h,w,t,cue,opening,pulse,board=None,intensity=.75,flash=True,viewport=None):
        if not cue.start<=t<cue.end or intensity<=0: return
        p=cue.phase(t)
        strength=(.35+.65*min(1.,intensity))*min(1.6,max(0.,cue.power))*math.sin(math.pi*p)
        if strength<=0: return
        bright=9 if flash and .15<p<.65 and intensity>.5 else 8
        bx,by=board or game_layout(c.context.width,c.context.height).board
        rows=cue.coords or (21,)
        origin=by+1+sum(rows)/len(rows)-2
        count=samples(c,96,24)
        def ring(x,y,rx,ry,style=8,depth=-4):
            c.curve(((x+math.cos(j*TAU/count)*rx,y+math.sin(j*TAU/count)*ry)
                     for j in range(count+1)),style,depth)
        if cue.name=='clear':
            for row in rows:
                yy=by+1+row-2
                for side in (-1,1):
                    x=bx-2 if side<0 else bx+23
                    reach=(5+p*w*.28)*strength
                    c.line((x,yy),(x+side*reach,yy),bright,-4)
                    for j in range(1+int(5*strength)):
                        xx=x+side*reach*(j+.5)/(1+int(5*strength))
                        c.curve(((xx-1,yy),(xx,yy-strength),(xx+1,yy),(xx,yy+strength),(xx-1,yy)),8,-5)
            return
        for side in (-1,1):
            x=(bx-9 if side<0 else bx+31) if viewport else cx+side*w*.34
            if cue.name=='bloom':
                if getattr(cue,'variant','')=='spin':
                    # 장미 조각이 삭제 위치를 중심으로 회전하며 Tetris의 종광과 구분된다.
                    r=(5+12*p)*strength
                    for j in range(8):
                        a=j*TAU/8+p*TAU
                        c.curve(((x+math.cos(a)*r*.35,origin+math.sin(a)*r*.18),
                                 (x+math.cos(a+.45)*r,origin+math.sin(a+.45)*r*.45),
                                 (x+math.cos(a+.9)*r*.65,origin+math.sin(a+.9)*r*.3)),bright,-4)
                else:
                    for j in range(-2,3):
                        xx=x+j*2.5*strength
                        reach=(4+p*h*.6)*strength*(1-abs(j)*.12)
                        c.line((xx,origin),(xx,origin-reach),bright if j==0 else 3,-4)
                        ring(xx,origin,2+strength*4,.5+strength,8,-5)
            elif cue.name=='ascension':
                # 올 클리어는 마지막 삭제 행에서 위로 올라오는 펼쳐진 유리 광막이다.
                rise=(.25+p*.65)*max(3,origin-2)*strength
                for j in range(-4,5):
                    xx=x+j*2*strength;top=origin-rise*(1-abs(j)*.09)
                    c.line((xx,origin),(xx,top),bright if j==0 else 3,-4)
                    c.curve(((xx-1,top+2),(xx,top),(xx+1,top+2)),8,-5)
                    for yy in range(max(0,int(top)),min(h,int(origin)),2):
                        if (yy+j)%3==0:
                            c.put(xx,yy,':' if c.context.ascii_mode else '░',6,-3)
                ring(x,origin-rise,6*strength,2*strength,8,-5)
            elif cue.name=='victory':
                # 승리는 닫히는 아치와 완성된 장미창·왕관; 상승 광막과 형상을 공유하지 않는다.
                yy=h*.24;r=(6+5*p)*strength
                ring(x,yy,r,r*.42,bright)
                for j in range(8):
                    a=j*TAU/8
                    c.line((x+math.cos(a)*r*.2,yy+math.sin(a)*r*.1),
                           (x+math.cos(a)*r*.9,yy+math.sin(a)*r*.38),8,-5)
                c.curve(((x-r,yy+4),(x-r,yy-2),(x-r*.5,yy),
                         (x,yy-5*strength),(x+r*.5,yy),(x+r,yy-2),(x+r,yy+4)),bright,-4)
                c.line((x-r,yy+4),(x+r,yy+4),8,-4)
            elif cue.name=='eclipse':
                yy=h*.5;r=(4+(1-p)*12)*strength
                for j in range(4):
                    a=p*.8+j*TAU/4
                    c.curve(((x+math.cos(a)*r,yy+math.sin(a)*r*.45),
                             (x+math.cos(a+.8)*r*.6,yy+math.sin(a+.8)*r*.28),
                             (x+math.cos(a+1.1)*r*.2,yy+math.sin(a+1.1)*r*.1)),6,-4)
                ring(x,yy,r*.45,r*.2,2,-5)
            elif cue.name=='awakening':
                yy=h*.52;r=(3+p*10)*strength
                c.curve(((x-r,yy+r*.4),(x-r,yy),(x,yy-r*.7),
                         (x+r,yy),(x+r,yy+r*.4)),bright,-4)
                for j in range(-2,3):
                    xx=x+j*r*.3
                    c.line((xx,yy+r*.4),(xx,yy-r*.3+abs(j)*strength),3,-4)
                ring(x,yy+r*.4,r*1.1,.5+strength,8,-5)

    def local_effect(self,c,board,t,cue,intensity,flash):
        from .theme_actions import render_local
        render_local(c,board,t,cue,'cathedral',intensity,flash)
