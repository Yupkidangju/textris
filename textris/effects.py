"""게임과 독립된 공통 아트 무대, 성취 시간축과 갤러리 연출."""
import math
from .scenes import BACKGROUNDS, EFFECTS
from .art_director import ArtDirector, Cue
from .theme_art import ThemeScene
from .gallery_art import GalleryArt
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
        self.director=ArtDirector()
        self.stage=ThemeScene()
        self.gallery=GalleryArt()
        self._art_cache=None; self._art_key=None
        self.scene=None; self.profile={}; self.quality=1.
        self.actions=[]
        self.shake_start=-100.; self.strength=0.
        self.headline=''; self.headline_until=0.; self.priority=0
        self.glow_until=0.; self.fever=0; self.fever_until=0.; self.combo=0
        self.danger=False

    def configure(self,settings): self.profile=settings

    def p(self,key,default): return self.profile.get(key,default)

    def trigger(self,name,data,now):
        self.director.trigger(name,data,now,self.p('fx_speed',1))
        if name=='clear':
            count=data.get('count',0); self.combo=max(0,data.get('combo',0))
            if now>=self.fever_until:
                self.fever+=count*15+(20 if data.get('spin') or count==4 else 0)+(40 if data.get('perfect') else 0)
                if self.fever>=100: self.fever=100; self.fever_until=now+8
        cue=self.director.major
        if cue: self.headline,self.headline_until,self.priority=cue.label,cue.end,cue.priority
        if name in ('drop','clear'):
            self.shake_start,self.strength=now,.5

    def action(self,name,now,kind='I',coords=()):
        if name=='focus':
            self.director.local.append(Cue('focus',now,now+.5,coords=tuple(coords)))
            self.director.local=self.director.local[-8:]
        elif name in EFFECTS:
            self.preview(name,now)

    def preview(self,name,now):
        if name not in EFFECTS: raise ValueError('unknown effect')
        self.actions=[(name,now)]

    def update(self,now):
        self.director.update(now)
        self.actions=[(name,start) for name,start in self.actions if 0<=now-start<2/self.p('fx_speed',1)]
        if self.fever_until and now>=self.fever_until: self.fever=0; self.fever_until=0

    def offset(self,now):
        age=now-self.shake_start
        if not self.p('shake',True) or not 0<=age<.18: return 0,0
        return round(math.sin(age*50)*max(0,1-age/.18)*self.p('fx_intensity',.75)/.75),0

    def background(self,app,now):
        self.configure(app.settings); self.update(now)
        context=app.art_context()
        h,w=app.win.getmaxyx()
        board=game_layout(w,h).board if app.game else None
        active=self.director.major or self.director.local
        fps=24 if self.quality>=.85 else 16 if self.quality>=.65 else 10
        key=(context,int(now*fps),bool(active),self.scene,self.p('theme','cathedral'),
             self.p('fx_speed',1),self.p('flash',True),self.p('fx_intensity',.75),self.p('fx_density',.75))
        if active or key!=self._art_key:
            stamp=now if active else int(now*fps)/fps
            if self.scene:
                self._art_cache=self.gallery.render(context,stamp*self.p('fx_speed',1),self.scene,
                    intensity=self.p('fx_intensity',.75),density=self.p('fx_density',.75),flash=self.p('flash',True))
            else:
                self._art_cache=self.stage.render(context,stamp,self.p('theme','cathedral'),
                    self.director.major,self.director.local,board,self.p('flash',True),
                    self.p('fx_intensity',.75),self.p('fx_density',.75),self.p('fx_speed',1))
            self._art_key=key
        self._art_cache.paint(app)

    def draw(self,app,bx,by,now):
        if app.screen!='gallery': return
        self.configure(app.settings)
        context=app.art_context()
        for name,start in self.actions:
            self.gallery.render(context,now*self.p('fx_speed',1),name,
                age=(now-start)*self.p('fx_speed',1),intensity=self.p('fx_intensity',.75),
                density=self.p('fx_density',.75),flash=self.p('flash',True)).paint(app)

    def reflection(self,app,bx,by,now):
        # 반사는 갤러리의 전용 고해상도 장면으로 제공한다.
        pass
