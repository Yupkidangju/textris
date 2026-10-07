"""대성당 아트와 기존 UI 사이의 읽기 전용 합성 경계."""
import curses
import math
from .art import RenderContext, game_layout
from .effects import art


class CathedralUI:
    @property
    def cathedral_enabled(self):
        return self.settings.get('theme')=='cathedral'

    def art_attr(self,style):
        return self.art_palette.attr(style,self.has_color and self.settings['color'])

    def art_context(self):
        h,w=self.win.getmaxyx()
        screen=self.confirm_return if self.screen=='confirm' else self.help_return if self.screen=='help' else self.screen
        playing=screen in ('playing','ready','paused','result','showcase','replay','autoplay') and self.game
        if playing:
            protected=game_layout(w,h).protected
        elif screen=='menu':
            protected=((w//2-29,1,58,9),(w//2-22,10,44,15),(0,h-3,w,3))
        elif screen=='gallery':
            protected=((0,1,w,3),(0,h-4,w,4))
        else:
            protected=((max(0,w//2-28),2,56,h-4),)
        return RenderContext(w,h,protected,self.settings['ascii'],self.settings.get('braille',True),1. if self.effects.quality>=.85 else .7 if self.effects.quality>=.6 else .4)

    def draw_cathedral_menu(self,logo):
        h,w=self.win.getmaxyx()
        for y in range(1,10): self.put(y,max(0,w//2-29),' '*min(58,w-1))
        self.center(1,'T E X T R I S' if self.settings['ascii'] else self.t('cathedral_kicker'),self.art_attr(8))
        rows=art('TEXTRIS',True) if self.settings['ascii'] else logo
        elapsed=max(0,self.now-self.art_epoch)
        for y,row in enumerate(rows):
            for x,ch in enumerate(row):
                if ch==' ': continue
                # 첫 진입 때만 문자 입자가 제자리에 모이고 이후에는 느린 광택만 움직인다.
                assembling=self.fx_enabled and elapsed<.8
                scatter=(1-elapsed/.8) if assembling else 0
                px=(w-len(row))//2+x+round(math.sin(x*2+y)*scatter*5)
                py=max(2,min(8,3+y+round(math.cos(x+y*3)*scatter*2)))
                shade=5 if abs((x-self.now*3)%80-40)<3 and self.fx_enabled else (5,4,3,3,6,8)[y%6]
                self.put(py,px,ch,self.art_attr(shade))
        self.center(9,self.t('cathedral_subtitle'),self.art_attr(9))
        from .storage import MODES
        options=[self.t(m) for m in MODES[:3]]+[self.t('settings'),self.t('records'),self.t('quit'),self.t('extras')]
        for i,item in enumerate(options):
            selected=i==self.selection
            text=('> ' if self.settings['ascii'] else '◆ ') if selected else '  '
            text+=item
            self.center(11+2*i,text,self.art_attr(10 if selected else 6))
            if selected:
                self.put(11+2*i,w//2-20,'--' if self.settings['ascii'] else '──',self.art_attr(9))
                self.put(11+2*i,w//2+18,'--' if self.settings['ascii'] else '──',self.art_attr(9))
        self.center(24,self.t('start_level',value=self.start_level),self.art_attr(8))
        self.center(h-3,self.t('fx_hint'),self.art_attr(4))
        self.center(h-2,self.t('menu_hint'),self.art_attr(6))
        if self.store.warning: self.center(h-1,self.t(self.store.warning),self.color('Z'))

    def cathedral_frame(self,bx,by):
        ascii_mode=self.settings['ascii']
        cue=self.effects.director.major
        local=self.effects.director.local
        style=11 if self.effects.danger else 9 if cue else 5 if local else 3
        attr=self.art_attr(style)
        if self.effects.danger:
            self.center(by-1,self.t('danger'),self.art_attr(11)|curses.A_BOLD)
        tl,tr,bl,br,hor,vert=('+','+','+','+','-','|') if ascii_mode else ('╭','╮','╰','╯','─','│')
        self.put(by,bx,tl+hor*20+tr,attr)
        self.put(by+21,bx,bl+hor*20+br,attr)
        for y in range(by+1,by+21):
            self.put(y,bx,vert,attr); self.put(y,bx+21,vert,attr)
        for y in range(by+2,by+20):
            tick=(y-by)%5==0
            for x in (bx-1,bx+22):
                self.put(y,x,'+' if tick and ascii_mode else '◇' if tick else '|' if ascii_mode else '╎',self.art_attr(8 if tick else 2))
        if cue and self.fx_enabled and self.win.getmaxyx()[0]>=38:
            word=cue.label
            if word:
                rows=art(word,self.settings['ascii'])
                # 보드 위쪽의 독립 영역에만 대형 타이포그래피를 합성한다.
                start=max(0,by-8)
                p=cue.phase(self.now)
                for i,row in enumerate(rows):
                    visible=''.join(ch if p>.2 or (j*7+i*11)%19/19<p/.2 else ' '
                                    for j,ch in enumerate(row))
                    self.center(start+i,visible,self.art_attr(9 if i<2 else 4))
