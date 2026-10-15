"""플레이어별 허용 여백에 그리는 유한 조작과 읽기 전용 상태 연출."""
import math
from .themes import THEMES

ACTIONS=('drop','lock','rotate','hold','focus','move')


class _Brush:
    def __init__(self,canvas,regions=None,budget=240,flash=True):
        self.canvas=canvas
        self.regions=regions
        self.remaining=budget
        self.flash=flash
        self.quality=max(.15,min(1.,canvas.context.quality))
        self.depth=-5

    def put(self,x,y,glyph,style=3):
        x,y=round(x),round(y)
        if self.remaining<=0 or not self.canvas.accepts(x,y):
            return
        if self.regions is not None and not any(a<=x<a+w and b<=y<b+h for a,b,w,h in self.regions):
            return
        self.remaining-=1
        self.canvas.put(x,y,glyph,style if self.flash else min(style,3),self.depth)

    def line(self,a,b,style=3):
        dx,dy=b[0]-a[0],b[1]-a[1]
        steps=min(32,max(1,math.ceil(max(abs(dx),abs(dy))*(.5+.5*self.quality))))
        glyph='|' if abs(dy)>abs(dx)*2 else '-' if abs(dx)>abs(dy)*2 else '/' if dx*dy<0 else '\\'
        for i in range(steps+1):
            u=i/steps
            self.put(a[0]+dx*u,a[1]+dy*u,glyph,style)

    def path(self,points,style=3):
        for a,b in zip(points,points[1:]):
            self.line(a,b,style)


def _motif(brush,theme,x,y,r,p,style=3):
    """색 없이도 구별되는 종/회로/궤도/불꽃/벡터/판화/해파리/결정 골격."""
    if theme=='cathedral':
        brush.path(((x-r,y+1),(x-r,y),(x,y-r*.6),(x+r,y),(x+r,y+1)),style)
        brush.line((x-r,y+1),(x+r,y+1),style)
        brush.put(x,y+2,'o',style)
    elif theme=='cyberpunk':
        brush.path(((x-r,y+1),(x-r,y-1),(x,y-1),(x,y-2),(x+r,y-2),(x+r,y+1)),style)
        brush.put(x-r,y+1,'[',style);brush.put(x+r,y+1,']',style)
        brush.put(x+r*(2*p-1),y,'=',style)
    elif theme=='space':
        steps=max(8,int(24*brush.quality))
        for i in range(steps):
            a=i*math.tau/steps+p
            brush.put(x+math.cos(a)*r,y+math.sin(a)*r*.55,'.',style)
        brush.put(x+math.cos(p*math.tau)*r,y+math.sin(p*math.tau)*r*.55,'*',style)
    elif theme=='fire':
        for i in range(max(2,int(5*brush.quality))):
            dx=(i-2)*r/3
            brush.path(((x+dx,y+1),(x+dx+math.sin(p*7+i),y-1),(x+dx*.4,y-r)),style)
        brush.put(x,y+1,'^',style)
    elif theme=='crt':
        brush.path(((x-r,y),(x-r/2,y-r*.55),(x+r/2,y+r*.55),(x+r,y)),style)
        brush.line((x-r,y+2),(x+r,y+2),style)
        brush.put(x+(2*p-1)*r,y,'+',style)
    elif theme=='abyss':
        brush.path(((x-r,y),(x-r*.6,y-r*.5),(x+r*.6,y-r*.5),(x+r,y)),style)
        brush.line((x-r,y),(x+r,y),style)
        for i in range(max(1,int(3*brush.quality))):
            dx=(i-1)*r*.55
            brush.path(((x+dx,y),(x+dx+math.sin(p*6+i),y+1),
                        (x+dx+math.sin(p*6+i+1),y+2)),style)
        brush.put(x-r,y,'(',style);brush.put(x+r,y,')',style)
        brush.put(x+math.sin(p*5)*r*.5,y-r*.5-1,'o',style)
        brush.put(x-r*.5,y+3,'~',style);brush.put(x+r*.5,y+3,'~',style)
    elif theme=='aurora':
        brush.line((x,y+r*.6),(x,y-r*.8),style)
        for side in (-1,1):
            brush.path(((x,y+.5),(x+side*r*.6,y-r*.25),(x+side*r,y-r*.7)),style)
            brush.line((x+side*r*.6,y-r*.25),(x+side*r,y),style)
        brush.put(x,y,'+',style)
        for i in range(max(1,int(3*brush.quality))):
            dx=(i-1)*r*.7
            brush.put(x+dx,y-r-1-math.sin(p*5+i)*.5,'*' if i%2 else '|',style)
    else:
        brush.path(((x-r,y),(x,y-r*.6),(x+r,y),(x,y+r*.6),(x-r,y)),style)
        for i in range(max(1,int(4*brush.quality))):
            brush.put(x-r/2+i,y+(i%2),'#' if i%2 else '/',style)


