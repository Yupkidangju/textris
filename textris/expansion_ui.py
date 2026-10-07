"""확장 허브, 효과 갤러리, 프로필과 분석의 화면/입력."""
import curses
from .scenes import BACKGROUNDS,EFFECTS,THEMES,PROFILES
from .replay import Player
from .autoplay import Autoplayer

CATALOG=BACKGROUNDS+EFFECTS
HUB=('gallery','profiles','boss','replays','autoplay')


class ExpansionUI:
    def init_expansion(self):
        self.hub_selection=self.profile_selection=self.gallery_index=self.replay_selection=0
        self.gallery_auto=False; self.gallery_next=0.
        self.profile_return='hub'; self.analysis_return='result'; self.highlight_selection=0
        self.player=None; self.replay_paused=False; self.replay_speed=1.
        self.director=True; self.slow_until=0.; self.last_replay=None
        self.notice=''; self.bot=Autoplayer(); self.auto_restart=0.

    def open_gallery(self):
        self.screen='gallery'; self.game=None; self.session=None
        self.gallery_index=0; self.gallery_auto=False
        self.effects=type(self.effects)(); self.effects.configure(self.settings); self.effects.scene=BACKGROUNDS[0]
        self.gallery_next=self.now

    def change_profile(self,delta):
        name=PROFILES[self.profile_selection]; value=self.settings[name]
        if name=='theme': value=THEMES[(THEMES.index(value)+delta)%len(THEMES)]
        elif name in ('fx_intensity','fx_density','fx_speed'):
            value=max(.5 if name=='fx_speed' else .25,min(2 if name=='fx_speed' else 1,value+delta*.25))
        else: value=not value
        self.settings[name]=value; self.store.save()
        if name=='theme':
            scene=self.effects.scene
            self.reset_presentation()
            self.effects.scene=scene if self.screen=='gallery' else None
        self.effects.configure(self.settings)

    def gallery_trigger(self):
        name=CATALOG[self.gallery_index]
        if self.gallery_index<len(BACKGROUNDS): self.effects.scene=name
        else:
            if self.effects.scene is None: self.effects.scene=BACKGROUNDS[0]
            self.effects.preview(name,self.now)

    def expansion_handle(self,key,enter,escape,up,down,left,right):
        screen=self.screen
        if screen=='hub':
            if up or down: self.hub_selection=(self.hub_selection+(-1 if up else 1))%len(HUB)
            elif enter:
                choice=HUB[self.hub_selection]
                if choice=='gallery': self.open_gallery()
                elif choice=='profiles': self.profile_return='hub'; self.screen='profiles'
                elif choice=='boss': self.start('boss')
                elif choice=='autoplay':
                    self.start('marathon',record=False); self.screen='autoplay'; self.game.state='playing'
                    self.bot=Autoplayer(); self.auto_restart=0.
                else: self.screen='replays'; self.replay_selection=0
            elif escape or key=='q': self.screen='menu'
        elif screen=='profiles':
            if up or down: self.profile_selection=(self.profile_selection+(-1 if up else 1))%len(PROFILES)
            elif left or right or enter: self.change_profile(-1 if left else 1)
            elif escape or key=='q': self.screen=self.profile_return
        elif screen=='gallery':
            if key=='s': self.store.save()
            elif key=='a': self.gallery_auto=not self.gallery_auto; self.gallery_next=self.now+3
            elif left or right or up or down:
                self.gallery_index=(self.gallery_index+(-1 if left or up else 1))%len(CATALOG)
                self.effects.actions.clear(); self.effects.debris.clear(); self.gallery_trigger()
            elif key==' ': self.gallery_trigger()
            elif key=='t': self.profile_selection=0; self.change_profile(1)
            elif key in ('+','-'): self.profile_selection=1; self.change_profile(-1 if key=='-' else 1)
            elif key in (']','['): self.profile_selection=2; self.change_profile(-1 if key=='[' else 1)
            elif key in ('}', '{'): self.profile_selection=3; self.change_profile(-1 if key=='{' else 1)
            elif escape or key=='q': self.screen='hub'; self.reset_presentation()
        elif screen=='replays':
            files=self.replays.list()
            if up or down: self.replay_selection=(self.replay_selection+(-1 if up else 1))%max(1,len(files))
            elif enter and files:
                try: self.open_replay(self.replays.load(files[self.replay_selection]))
                except (OSError,ValueError,TypeError): self.notice='replay_error'
            elif escape or key=='q': self.screen='hub'
        elif screen=='replay':
            if escape or key=='q': self.screen='replays'; self.game=None; self.player=None
            elif key in (' ','p'): self.replay_paused=not self.replay_paused
            elif key=='a': self.analysis_return='replay'; self.screen='analysis'
            elif left or right:
                self.player.seek(self.player.session.tick+(-300 if left else 300))
                self.session=self.player.session; self.game=self.session.game
                self.reset_presentation()
            elif up or down:
                speeds=(.5,1.,2.,4.)
                self.replay_speed=speeds[(speeds.index(self.replay_speed)+(1 if up else -1))%4]
            elif key=='c': self.director=not self.director
        elif screen=='analysis':
            highlights=self.session.highlights if self.session else []
            if left or right or up or down:
                self.highlight_selection=(self.highlight_selection+(-1 if left or up else 1))%max(1,len(highlights))
            elif enter and highlights:
                data=self.player.data if self.player and self.analysis_return=='replay' else self.last_replay
                if data:
                    self.open_replay(data); self.player.seek(max(0,highlights[self.highlight_selection%len(highlights)]['tick']-60))
                    self.session=self.player.session; self.game=self.session.game
            elif escape or key=='q': self.screen=self.analysis_return
        elif screen=='autoplay':
            if escape or key=='q': self.screen='hub'; self.game=None; self.session=None
            elif key=='p': self.auto_paused=not getattr(self,'auto_paused',False)
        else: return False
        return True

    def reset_presentation(self):
        self.effects=type(self.effects)()
        self.effects.configure(self.settings)

    def open_replay(self,data):
        self.player=Player(data); self.session=self.player.session; self.game=self.session.game
        self.screen='replay'; self.replay_paused=False; self.accumulator=0.
        self.replay_speed=1.; self.slow_until=0.; self.reset_presentation()

    def draw_expansion(self):
        h,w=self.win.getmaxyx()
        if self.screen=='hub':
            self.panel(self.t('extras'),[self.t(k) for k in HUB],self.hub_selection,self.t('back'))
        elif self.screen=='profiles':
            lines=[]
            for key in PROFILES:
                value=self.settings[key]
                label=self.t('theme_'+value) if key=='theme' else f'{value:.2f}' if type(value) is float else self.t('on' if value else 'off')
                lines.append(self.t(key)+': '+label)
            self.panel(self.t('profiles'),lines,self.profile_selection,self.t('settings_hint'))
        elif self.screen=='gallery':
            name=CATALOG[self.gallery_index]
            if self.fx_enabled: self.effects.draw(self,max(1,w//2-10),max(2,h//2-10),self.now)
            self.center(1,self.t('gallery')+f' {self.gallery_index+1}/{len(CATALOG)}',curses.A_BOLD|self.color('O'))
            self.center(3,self.t('scene_'+name),curses.A_BOLD|self.color('T'))
            self.center(h-4,self.t('gallery_values',theme=self.t('theme_'+self.settings['theme']),intensity=self.settings['fx_intensity'],speed=self.settings['fx_speed'],density=self.settings['fx_density']),self.color('O'))
            self.center(h-3,self.t('gallery_hint'),curses.A_DIM)
            self.center(h-2,self.t('gallery_adjust'),curses.A_DIM)
        elif self.screen=='replays':
            files=self.replays.list()
            start=max(0,self.replay_selection-7)
            lines=[name[7:-5] for name in files[start:start+10]] or [self.t('empty_replays')]
            self.panel(self.t('replays'),lines,self.replay_selection-start if files else None,self.t('back'))
        elif self.screen=='analysis':
            s=self.session
            self.center(2,self.t('analysis'),curses.A_BOLD|self.color('O'))
            samples=s.samples or [[s.tick,s.game.score,s.game.lines]]
            maximum=max(1,max(row[1] for row in samples)); columns=min(w-10,60)
            for x in range(columns):
                row=samples[min(len(samples)-1,x*len(samples)//columns)]
                height=round(row[1]/maximum*8)
                for y in range(height): self.put(13-y,(w-columns)//2+x,'#' if self.settings['ascii'] else '▓',self.color('I'))
            self.center(15,self.t('analysis_counts',**s.counts),self.color('T'))
            marks=''.join(str(min(9,event['combo'])) for event in s.highlights[-columns:])
            self.center(17,self.t('timeline')+': '+marks,curses.A_BOLD)
            if s.highlights:
                event=s.highlights[self.highlight_selection%len(s.highlights)]
                self.center(20,f'{self.highlight_selection+1}/{len(s.highlights)}  '+self.t(event['kind'])+'  '+f'{event["tick"]/60:.1f}s')
            self.center(h-3,self.t('analysis_hint'),curses.A_DIM)

    def draw_boss(self,oy):
        hp=self.session.boss_hp
        self.center(oy+1,self.t('boss_hp',hp='/'.join(str(v) for v in hp),time=max(0,180-self.session.tick//60)),self.color('Z')|curses.A_BOLD)
        if self.win.getmaxyx()[1]>=110:
            parts=(' /[==]\\ ',' | o o | ','[|=====|]',' /|###|\\ ','[A]###[B]','  |###|  ','  /   \\  ')
            for i,row in enumerate(parts):
                if not hp[0]: row=row.replace('[A]','   ')
                if not hp[1]: row=row.replace('[B]','   ')
                if not hp[2]: row=row.replace('#',' ')
                self.put(oy+5+i,1,row,self.color('Z')|curses.A_BOLD)
