"""엔진과 독립된 문자 배경, 충격파와 중력 파편. 모든 좌표는 터미널 셀 단위."""
import curses
import math
import random
from .particles import Particle
from .scenes import BACKGROUNDS, EFFECTS, render
from .art_director import ArtDirector
from .cathedral import CathedralScene
from .art import game_layout


FONT = {
    'A':(' # ','# #','###','# #','# #'), 'B':('## ','# #','## ','# #','## '),
    'C':(' ##','#  ','#  ','#  ',' ##'), 'D':('## ','# #','# #','# #','## '),
    'E':('###','#  ','## ','#  ','###'), 'F':('###','#  ','## ','#  ','#  '),
    'G':(' ##','#  ','# #','# #',' ##'), 'H':('# #','# #','###','# #','# #'),
    'I':('###',' # ',' # ',' # ','###'), 'K':('# #','# #','## ','# #','# #'),
    'L':('#  ','#  ','#  ','#  ','###'), 'M':('# #','###','###','# #','# #'),
    'N':('# #','###','###','###','# #'), 'O':(' # ','# #','# #','# #',' # '),
    'P':('## ','# #','## ','#  ','#  '), 'R':('## ','# #','## ','# #','# #'),
    'S':(' ##','#  ',' # ','  #','## '), 'T':('###',' # ',' # ',' # ',' # '),
    'U':('# #','# #','# #','# #','###'), 'V':('# #','# #','# #','# #',' # '),
    'W':('# #','# #','###','###','# #'), 'X':('# #','# #',' # ','# #','# #'),
    '0':('###','# #','# #','# #','###'), '1':(' # ','## ',' # ',' # ','###'),
    '2':('## ','  #',' # ','#  ','###'), '3':('## ','  #',' # ','  #','## '),
    '4':('# #','# #','###','  #','  #'), '5':('###','#  ','## ','  #','## '),
    '6':(' ##','#  ','###','# #','###'), '7':('###','  #',' # ',' # ',' # '),
    '8':('###','# #','###','# #','###'), '9':('###','# #','###','  #','## '),
    'Y':('# #','# #',' # ',' # ',' # '),
    '!':(' # ',' # ',' # ','   ',' # '), ' ':('   ',)*5,
}


def art(word, ascii_mode=False):
    ink = '#' if ascii_mode else '█'
    return [' '.join(FONT.get(c,FONT[' '])[row] for c in word).replace('#',ink)
            for row in range(5)]