def _action_pose(action,board,landing,row,side,p,strength):
    bx,by=board
    x=bx-3 if side<0 else bx+24
    r=1+strength*(1.2+2*p)
    if action in ('drop','lock'):
        return x,by+1+landing,r*(1+p if action=='lock' else 1)
    if action=='rotate':
        return x+math.cos(p*math.tau)*1.3,by+5+p*4,r
    if action=='hold':
        return x+side*(1-p)*2,by+3+p*3,r*.7
    if action=='move':
        return x+side*(p*3-1.5),by+1+row,r*.65
    return x,by+9-p*2,r*.65


def _wake(brush,theme,x,y,r,p,style):
    """주 문양을 복제하지 않고 몇 셀의 테마별 여운만 남긴다."""
    spread=min(2,max(1,r*.45))
    if theme=='cathedral':
        brush.put(x,y,"'",style)
        brush.put(x-spread,y+1,'(',style);brush.put(x+spread,y+1,')',style)
    elif theme=='cyberpunk':
        brush.path(((x-spread,y+1),(x-spread,y),(x,y),(x,y-1)),style)
        brush.put(x+spread,y-1,':',style)
    elif theme=='space':
        for i in range(3):
            a=p*math.tau+i*.8
            brush.put(x+math.cos(a)*spread,y+math.sin(a),'.',style)
        brush.put(x,y-1,'*',style)
    elif theme=='fire':
        brush.put(x+math.sin(p*8),y-r-1,'^',style)
        brush.put(x-spread,y-r,',',style);brush.put(x+spread,y-r+1,':',style)
    elif theme=='crt':
        brush.path(((x-spread,y+1),(x,y-1),(x+spread,y)),style)
        brush.put(x,y+2,':',style)
    elif theme=='abyss':
        brush.put(x,y-1,'o',style)
        brush.put(x-spread,y+1,'~',style);brush.put(x+spread,y+1,'~',style)
    elif theme=='aurora':
        brush.put(x,y-1,'+',style)
        brush.put(x-spread,y,'|',style);brush.put(x+spread,y+1,'*',style)
    else:
        brush.put(x-spread,y,'/',style);brush.put(x,y-1,'/',style)
        brush.put(x+spread,y-2,'.',style)


def render_local(canvas,board,t,cue,theme,intensity,flash):
    """Cue 좌표는 보드 내부 상대좌표이고 출력은 보드 외곽에 한정한다."""
    if theme not in THEMES or cue.name not in ACTIONS or not cue.start<=t<cue.end or intensity<=0:
        return
    viewports=getattr(canvas.context,'viewports',())
    viewport=next((v for v in viewports if v.player_id==getattr(cue,'player_id','p1')),None)
    if viewports and viewport is None:
        return
    regions=viewport.effect_regions if viewport else None
    brush=_Brush(canvas,regions,180,flash)
    bx,by=board
    p=cue.phase(t)
    strength=min(1.6,max(.05,intensity*cue.power))
    coords=cue.coords[:4]
    landing=max((pos[1] for pos in coords),default=18)
    landing=max(0,min(19,landing))
    row=max(0,min(19,sum(pos[1] for pos in coords)/len(coords) if coords else 8))
    style=5 if flash and p<.25 and strength>.5 else 3
    for side in (-1,1):
        edge=bx-3 if side<0 else bx+24
        x,y,radius=_action_pose(cue.name,board,landing,row,side,p,strength)
        if cue.name=='drop':
            length=2+int((1-p)*strength*9)
            brush.line((x,y-length),(x,y),style)
            _motif(brush,theme,x,y,radius,p,style)
        elif cue.name=='lock':
            _motif(brush,theme,x,y,radius,p,style)
        elif cue.name=='rotate':
            _motif(brush,theme,x,y,radius,p,style)
            brush.put(edge+side*radius,y-2,'<' if side<0 else '>',style)
        elif cue.name=='hold':
            _motif(brush,theme,x,y,radius,p,style)
            brush.line((edge,y+3),(edge-side*(2+strength*2),y+3),style)
            brush.put(edge-side*(2+strength*2),y+3,'>' if side<0 else '<',style)
        elif cue.name=='move':
            _motif(brush,theme,x,y,radius,p,style)
            brush.line((edge-side*2,y+2),(x,y+2),style)
            brush.put(x,y+2,'<' if side<0 else '>',style)
        else:
            _motif(brush,theme,x,y,radius,p,style)
            brush.path(((x-2,y-3),(x,y-3),(x,y-2)),style)
            brush.path(((x+2,y+3),(x,y+3),(x,y+2)),style)
    # 양쪽 주 문양이 예산을 먼저 사용한다. 과거 phase의 최대 두 표본은
    # 같은 brush의 남은 예산과 뒤쪽 깊이만 써서 본 동작을 가리지 않는다.
    for echo in range(1,min(2,int(2*brush.quality*min(1,strength)))+1):
        previous=p-.14*echo
        if previous<0:
            continue
        brush.depth=-5+echo
        for side in (-1,1):
            x,y,radius=_action_pose(cue.name,board,landing,row,side,previous,strength)
            _wake(brush,theme,x,y-echo*2,radius,previous,3-echo)


