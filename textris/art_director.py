"""게임 시간에 영향을 주지 않는 유한한 성취/국소 연출 시간축."""
from dataclasses import dataclass


@dataclass
class Cue:
    name: str
    start: float
    end: float
    priority: int=0
    power: float=1.
    coords: tuple=()
    label: str=''

    def phase(self,now):
        return max(0.,min(1.,(now-self.start)/(self.end-self.start)))


class ArtDirector:
    def __init__(self):
        self.major=None
        self.local=[]

    def update(self,now):
        if self.major and now>=self.major.end: self.major=None
        self.local=[cue for cue in self.local if now<cue.end]

    def trigger(self,name,data,now,speed=1.):
        self.update(now)
        if name in ('drop','lock','rotate','hold'):
            if name=='lock' and any(c.name=='drop' and now-c.start<.1 for c in self.local): return
            coords=tuple((x*2,y-2+(data.get('distance',0) if name=='drop' else 0))
                         for x,y in data.get('cells',()))
            duration=.35 if name in ('drop','lock') else .22
            self.local.append(Cue(name,now,now+duration/speed,coords=coords))
            self.local=self.local[-8:]
            return
        if name=='clear':
            kind='ascension' if data.get('perfect') else 'bloom' if data.get('count')==4 or data.get('spin') else 'clear'
            priority={'ascension':4,'bloom':3,'clear':1}[kind]
            duration={'ascension':1.8,'bloom':1.2,'clear':.55}[kind]
        elif name in ('win','gameover','level','go','boss_break'):
            kind={'win':'victory','gameover':'eclipse','level':'awakening','go':'awakening','boss_break':'bloom'}[name]
            priority=5 if name in ('win','gameover') else 2
            duration=1.8 if priority==5 else .9
        else: return
        if self.major and self.major.priority>=priority:
            self.major.power=min(1.6,self.major.power+.08)
            return
        label=('ALL CLEAR' if data.get('perfect') else 'T SPIN' if data.get('spin') else 'TETRIS' if data.get('count')==4 else ('','SINGLE','DOUBLE','TRIPLE')[data.get('count',0)]) if name=='clear' else {'win':'VICTORY','gameover':'GAME OVER','level':'LEVEL UP','go':'GO!','boss_break':'BREAK!'}[name]
        self.major=Cue(kind,now,now+duration/speed,priority,
                       min(1.6,1+max(0,data.get('combo',0))*.04),
                       tuple(data.get('rows',())),label)