class Effects:
    def __init__(self):
        self.rng=random.Random(731)
        self.director=ArtDirector()
        self.cathedral=CathedralScene()
        self._art_cache=None
        self._art_key=None
        self.debris=[]; self.rings=[]; self.labels=[]; self.actions=[]
        self.shake_start=-100.; self.strength=0
        self.headline=''; self.headline_until=0.; self.priority=0
        self.glow_until=0.; self.fever=0; self.fever_until=0.; self.combo=0
        self.scene=None; self.profile={}; self.quality=1.
        self._cache={}; self._scene=None; self._previous=None; self._transition=0.
        self.danger=False; self.stage=0
        self._last_frame=[]; self._old_frame=[]; self._exploded=set()

    def configure(self,settings): self.profile=settings

    def p(self,key,default): return self.profile.get(key,default)

    def burst(self,x,y,now,amount=24,kind='O',speed=16):
        amount=max(2,int(amount*self.p('fx_density',.75)*self.quality))
        speed*=self.p('fx_intensity',.75)/.75*self.p('fx_speed',1)
        for i in range(amount):
            angle=self.rng.uniform(0,math.tau); velocity=self.rng.uniform(speed*.3,speed)
            self.debris.append(Particle(now,x,y,math.cos(angle)*velocity*2,
                math.sin(angle)*velocity-5,min(2,self.rng.uniform(.8,2)/self.p('fx_speed',1)),kind,i%4,now))
        self.debris=self.debris[-600:]

    def ring(self,x,y,now,power=1,kind='I'):
        self.rings=[p for p in self.rings if not (p[0]==now and p[1]==x and p[2]==y)]
        self.rings.append((now,x,y,power,kind)); self.rings=self.rings[-12:]

    def action(self,name,now,kind='I',coords=()):
        self.actions=[p for p in self.actions if not (p[0]==name and p[1]==now)]
        self.actions.append((name,now,kind,tuple(coords)))
        self.actions=self.actions[-24:]

    def announce(self,word,now,priority):
        if now>=self.headline_until or priority>=self.priority:
            self.headline,self.headline_until,self.priority=word,now+1.4,priority

    def trigger(self,name,data,now):
        self.director.trigger(name,data,now,self.p('fx_speed',1))
        if self.p('theme',None)=='cathedral' and self.scene is None:
            self._cathedral_event(name,data,now)
            return
        kind=data.get('kind','I')
        coords=data.get('cells',())
        if name in ('drop','lock'):
            x=sum(p[0] for p in coords)/len(coords)*2 if coords else 10
            y=max(p[1] for p in coords)-2 if coords else 19
            if name=='drop': y+=data.get('distance',0)
            power=1.5 if name=='drop' else .7
            if 0<=now-self.shake_start<.45: power=max(power,self.strength*(1-(now-self.shake_start)/.45))
            self.shake_start,self.strength=now,power
            self.burst(x,y,now,42 if name=='drop' else 16,kind,13); self.ring(x,y,now,power,kind)
            self.action('impact',now,kind,((x,y),)); self.action('elastic',now,kind)
            self.action('echoes',now,kind)
            if name=='drop':
                style={'I':'laser','O':'gold','T':'vortex','S':'electric','Z':'electric','J':'ice','L':'embers'}[kind]
                self.action(style,now,kind,((x,y),))
            self.glow_until=now+.18
        elif name=='clear':
            count=data['count']; self.combo=max(0,data['combo'])
            power=1+count*.45+min(self.combo,7)*.12+(.4 if data.get('b2b') else 0)
            self.shake_start,self.strength=now,power
            removed={(y,x):k for x,y,k in data.get('cleared_cells',())}
            for row in data['rows']:
                for x in range(10): self.burst(x*2,row-2,now,4,removed.get((row,x),'IOTSZJL'[x%7]),18+count*3)
                self.ring(10,row-2,now,power,'O' if count==4 else kind)
            cells=data.get('cleared_cells',[(x,y,'O') for y in data['rows'] for x in range(10)])
            positions=tuple((x*2,y-2) for x,y,*_ in cells)
            for effect in ('cracks','shatter','chain','lightning','smoke','ripple'):
                self.action(effect,now,'O' if count==4 else kind,positions)
            self.labels.append((now,10,10,f'+{data["points"]:,}')); self.labels=self.labels[-8:]
            perfect=data['perfect']; spin=data['spin']
            word='ALL CLEAR' if perfect else 'T SPIN' if spin else 'TETRIS' if count==4 else 'COMBO' if self.combo else ('','SINGLE','DOUBLE','TRIPLE')[count]
            self.announce(word,now,4 if perfect else 3 if spin or count==4 else 2 if self.combo else 1)
            self.action('assemble' if perfect else 'typewriter',now)
            if self.combo: self.action('odometer',now,'O')
            if perfect: self.action('blackhole',now,'T'); self.action('warp',now,'T')
            self.glow_until=now+.32
            if now>=self.fever_until:
                self.fever+=count*15+(20 if spin or count==4 else 0)+(40 if perfect else 0)
                if self.fever>=100: self.fever=100; self.fever_until=now+8; self.action('fire',now,'L')
        elif name in ('rotate','hold'):
            self.burst(10,2,now,14,'T' if name=='rotate' else kind,7)
            self.action('vortex' if name=='rotate' else 'braille',now,kind)
        elif name in ('level','go','win','gameover','boss_break'):
            if name=='level': self.stage+=1
            word={'level':'LEVEL UP','go':'GO!','win':'VICTORY','gameover':'GAME OVER','boss_break':'BREAK!'}[name]
            self.announce(word,now,5 if name in ('win','gameover') else 2)
            self.shake_start,self.strength=now,2
            for x,y in ((2,4),(18,4),(10,12)):
                self.burst(x,y,now,85,'Z' if name=='gameover' else 'IOTS'[int(x)%4],20)
                self.ring(x,y,now,2,'Z' if name=='gameover' else 'T')
            self.action('collapse' if name=='gameover' else 'victory' if name=='win' else 'warp',now,'Z' if name=='gameover' else 'T',tuple((x*2,y-2) for x,y in coords))
            if name=='win':
                for x,y in coords: self.burst(x*2,y-2,now,3,'O',18)
            self.action('glitch',now,'T'); self.glow_until=now+.3

    def _cathedral_event(self,name,data,now):
        if name=='clear':
            count=data.get('count',0); self.combo=max(0,data.get('combo',0))
            if now>=self.fever_until:
                self.fever+=count*15+(20 if data.get('spin') or count==4 else 0)+(40 if data.get('perfect') else 0)
                if self.fever>=100: self.fever=100; self.fever_until=now+8
        cue=self.director.major
        if cue:
            self.headline,self.headline_until,self.priority=cue.label,cue.end,cue.priority
        if name in ('drop','clear'):
            self.shake_start,self.strength=now,.5

    def preview(self,name,now):
        if name not in EFFECTS: raise ValueError('unknown effect')
        self.action(name,now,'I',tuple((x*2,y) for y in (15,17,19) for x in range(10)))
        if name in ('shatter','ricochet','victory','collapse','impact','gold','ice','embers','braille'):
            for x,y in ((2,16),(10,10),(18,16)): self.burst(x,y,now,70,'IOTSZJL'[int(x)%7],22)
        if name in ('impact','elastic','echoes','ripple'):
            self.ring(10,17,now,2); self.shake_start,self.strength=now,2
        if name in ('typewriter','assemble','odometer'):
            self.combo=8; self.announce('COMBO 8',now,3)

    def update(self,now):
        self.director.update(now)
        blackholes=[start for name,start,kind,coords in self.actions if name=='blackhole']
        for start in blackholes:
            age=(now-start)*self.p('fx_speed',1)
            if age<.7:
                for p in self.debris:
                    p.vx+=(10-p.x)*.8; p.vy+=(10-p.y)*.8
            elif start not in self._exploded:
                self._exploded.add(start); self.burst(10,10,now,120,'T',30); self.ring(10,10,now,3,'T')
        self._exploded={t for t in self._exploded if now-t<3}
        for p in self.debris: p.advance(now)
        self.debris=[p for p in self.debris if 0<=now-p.start<p.life]
        self.rings=[p for p in self.rings if 0<=now-p[0]<1]
        self.labels=[p for p in self.labels if 0<=now-p[0]<1.3]
        self.actions=[p for p in self.actions if 0<=now-p[1]<2/self.p('fx_speed',1)]
        if self.fever_until and now>=self.fever_until: self.fever=0; self.fever_until=0

    def offset(self,now):
        if self.p('theme',None)=='cathedral':
            return (round(math.sin((now-self.shake_start)*50)*max(0,1-(now-self.shake_start)/.18)),0) if self.p('shake',True) and 0<=now-self.shake_start<.18 else (0,0)
        age=now-self.shake_start
        if not self.p('shake',True) or not 0<=age<.45: return 0,0
        decay=(1-age/.45)**2*self.p('fx_intensity',.75)
        return round(2*min(1,self.strength)*decay*math.sin(age*95)),round(min(1,self.strength)*decay*math.cos(age*71))

    def background(self,app,now):
        self.configure(app.settings)
        if self.scene=='cathedral' or self.p('theme',None)=='cathedral' and self.scene is None:
            self.director.update(now)
            context=app.art_context()
            h,w=app.win.getmaxyx()
            board=game_layout(w,h).board if app.game else None
            active=self.director.major or self.director.local
            # 배경은 낮은 빈도로, 입력 반응은 매 프레임 갱신한다. 설정 변경은 즉시 반영한다.
            fps=24 if self.quality>=.85 else 16 if self.quality>=.65 else 10
            key=(context,int(now*fps),bool(active),self.p('fx_speed',1),self.p('flash',True),self.p('fx_intensity',.75),self.p('fx_density',.75))
            if active or key!=self._art_key:
                self._art_cache=self.cathedral.render(context,now if active else int(now*fps)/fps,self.director.major,self.director.local,
                    board,self.p('flash',True),self.p('fx_intensity',.75),self.p('fx_density',.75),self.p('fx_speed',1))
                self._art_key=key
            self._art_cache.paint(app)
            return
        h,w=app.win.getmaxyx(); t=now*self.p('fx_speed',1)
        scene=self.scene or BACKGROUNDS[(int(t/9)+self.stage)%len(BACKGROUNDS)]
        if self.fever_until>now and self.scene is None: scene='fluid'
        if self.scene is None and any(name=='warp' and now-start<1 for name,start,kind,coords in self.actions): scene='warp'
        if scene!=self._scene:
            self._old_frame=self._last_frame
            self._previous=self._scene; self._scene=scene; self._transition=now
        stride=2 if self.quality>=.65 else 3
        cols=(w-1)//stride; rows=min(h,32 if self.quality>=.65 else 20)
        ascii_mode=app.settings['ascii'] or scene=='braille' and not self.p('braille',True)
        key=(scene,cols,rows,int(now*20),ascii_mode)
        if key not in self._cache:
            frame=render(scene,cols,rows,t,ascii_mode)
            self._cache[key]=frame
            if len(self._cache)>4: del self._cache[next(iter(self._cache))]
        frame=self._cache[key]
        phase=min(1,(now-self._transition)/.8)
        impact=next((start for name,start,kind,coords in reversed(self.actions) if name=='impact' and now-start<.6),None)
        for sy,row in enumerate(frame):
            y=int(sy*h/rows)
            if impact is not None: y+=round(math.sin(sy*.8-(now-impact)*20)*2*(1-(now-impact)/.6))
            if phase<1 and self._old_frame:
                old=self._old_frame[min(sy,len(self._old_frame)-1)]
                row=''.join(old[min(x,len(old)-1)] if (x*13+sy*17)%29/29>phase else c for x,c in enumerate(row))
            text=''.join(c+' '*(stride-1) for c in row)
            attr=app.fx_color(sy+int(t*3)) if hasattr(app,'fx_color') else app.color('IOTSZJL'[sy%7])
            if self.fever_until>now: attr=app.color('IOTSZJL'[(sy+int(t*8))%7])
            if self.danger: attr=app.color('Z')
            app.put(y,0,text,attr|curses.A_DIM)
        self._last_frame=frame
        ribbon='0101 / TEXTRIS / <> / '*8
        for x in range(0,w-1,4):
            y=round(h/2+math.sin(x*.09+t)*max(2,h/3))
            app.put(y,x,ribbon[(x//2+int(t*5))%len(ribbon)],app.color('T')|curses.A_DIM)
        # 세 깊이의 별은 저해상도 장면 위에서 개별 이동한다.
        for i in range(24):
            x=int((i*37+t*(1+i%3))%max(1,w-1)); y=int((i*11+t*(.3+i%2))%h)
            app.put(y,x,'.' if i%3==0 else '+' if ascii_mode else '✦',app.color('IOTSZJL'[i%7])|curses.A_DIM)
        if self.danger:
            app.center(1,app.t('danger'),app.color('Z')|curses.A_BOLD)
        if self.p('theme','cyberpunk')=='crt':
            for y in range(int(t*7)%3,h,3): app.put(y,0,'-'*(w-1),app.color('S')|curses.A_DIM)
        beat=app.audio.visual_state(now)[1] if hasattr(app.audio,'visual_state') else max(0,math.sin(t*math.tau*4))
        for i in range(12):
            bar=1+int((math.sin(i*.7+t)*.5+.5)*beat*4)
            app.put(h-2-i%2,2+i*2,('|' if ascii_mode else '▂')*min(2,bar),app.color('IOTSZJL'[i%7])|curses.A_DIM)

    def reflection(self,app,bx,by,now):
        if self.p('theme',None)=='cathedral' and self.scene is None: return
        if app.win.getmaxyx()[0]<36 or not app.game: return
        h,w=app.win.getmaxyx()
        if by+22>=h-1: return
        for i in range(min(4,h-by-23)):
            row=app.game.board[21-i]
            text=''.join(('[]' if app.settings['ascii'] else '▒▒') if kind else '  ' for kind in row)
            app.put(by+22+i,bx+round(math.sin(now*3+i)),text,app.color('I')|curses.A_DIM)

    def draw(self,app,bx,by,now):
        if self.p('theme',None)=='cathedral' and self.scene is None: return
        ascii_mode=app.settings['ascii']; speed=self.p('fx_speed',1)
        for name,start,kind,coords in self.actions:
            age=(now-start)*speed
            attr=app.color(kind)|(curses.A_DIM if self.p('fx_intensity',.75)<=.25 else curses.A_BOLD)
            ink='*' if ascii_mode else '✦'
            if name=='focus':
                x,y=coords[0]
                for dx,dy,c in ((-5,-2,'>'),(5,-2,'<'),(-5,2,'>'),(5,2,'<')):
                    app.put(by+round(y)+dy,bx+round(x)+dx,c,attr)
                app.put(by+round(y)-3,bx+round(x)-3,'[FOCUS]',attr)
            elif name in ('elastic','echoes'):
                for i in range(1,4 if name=='echoes' else 2):
                    dx=round(i*(1-age)*2); dy=round(math.sin(age*15)*max(0,1-age))
                    app.put(by+20+dy+i%2,bx-dx,'+'+'-'*(20+dx*2)+'+',attr|curses.A_DIM)
            elif name in ('cracks','shatter','chain'):
                for i,(x,y) in enumerate(coords):
                    if name=='chain' and abs(x-min(18,age*24))>3: continue
                    app.put(by+round(y),bx+round(x),('/' if i%2 else '\\') if name=='cracks' else ink,attr)
            elif name in ('lightning','electric','laser'):
                for i in range(20):
                    x=10 if name=='laser' else 10+round(math.sin(i*2+age*35)*3)
                    app.put(by+i,bx+x,'|' if ascii_mode or name=='laser' else 'ϟ',attr)
                    if name!='laser' and i%4==0: app.put(by+i,bx+x+2,'--' if ascii_mode else '╱─',attr)
            elif name in ('blackhole','vortex','gold','warp','ripple'):
                for i in range(48):
                    angle=i*math.tau/24+age*5
                    radius=(1-age)*12 if name=='blackhole' and age<1 else age*13 if name in ('warp','ripple') else 6+math.sin(age*6+i)*3
                    x=10+math.cos(angle)*radius*1.6; y=10+math.sin(angle)*radius*.65
                    app.put(by+round(y),bx+round(x),ink,attr)
            elif name in ('smoke','fire','embers','ice','braille'):
                for i in range(28):
                    x=(i*7)%22+math.sin(age*3+i)*2
                    y=19-age*(6+i%5)+(i%3)
                    glyph=('~' if name=='smoke' else '^' if name=='fire' else '+' if name=='ice' else '*') if ascii_mode else ('░' if name=='smoke' else '▓' if name=='fire' else '❄' if name=='ice' else chr(0x2800+(1<<(i%8))) if name=='braille' and self.p('braille',True) else '✦')
                    app.put(by+round(y),bx+round(x),glyph,attr|curses.A_DIM if name=='smoke' else attr)
            elif name=='glitch':
                for i in range(5):
                    app.put(by+i*4,bx+round(math.sin(age*45+i)*4),'< / 01 # >'[(i+int(age*30))%7:]+ ' //',attr)
            elif name in ('victory','collapse'):
                points=coords or tuple((i%10*2,i//10*6) for i in range(24))
                for x,y in points:
                    y=y+(age*age*10 if name=='collapse' else -age*9)
                    app.put(by+round(y),bx+x,'##' if ascii_mode else '▓▓' if name=='collapse' else '✦',attr)
            elif name=='odometer':
                number=int(self.combo*min(1,age*3))
                app.put(by+2,bx+4,f'COMBO {number:02}',app.color('O')|curses.A_BOLD)
            elif name in ('typewriter','assemble'):
                word=self.headline[:max(1,int(age*len(self.headline)*4))] if name=='typewriter' else self.headline
                for i,c in enumerate(word):
                    scatter=max(0,1-age/.7) if name=='assemble' else 0
                    app.put(by+3+round(math.sin(i*2)*scatter*8),bx-2+i+round(math.cos(i*2)*scatter*16),c,attr)
            elif name in ('ricochet','impact'):
                app.put(by+19,bx,('/'*20 if age<.3 else '.'*20),attr)
        for start,x,y,power,kind in self.rings:
            age=(now-start)*speed; rx=age*(20+power*9); ry=rx/2.5
            for i in range(32):
                a=i*math.tau/32
                app.put(round(by+y+math.sin(a)*ry),round(bx+x+math.cos(a)*rx),'.' if age>.7 else '*' if ascii_mode else '✧',app.color(kind)|curses.A_BOLD)
        glyph=('*','+','#','.') if ascii_mode else ('✦','◆','▓','·')
        dots={}
        for p in self.debris[-max(120,int(600*self.quality)):]:
            age=now-p.start
            if age>=p.life: continue
            attr=app.color(p.kind)|(curses.A_DIM if age>p.life*.65 else curses.A_BOLD)
            if not ascii_mode and self.p('braille',True) and p.shape:
                px=math.floor((bx+p.x)*2); py=math.floor((by+p.y)*4)
                cell=(px//2,py//4)
                bit=((0,1,2,6),(3,4,5,7))[px%2][py%4]
                mask=dots.get(cell,(0,attr))[0]|(1<<bit)
                dots[cell]=(mask,attr)
            else: app.put(round(by+p.y),round(bx+p.x),glyph[p.shape],attr)
        for (x,y),(mask,attr) in dots.items(): app.put(y,x,chr(0x2800+mask),attr)
        for start,x,y,text in self.labels:
            app.put(round(by+y-(now-start)*6),round(bx+x-len(text)/2),text,app.color('O')|curses.A_BOLD)
        if now<self.headline_until:
            h,w=app.win.getmaxyx()
            fullscreen=getattr(app,'screen','') in ('gallery','showcase')
            if fullscreen or w>=100 and h>=36:
                typing=next((start for name,start,kind,coords in reversed(self.actions) if name=='typewriter'),None)
                word=self.headline[:max(1,int((now-typing)*len(self.headline)*4))] if typing is not None else self.headline
                rows=art(word,ascii_mode)
                base=max(1,by+5) if fullscreen else max(0,by-4)
                for i,row in enumerate(rows): app.center(base+i,row,app.color('IOTSZJL'[(i+int(now*8))%7])|curses.A_BOLD)