def render_state(canvas,t,theme,state,viewport=None,*,intensity=.75,flash=True):
    """프레임마다 상태를 읽으며 종료된 위험/피버의 잔여 상태를 저장하지 않는다."""
    if theme not in THEMES or state is None or intensity<=0:
        return
    viewports=getattr(canvas.context,'viewports',())
    if viewport is None and viewports:
        viewport=next((v for v in viewports if v.player_id==state.player_id),None)
        if viewport is None:
            return
    if viewport is not None and viewport.player_id!=state.player_id:
        return
    regions=viewport.effect_regions if viewport is not None else ((1,2,8,max(0,canvas.context.height-4)),(canvas.context.width-10,2,8,max(0,canvas.context.height-4)))
    strength=min(1.,max(.05,intensity))
    brush=_Brush(canvas,regions,260,flash)
    brush.quality*=.3+.7*strength
    statuses=[]
    if state.danger: statuses.append(('danger',1))
    if state.fever: statuses.append(('fever',1))
    if state.combo>0: statuses.append(('combo',min(6,state.combo)))
    if state.b2b: statuses.append(('b2b',2))
    if state.level>1: statuses.append(('level',min(8,state.level)))
    # 한 영역이 보드까지 감싸면 중심은 보호 마스크에 숨는다. 보드 양옆의
    # 실제 연출 통로로 축약하되 허용영역과 교집합만 사용한다.
    lanes=regions
    if viewport is not None and hasattr(viewport,'board'):
        bx,by=viewport.board
        lanes=[]
        for a,b,w,h in regions[:8]:
            for lx,ly,lw,lh in ((bx-7,by,6,22),(bx+23,by,6,22)):
                left,top=max(a,lx),max(b,ly)
                right,bottom=min(a+w,lx+lw),min(b+h,ly+lh)
                if right>left and bottom>top:
                    lanes.append((left,top,right-left,bottom-top))
    phase=(t*.7)%1
    for a,b,w,h in lanes[:8]:
        if w<=0 or h<=0:
            continue
        x=a+(w-1)/2
        for kind,value in statuses:
            # 상하 위치도 상태 의미의 일부다. HUD/다른 플레이어 영역은 brush가 차단한다.
            band={'danger':.18,'fever':.48,'combo':.7,'b2b':.82,'level':.94}[kind]
            y=b+(h-1)*band+math.sin(t*2+band)*1.3
            radius=min(4,max(.8,(w-1)/2))*(.35+.65*strength)
            if kind=='danger':
                _motif(brush,theme,x,y,radius,phase,11)
                brush.put(x,y-2,'!',11)
            elif kind=='fever':
                _motif(brush,theme,x,y,radius*(.6+.4*phase),phase,9)
                brush.line((x,y+1),(x,y-3-phase*2),9)
            elif kind=='combo':
                for i in range(min(value,max(1,int(4*brush.quality)))):
                    _motif(brush,theme,x+(i%2-.5)*2,y-i*.7,(1+phase)*(.35+.65*strength),phase,4)
            elif kind=='b2b':
                _motif(brush,theme,x-1,y-phase*2,1.3*(.35+.65*strength),phase,7)
                _motif(brush,theme,x+1,y-1+phase*2,1.3*(.35+.65*strength),phase,7)
                brush.line((x-1,y),(x+1,y-1),7)
            else:
                _motif(brush,theme,x,y,(1+value*.2)*(.35+.65*strength),phase,6)
                brush.put(x+math.sin(t*2)*2,y-1,'=' if value<5 else '#',6)
