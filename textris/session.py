"""고정 틱, 보스와 분석. 시각 설정과 독립적인 게임 세션."""
import hashlib
import json
import secrets
from .engine import Game

STEP = 1/60
COMMANDS = ('left','right','soft','cw','ccw','hold','drop')


class Session:
    def __init__(self,seed=None,mode='marathon',level=1,record=True):
        self.seed=seed if seed is not None else secrets.randbits(63)
        self.mode,self.level=mode,level
        self.game=Game(self.seed,'marathon' if mode=='boss' else mode,level)
        self.tick=0
        self.actions=[]
        self.max_actions=100000
        self.recording=record
        self.warning=''
        self.boss_hp=[60,60,60] if mode=='boss' else []
        self.samples=[]
        self.highlights=[]
        self.counts=dict(tetris=0,tspin=0,perfect=0,max_combo=0)
        self._processed=[]
        self._pending_clears=[]
        self._terminal=None

    def command(self,name):
        if name not in COMMANDS: raise ValueError('invalid command')
        if self.game.state!='playing': return
        if self.recording:
            if len(self.actions)>=self.max_actions or self.tick>=432000:
                self.recording=False; self.warning='replay_limit'
            else: self.actions.append([self.tick,name])
        g=self.game
        if name=='left': g.move(-1,0)
        elif name=='right': g.move(1,0)
        elif name=='soft': g.move(0,1,soft=True)
        elif name=='cw': g.rotate(1)
        elif name=='ccw': g.rotate(-1)
        elif name=='hold': g.hold()
        else: g.hard_drop()

    def step(self):
        self.game.update(STEP)
        self.tick+=1
        self.observe(finalize=True)
        if self.recording and self.tick>=432000:
            self.recording=False; self.warning='replay_limit'

    def observe(self,finalize=False):
        g=self.game
        old={id(e) for e in self._processed}
        for event in list(g.events):
            if id(event) in old: continue
            if event.name=='clear':
                d=event.data
                self.counts['tetris']+=d['count']==4
                self.counts['tspin']+=bool(d['spin'])
                self.counts['perfect']+=bool(d['perfect'])
                self.counts['max_combo']=max(self.counts['max_combo'],d['combo'])
                if len(self.highlights)<10000:
                    self.highlights.append(dict(tick=max(0,self.tick-1) if finalize else self.tick,score=g.score,
                                                combo=d['combo'],kind='perfect' if d['perfect'] else 'tspin' if d['spin'] else 'tetris' if d['count']==4 else 'clear'))
                if self.mode=='boss': self._pending_clears.append(dict(d))
        if finalize:
            if self.mode=='boss' and g.state!='over':
                for d in self._pending_clears:
                    damage=(0,10,25,45,70)[d['count']]+20*bool(d['spin'])+40*bool(d['perfect'])
                    for i,hp in enumerate(self.boss_hp):
                        hit=min(hp,damage); self.boss_hp[i]-=hit; damage-=hit
                        if hp and not self.boss_hp[i]: g.emit('boss_break',part=i)
                    g.emit('boss_hit',hp=self.boss_hp[:])
            self._pending_clears.clear()
        if finalize and self.mode=='boss' and g.state not in ('over','won'):
            if not any(self.boss_hp): g.state='won'; g.emit('win')
            elif self.tick>=10800: g.state='over'; g.emit('gameover')
        if finalize and self.tick%60==0 and len(self.samples)<7200 and (not self.samples or self.samples[-1][0]!=self.tick):
            self.samples.append([self.tick,g.score,g.lines])
        self._processed=g.events[:]

    def checksum(self):
        g=self.game
        state=[g.board,[g.active.kind,g.active.rotation,g.active.x,g.active.y],list(g.queue),
               g.held,g.hold_used,g.score,g.lines,g.level,g.elapsed,g.gravity_elapsed,
               g.lock_elapsed,g.lock_resets,g.combo,g.b2b,g.last_rotate,g.state,
               self.tick,self.boss_hp,g.rng.getstate()]
        return hashlib.sha256(json.dumps(state,separators=(',',':')).encode()).hexdigest()

    def replay(self):
        return dict(version=1,rules=1,seed=self.seed,mode=self.mode,level=self.level,
                    actions=self.actions[:],end_tick=self.tick,checksum=self.checksum(),
                    counts=dict(self.counts),samples=self.samples[:],highlights=self.highlights[:])
