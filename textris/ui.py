"""curses 화면, 키보드 상태 전이와 이벤트 기반 텍스트 애니메이션."""
import curses
from datetime import datetime
import math
import queue
import random
import time
import unicodedata
from functools import lru_cache

from .engine import Game, Piece, cells, HIDDEN
from .effects import Effects
from .i18n import tr
from .storage import MODES
from .session import Session,STEP
from .replay import ReplayStore
from .expansion_ui import ExpansionUI, CATALOG
from .art import Palette
from .art_ui import CathedralUI

LOGO = (
    '████████╗███████╗██╗  ██╗████████╗██████╗ ██╗███████╗',
    '╚══██╔══╝██╔════╝╚██╗██╔╝╚══██╔══╝██╔══██╗██║██╔════╝',
    '   ██║   █████╗   ╚███╔╝    ██║   ██████╔╝██║███████╗',
    '   ██║   ██╔══╝   ██╔██╗    ██║   ██╔══██╗██║╚════██║',
    '   ██║   ███████╗██╔╝ ██╗   ██║   ██║  ██║██║███████║',
    '   ╚═╝   ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝',
)
NUMBERS = {
    3: ('###','  #','###','  #','###'),
    2: ('###','  #','###','#  ','###'),
    1: (' # ','## ',' # ',' # ','###'),
}


@lru_cache(maxsize=512)
def cell_width(c):
    return 0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ('W','F') else 1


def width(text):
    return sum(cell_width(c) for c in text)


def clip(text, limit):
    result, used = [], 0
    for c in text:
        w = cell_width(c)
        if used+w > limit:
            break
        result.append(c); used += w
    return ''.join(result)


def clock(seconds):
    seconds = max(0,seconds)
    return f'{int(seconds)//60:02}:{int(seconds)%60:02}.{int(seconds*10)%10}'


class App(CathedralUI, ExpansionUI):
    def __init__(self, window, store, audio, seed=None):
        self.win, self.store, self.audio, self.seed = window, store, audio, seed
        self.settings = store.settings
        self.screen = 'menu'
        self.selection = self.setting_selection = self.pause_selection = 0
        self.mode_index = 0
        self.start_level = 1
        self.game = None
        self.session = None
        self.accumulator = 0.
        self.replays = ReplayStore(store.directory)
        self.init_expansion()
        self.ready_elapsed = 0.
        self.help_return = 'menu'
        self.confirm_return = 'playing'
        self.confirm_action = 'quit'
        self.running = True
        self.now = time.monotonic()
        self.art_epoch=self.now
        self.flash_until = 0.
        self.flash_rows = []
        self.trails = []
        self.particles = []
        self.banner = ''
        self.banner_until = 0.
        self.result_since = 0.
        self.new_record = False
        self.fx_rng = random.Random(19)
        self.effects = Effects()
        self.fx_enabled = True
        self.showcase_step = 0
        self.showcase_next = 0.
        self.has_color = False
        self.art_palette=Palette()
        self._setup()

    def _setup(self):
        self.win.keypad(True)
        self.win.nodelay(True)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        if hasattr(curses,'set_escdelay'):
            curses.set_escdelay(25)
        if curses.has_colors():
            curses.start_color()
            background = curses.COLOR_BLACK
            try:
                curses.use_default_colors(); background = -1
            except curses.error:
                pass
            colors = (curses.COLOR_CYAN,curses.COLOR_YELLOW,curses.COLOR_MAGENTA,
                      curses.COLOR_GREEN,curses.COLOR_RED,curses.COLOR_BLUE,curses.COLOR_WHITE)
            try:
                for i,color in enumerate(colors,1):
                    curses.init_pair(i,color,background)
                self.has_color = True
                self.art_palette.setup(curses.COLORS,curses.COLOR_PAIRS)
            except curses.error:
                pass

    def t(self, key, **values):
        return tr(self.settings['language'],key,**values)

    def color(self, kind=None):
        if not self.has_color or not self.settings['color']:
            return 0
        if self.settings.get('theme')=='mono': return 0
        if self.cathedral_enabled:
            return self.art_attr(16+'IOTSZJL'.index(kind)) if kind else self.art_attr(3)
        return curses.color_pair('IOTSZJL'.index(kind)+1 if kind in 'IOTSZJL' else 1) if kind else curses.color_pair(1)

    def fx_color(self,index):
        palette={'cathedral':'IITIJOL','cyberpunk':'ITIZTJL','space':'IJITJLI','fire':'ZOLZOLZ','crt':'SSSIOOS','mono':'IIIIIII'}
        return self.color(palette[self.settings.get('theme','cyberpunk')][index%7])

    def put(self, y, x, text, attr=0):
        h,w = self.win.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w-1:
            return
        text = clip(str(text),w-x-1)
        if self.cathedral_enabled and not attr & curses.A_COLOR:
            attr |= self.art_attr(15 if text.strip() else 0)
        canvas=getattr(self,'_canvas',None)
        if canvas is not None:
            for c in text:
                size=cell_width(c)
                if size==0:
                    if x: canvas[y][x-1]=(canvas[y][x-1][0]+c,attr)
                    continue
                # 넓은 글자의 어느 셀을 덮어도 기존 소유자와 연속 셀을 함께 정리한다.
                for target in range(x,x+size):
                    old,old_attr=canvas[y][target]
                    if not old and target>0: canvas[y][target-1]=(' ',old_attr)
                    elif old and cell_width(old[0])==2 and target+1<len(canvas[y]): canvas[y][target+1]=(' ',old_attr)
                canvas[y][x]=(c,attr)
                if size==2: canvas[y][x+1]=('',attr)
                x+=size
            return
        try:
            self.win.addstr(y,x,text,attr)
        except curses.error:
            pass

    def center(self, y, text, attr=0):
        self.put(y,max(0,(self.win.getmaxyx()[1]-width(text))//2),text,attr)

    def panel(self, title, lines, selected=None, footer=None):
        h,w = self.win.getmaxyx()
        ph = min(h-2,max(8,len(lines)+6)); pw = min(w-2,52)
        y,x = (h-ph)//2,(w-pw)//2
        for row in range(ph):
            self.put(y+row,x,' '*pw)
        self.put(y,x,'+'+'-'*(pw-2)+'+',self.color())
        self.put(y+ph-1,x,'+'+'-'*(pw-2)+'+',self.color())
        for row in range(1,ph-1):
            self.put(y+row,x,'|',self.color()); self.put(y+row,x+pw-1,'|',self.color())
        self.put(y+1,x+max(1,(pw-width(title))//2),title,curses.A_BOLD|self.color('O'))
        for i,line in enumerate(lines):
            attr = curses.A_REVERSE|curses.A_BOLD if selected == i else 0
            prefix = '> ' if selected == i else '  '
            self.put(y+3+i,x+3,clip(prefix+line,pw-6),attr)
        if footer:
            self.put(y+ph-2,x+max(1,(pw-width(footer))//2),clip(footer,pw-2),curses.A_DIM)

    def _background(self):
        if self.fx_enabled:
            self.effects.background(self,self.now)

    def draw_menu(self):
        if self.cathedral_enabled:
            self.draw_cathedral_menu(LOGO)
            return
        h,_ = self.win.getmaxyx()
        if self.settings['ascii']:
            for i,text in enumerate(('T E X T R I S','[ ][ ][ ][ ][ ][ ][ ]')):
                self.center(3+i,text,curses.A_BOLD|self.color('I'))
        else:
            for i,row in enumerate(LOGO):
                # 가로 파형으로 이동해 이웃 행을 덮어쓰지 않는다.
                x = (self.win.getmaxyx()[1]-width(row))//2+round(math.sin(self.now*2+i*.6))
                self.put(2+i,max(0,x),row,self.color('IOTSZJL'[i])|curses.A_BOLD)
        self.center(9,self.t('subtitle'),curses.A_DIM)
        options = [self.t(m) for m in MODES[:3]]+[self.t('settings'),self.t('records'),self.t('quit'),self.t('extras')]
        for i,item in enumerate(options):
            text = ('▶ ' if i == self.selection and not self.settings['ascii'] else '> ' if i == self.selection else '  ')+item
            self.center(11+2*i,text,curses.A_REVERSE|curses.A_BOLD if i == self.selection else 0)
        self.center(24,self.t('start_level',value=self.start_level),self.color('O'))
        self.center(h-3,self.t('fx_hint'),self.color('T')|curses.A_BOLD)
        self.center(h-2,self.t('menu_hint'),curses.A_DIM)
        if self.store.warning:
            self.center(h-1,self.t(self.store.warning),self.color('Z'))

    def draw_settings(self):
        keys = ['language','sound','music','volume','ascii','color']
        lines = []
        for key in keys:
            value = self.settings[key]
            if key == 'language':
                label = '한국어' if value == 'ko' else 'English'
            elif key == 'volume':
                label = f'{round(value*100)}%'
            else:
                label = self.t('on' if value else 'off')
            lines.append(f'{self.t(key):<12}  {label}')
        lines.append(self.t('profiles'))
        self.panel(self.t('settings'),lines,self.setting_selection,self.t('settings_hint'))
        self.center(self.win.getmaxyx()[0]-3,self.t('sound_status',value=self.audio_label()),curses.A_DIM)

    def audio_label(self):
        if not self.settings['sound'] or self.settings['volume'] <= 0:
            return self.t('audio_muted')
        return self.t('audio_bell') if self.audio.status == 'audio_bell' else self.audio.status

    def draw_records(self):
        mode = MODES[self.mode_index]
        self.center(3,self.t('records')+' / '+self.t(mode),curses.A_BOLD|self.color('O'))
        self.center(6,self.t('record_head'),curses.A_DIM)
        rows = self.store.records[mode]
        if not rows:
            self.center(12,self.t('empty_records'))
        for i,r in enumerate(rows):
            line = f'{i+1:2}  {r["score"]:10,}  {r["lines"]:5}  {clock(r["seconds"]):>7}  {r["date"][:10]}'
            if mode == 'sprint' and r['completed']:
                line += ' *'
            self.center(8+i,line,self.color('I') if i == 0 else 0)
        self.center(24,self.t('records_hint'),curses.A_DIM)

    def preview(self, kind, y, x, dim=False):
        if not kind:
            return
        char = '[]' if self.settings['ascii'] else '██'
        for px,py in cells(Piece(kind,0,0,0)):
            self.put(y+py,x+2*px,char,self.color(kind)|(curses.A_DIM if dim else curses.A_BOLD))

    def draw_game(self):
        g = self.game
        h,w = self.win.getmaxyx()
        ox,oy = (w-64)//2,max(0,(h-28)//2)
        # HUD는 고정하고 보드와 그에 속한 효과만 흔든다.
        if not self.cathedral_enabled:
            for row in range(oy+2,oy+25):
                self.put(row,ox+1,' '*19)
                self.put(row,ox+44,' '*19)
        dx,dy=self.effects.offset(self.now) if self.fx_enabled else (0,0)
        bx,by = ox+21+dx,oy+3+dy
        self.center(oy,'T E X T R I S  /  '+self.t(self.session.mode if self.session else g.mode),curses.A_BOLD|self.color())
        border=self.color('Z')|(curses.A_BOLD if math.sin(self.now*4)>0 else curses.A_DIM) if self.effects.danger and self.settings.get('flash',True) else self.color('Z') if self.effects.danger else self.color()
        self.put(by,bx,'+'+'-'*20+'+',border)
        self.put(by+21,bx,'+'+'-'*20+'+',border)
        if self.fx_enabled and self.settings.get('flash',True) and self.now < self.effects.glow_until:
            self.put(by,bx,'+'+'='*20+'+',self.color('O')|curses.A_BOLD)
            self.put(by+21,bx,'+'+'='*20+'+',self.color('O')|curses.A_BOLD)
        glyph = '[]' if self.settings['ascii'] else '██'
        empty = '. ' if self.settings['ascii'] else '· '
        ghost = '::' if self.settings['ascii'] else '░░'
        for y in range(20):
            self.put(by+1+y,bx,'|',self.color())
            self.put(by+1+y,bx+21,'|',self.color())
            for x in range(10):
                kind = g.board[y+HIDDEN][x]
                pattern = ('. ', ': ', '· ', '░ ')[(x+y+int(self.now*4))%4] if self.fx_enabled else empty
                if self.settings['ascii']: pattern = '. ' if (x+y+int(self.now*3))%5 else ': '
                if self.cathedral_enabled: pattern='  '
                self.put(by+1+y,bx+1+2*x,glyph if kind else pattern,self.color(kind) if kind else curses.A_DIM)
        if g.state in ('playing','paused'):
            p = g.active
            for x,y in cells(Piece(p.kind,p.rotation,p.x,g.ghost_y())):
                if y >= HIDDEN:
                    self.put(by+1+y-HIDDEN,bx+1+2*x,ghost,self.color(p.kind)|curses.A_DIM)
            for x,y in cells(p):
                if y >= HIDDEN:
                    self.put(by+1+y-HIDDEN,bx+1+2*x,glyph,self.color(p.kind)|curses.A_BOLD)
        for start,coords,distance in ([] if self.cathedral_enabled else self.trails):
            if self.now-start < .18:
                for x,y in coords:
                    for dy in range(0,distance,2):
                        if HIDDEN <= y+dy < 22:
                            self.put(by+1+y+dy-HIDDEN,bx+1+2*x,'||' if self.settings['ascii'] else '╎╎',curses.A_DIM|self.color('I'))
        if not self.cathedral_enabled and self.settings.get('flash',True) and self.now < self.flash_until and int(self.now*30) % 2 == 0:
            for y in self.flash_rows:
                if y >= HIDDEN:
                    self.put(by+1+y-HIDDEN,bx+1,'='*20,curses.A_BOLD|self.color('O'))
        for start,x,y,vx,vy in ([] if self.fx_enabled else self.particles):
            age = self.now-start
            if age < .5:
                px = int(bx+1+x*2+vx*age)
                py = int(by+1+y-HIDDEN+vy*age+10*age*age)
                self.put(py,px,'*' if self.settings['ascii'] else '✦',self.color('O')|curses.A_BOLD)
        if self.screen == 'result':
            fill = min(20,int((self.now-self.result_since)*34))
            for y in range(20-fill,20):
                self.put(by+1+y,bx+1,'..'*10 if self.settings['ascii'] else '░░'*10,curses.A_DIM)
        if self.fx_enabled:
            self.effects.draw(self,bx+1,by+1,self.now)
        if self.fx_enabled:
            self.effects.reflection(self,bx+1,by+1,self.now)
        # 최종 게임 정보는 연출보다 위에 그려 판정과 고스트를 보존한다.
        if self.screen != 'result' and not self.cathedral_enabled:
            for y,row in enumerate(g.board[HIDDEN:]):
                for x,kind in enumerate(row):
                    if kind: self.put(by+1+y,bx+1+2*x,glyph,self.color(kind)|curses.A_BOLD)
            if g.state in ('playing','paused'):
                p=g.active
                for x,y in cells(Piece(p.kind,p.rotation,p.x,g.ghost_y())):
                    if y>=HIDDEN: self.put(by+1+y-HIDDEN,bx+1+2*x,ghost,self.color(p.kind)|curses.A_DIM)
                for x,y in cells(p):
                    if y>=HIDDEN: self.put(by+1+y-HIDDEN,bx+1+2*x,glyph,self.color(p.kind)|curses.A_BOLD)
        if self.cathedral_enabled: self.cathedral_frame(bx,by)
        if not self.cathedral_enabled:
            for row in range(oy+2,oy+25):
                self.put(row,ox+1,' '*19); self.put(row,ox+44,' '*19)
        self.put(oy+3,ox+2,self.t('hold'),curses.A_BOLD)
        self.preview(g.held,oy+5,ox+4,g.hold_used)
        stats = [('score',f'{g.score:,}'),('best',f'{self.best_score(self.session.mode if self.session else g.mode):,}'),
                 ('level_label',str(g.level)),('lines',str(g.lines)),('time',clock(g.elapsed))]
        for i,(key,value) in enumerate(stats):
            self.put(oy+9+i*3,ox+2,self.t(key),curses.A_DIM)
            self.put(oy+10+i*3,ox+2,value,curses.A_BOLD|self.color('O' if key == 'score' else 'I'))
        goal = f'{max(0,40-g.lines)}' if g.mode == 'sprint' else clock(120-g.elapsed) if g.mode == 'ultra' else f'{10-g.lines%10}'
        if self.session and self.session.mode=='boss': goal=str(sum(self.session.boss_hp))+' HP'
        self.put(oy+24,ox+2,self.t('goal')+': '+goal,curses.A_DIM)
        self.put(oy+3,ox+46,self.t('next'),curses.A_BOLD)
        for i,kind in enumerate(list(g.queue)[:5]):
            self.preview(kind,oy+5+i*4,ox+47)
        self.center(oy+25,self.banner if self.now < self.banner_until else self.t('help_pause')+' · H: '+self.t('help'),
                    self.color('O')|curses.A_BOLD if self.now < self.banner_until else curses.A_DIM)
        self.center(oy+27,self.t('showcase_hint') if self.screen == 'showcase' else self.t('sound_status',value=self.audio_label()),curses.A_DIM)
        if self.session and self.session.mode=='boss': self.draw_boss(oy)
        if self.screen in ('autoplay','replay'):
            self.center(oy+27,self.t('autoplay_hint') if self.screen=='autoplay' else self.t('replay_hint',speed=self.replay_speed),self.color('T'))
        if self.effects.fever_until>self.now:
            self.center(oy+26,self.t('fever'),self.color('L')|curses.A_BOLD)
        if self.screen == 'ready':
            number = max(1,3-int(self.ready_elapsed))
            self.panel(self.t('ready'),['']*6)
            for i,row in enumerate(NUMBERS[number]):
                self.center(h//2-2+i,row.replace('#','██' if not self.settings['ascii'] else '##').replace(' ','  '),self.color('O')|curses.A_BOLD)
        elif self.screen == 'paused':
            self.panel(self.t('paused'),[self.t(k) for k in ('resume','restart','help','main_menu','quit')],self.pause_selection)
        elif self.screen == 'result' and self.now-self.result_since > .65:
            lines = [f'{self.t("score")}: {g.score:,}',f'{self.t("lines")}: {g.lines}',
                     f'{self.t("time")}: {clock(g.elapsed)}',self.t('new_best') if self.new_record else '',
                     self.t('result_hint')]
            self.panel(self.t('won' if g.state == 'won' else 'gameover'),lines)

    def best_score(self, mode):
        return max((r['score'] for r in self.store.records[mode]),default=0)

    def draw(self):
        self.win.erase()
        h,w = self.win.getmaxyx()
        self._canvas=[[(' ',self.art_attr(0) if self.cathedral_enabled else 0)]*(w-1) for _ in range(h)]
        if h < 28 or w < 64:
            self.center(max(0,h//2-1),self.t('resize'),curses.A_BOLD)
            self.center(min(h-1,h//2+1),self.t('resize_hint'))
        else:
            self._background()
            underlying = self.confirm_return if self.screen == 'confirm' else self.help_return if self.screen == 'help' else self.screen
            if underlying in ('playing','paused','ready','result','showcase','replay','autoplay') and self.game:
                self.draw_game()
            elif underlying in ('hub','gallery','profiles','replays','analysis'):
                self.draw_expansion()
            elif underlying == 'settings':
                self.draw_settings()
            elif underlying == 'records':
                self.draw_records()
            else:
                self.draw_menu()
            if self.screen == 'help':
                self.panel(self.t('help'),[self.t(k) for k in ('help_move','help_soft','help_hard','help_rotate','help_ccw',
                           'help_hold','help_pause','help_sound','help_restart','help_rule','help_score','help_modes','help_fx')],footer=self.t('help_close'))
            elif self.screen == 'confirm':
                self.panel(self.t('confirm_'+self.confirm_action),[self.t('confirm_hint')])
            if self.store.warning and self.screen != 'menu':
                self.center(h-1,self.t(self.store.warning),self.color('Z'))
            elif self.notice:
                self.center(h-1,self.t(self.notice),self.color('Z'))
        canvas=self._canvas; self._canvas=None
        for y,row in enumerate(canvas):
            x=0
            while x<len(row):
                start=x; attr=row[x][1]; chars=[]
                while x<len(row) and row[x][1]==attr:
                    chars.append(row[x][0]); x+=1
                text=''.join(chars)
                if text:
                    try: self.win.addstr(y,start,text,attr)
                    except curses.error: pass
        self.win.noutrefresh()
        curses.doupdate()

    def start(self, mode=None,record=True):
        mode=mode or (self.session.mode if self.session else MODES[min(2,self.selection)])
        self.session=Session(self.seed,mode,self.start_level,record=record)
        self.game=self.session.game
        self.accumulator=0.
        self.last_replay=None
        self.notice=''
        self.game.state = 'paused'
        self.game.events.clear()
        self.screen = 'ready'
        self.ready_elapsed = 0.
        self.flash_until = self.banner_until = 0.
        self.particles.clear(); self.trails.clear()
        self.effects = Effects()
        self.new_record = False
        self.audio.play('hold')

    def show_help(self):
        self.help_return = self.screen
        self.screen = 'help'

    def confirm(self, action):
        self.confirm_return = self.screen
        self.confirm_action = action
        self.screen = 'confirm'

    def handle(self, key):
        h,w = self.win.getmaxyx()
        if h < 28 or w < 64:
            if key in ('q','Q'):
                self.running = False
            return
        if isinstance(key,str):
            key = key.lower()
        enter = key in ('\n','\r',curses.KEY_ENTER)
        escape = key == '\x1b'
        up = key in (curses.KEY_UP,'w')
        down = key in (curses.KEY_DOWN,'s')
        left = key in (curses.KEY_LEFT,'a')
        right = key in (curses.KEY_RIGHT,'d')
        if key == 'f':
            self.fx_enabled = not self.fx_enabled
            self.effects = Effects()
            self.effects.configure(self.settings)
            if self.screen=='gallery' and self.fx_enabled: self.gallery_trigger()
            return
        if self.screen == 'showcase':
            if escape or key == 'v':
                self.screen = 'menu'; self.game = None; self.effects = Effects()
            elif key == 'q':
                self.running = False
            return
        if self.expansion_handle(key,enter,escape,up,down,left,right): return
        if key == 'm':
            self.settings['sound'] = not self.settings['sound']; self.store.save(); return
        if key == 'b':
            self.settings['music'] = not self.settings['music']; self.store.save(); return
        if self.screen == 'confirm':
            if enter or key == 'y':
                if self.confirm_action == 'quit':
                    self.running = False
                elif self.confirm_action == 'restart':
                    self.start()
                else:
                    self.screen = 'menu'; self.game = None
            elif escape or key == 'n':
                self.screen = self.confirm_return
            return
        if self.screen == 'help':
            if enter or escape or key in ('h','?','q'):
                self.screen = self.help_return
            return
        if self.screen == 'settings':
            keys = ['language','sound','music','volume','ascii','color','profiles']
            if up or down:
                self.setting_selection = (self.setting_selection+(-1 if up else 1)) % len(keys)
            elif left or right or enter:
                name = keys[self.setting_selection]
                if name == 'profiles':
                    self.profile_return='settings'; self.screen='profiles'; return
                if name == 'language':
                    self.settings[name] = 'en' if self.settings[name] == 'ko' else 'ko'
                elif name == 'volume':
                    self.settings[name] = round(max(0,min(1,self.settings[name]+(-.1 if left else .1))),1)
                else:
                    self.settings[name] = not self.settings[name]
                self.store.save()
                self.audio.play('rotate')
            elif escape or key == 'q':
                self.screen = 'menu'
            return
        if self.screen == 'records':
            if left or right:
                self.mode_index = (self.mode_index+(-1 if left else 1)) % len(MODES)
            elif escape or key == 'q':
                self.screen = 'menu'
            return
        if self.screen == 'menu':
            if key == 'e': self.hub_selection=0; self.screen='hub'; return
            if key == 'v':
                self.start('marathon',record=False); self.screen = 'showcase'
                self.showcase_step = 0; self.showcase_next = self.now
                return
            if up or down:
                self.selection = (self.selection+(-1 if up else 1)) % 7
                self.audio.play('move')
            elif left or right:
                self.start_level = max(1,min(15,self.start_level+(-1 if left else 1)))
            elif enter:
                if self.selection < 3:
                    self.start(MODES[self.selection])
                elif self.selection == 3:
                    self.screen = 'settings'
                elif self.selection == 4:
                    self.screen = 'records'
                elif self.selection==5:
                    self.running = False
                else: self.hub_selection=0; self.screen='hub'
            elif key in ('h','?'):
                self.show_help()
            elif key == 'q' or escape:
                self.running = False
            return
        if self.screen == 'result':
            if key=='a': self.analysis_return='result'; self.screen='analysis'; return
            if enter or key == 'r':
                self.start()
            elif escape:
                self.screen = 'menu'; self.game = None
            elif key == 'q':
                self.running = False
            return
        if self.screen == 'paused':
            if escape or key == 'p':
                self.screen = 'playing'
            elif up or down:
                self.pause_selection = (self.pause_selection+(-1 if up else 1)) % 5
            elif enter:
                action = ('resume','restart','help','menu','quit')[self.pause_selection]
                if action == 'resume': self.screen = 'playing'
                elif action == 'help': self.show_help()
                else: self.confirm(action)
            elif key == 'q': self.confirm('quit')
            elif key == 'r': self.confirm('restart')
            elif key in ('h','?'): self.show_help()
            return
        if key == 'q': self.confirm('quit'); return
        if key == 'r': self.confirm('restart'); return
        if key in ('h','?'): self.show_help(); return
        if self.screen == 'ready':
            if escape or key == 'p':
                self.screen = 'menu'; self.game = None
            return
        if escape or key == 'p':
            self.screen = 'paused'; self.pause_selection = 0; return
        command='left' if left else 'right' if right else 'soft' if down else 'cw' if key in (curses.KEY_UP,'x','w') else 'ccw' if key=='z' else 'hold' if key=='c' else 'drop' if key==' ' else None
        if command: self.session.command(command)

    def process_events(self):
        g = self.game
        if not g:
            return
        if self.session and self.screen not in ('showcase','gallery'):
            self.session.observe()
        self.effects.configure(self.settings)
        self.effects.danger=any(any(row) for row in g.board[HIDDEN:HIDDEN+6])
        peak=any(e.name in ('clear','win','gameover','boss_break') for e in g.events)
        for event in g.events:
            data = event.data
            if self.fx_enabled and not (peak and event.name in ('drop','lock','rotate','hold')):
                fx_data=dict(data)
                if event.name in ('win','gameover'): fx_data['cells']=tuple((x,y) for y,row in enumerate(g.board) for x,k in enumerate(row) if k)
                self.effects.trigger(event.name,fx_data,self.now)
            if event.name in ('move','rotate','hold','drop','lock','level','gameover','win'):
                self.audio.play(event.name)
            if event.name == 'drop':
                self.trails.append((self.now,data['cells'],data['distance']))
            elif event.name == 'clear':
                self.audio.play('tetris' if data['count'] == 4 or data['spin'] else 'clear')
                self.flash_rows = data['rows']; self.flash_until = self.now+.24
                keys = ('','single','double','triple','tetris')
                text = self.t('tspin') if data['spin'] else self.t(keys[data['count']])
                if data['combo'] > 0:
                    text += ' · '+self.t('combo',value=data['combo'])
                if data['perfect']:
                    text = self.t('perfect')
                self.banner = text+f' +{data["points"]:,}'
                self.banner_until = self.now+1.6
                for row in data['rows']:
                    for _ in range(6):
                        self.particles.append((self.now,self.fx_rng.randrange(10),row,
                                               self.fx_rng.uniform(-8,8),self.fx_rng.uniform(-6,0)))
            elif event.name == 'level':
                self.banner = self.t('level',value=data['level']); self.banner_until = self.now+1.6
        g.events.clear()
        self.effects.update(self.now)
        self.trails = [t for t in self.trails if self.now-t[0] < .18]
        self.particles = [p for p in self.particles if self.now-p[0] < .5][-600:]
        if g.state in ('won','over') and self.screen not in ('result','showcase','replay','autoplay','analysis'):
            mode=self.session.mode if self.session else g.mode
            if self.session.actions and self.session.actions[-1][0]>=self.session.tick: self.session.step()
            old = self.store.records[mode][:]
            row = dict(score=g.score,lines=g.lines,level=g.level,seconds=round(g.elapsed,3),
                       completed=g.state == 'won',date=datetime.now().isoformat(timespec='seconds'))
            self.store.record(mode,row)
            if self.session.recording:
                self.last_replay=self.session.replay()
                if not self.replays.save(self.last_replay): self.notice='replay_error'
            elif self.session.warning: self.notice=self.session.warning
            self.new_record = bool(self.store.records[mode] and self.store.records[mode][0] == row
                                   and (not old or old[0] != row))
            self.screen = 'result'; self.result_since = self.now

    def showcase(self):
        if self.now < self.showcase_next:
            return
        self.showcase_next = self.now+1.6
        step=self.showcase_step%9
        self.showcase_step+=1
        g=self.game
        g.board=[[None]*10 for _ in range(22)]
        for y in range(17,22):
            for x in range(10):
                if (x+y+step)%4:
                    g.board[y][x]='IOTSZJL'[(x+y)%7]
        if step==0:
            g.emit('drop',cells=((4,2),(4,3),(4,4),(4,5)),distance=15)
            self.banner=self.t('fx_impact')
        elif step in (1,2,3,4,5):
            count=4 if step in (2,5) else 2 if step==3 else 1
            g.emit('clear',rows=list(range(22-count,22)),count=count,spin=step==3,
                   combo=4 if step==4 else 0,b2b=step==2,perfect=step==5,points=800*step)
        else:
            name=('level','gameover','win')[step-6]
            g.emit(name,level=8)
            self.banner=self.t({'level':'level','gameover':'gameover','win':'won'}[name],value=8)
        self.banner_until=self.now+1.6

    def tick(self, dt):
        h,w = self.win.getmaxyx()
        playable = h >= 28 and w >= 64
        if self.screen == 'showcase' and playable:
            self.showcase()
        if self.screen == 'ready' and playable:
            self.ready_elapsed += dt
            if self.ready_elapsed >= 3:
                self.screen = 'playing'; self.game.state = 'playing'
                self.banner = self.t('go'); self.banner_until = self.now+1.
                self.audio.play('level')
                if self.fx_enabled: self.effects.trigger('go',{},self.now)
        if self.screen=='gallery' and playable:
            if self.gallery_auto and self.now>=self.gallery_next:
                self.gallery_index=(self.gallery_index+1)%len(CATALOG); self.gallery_next=self.now+3; self.gallery_trigger()
            self.effects.update(self.now)
        if self.game and self.session:
            active=playable and (self.screen=='playing' or self.screen=='autoplay' and not getattr(self,'auto_paused',False))
            if self.screen=='replay':
                if playable and not self.replay_paused:
                    speed=self.replay_speed*(.5 if self.director and self.now<self.slow_until else 1)
                    self.accumulator+=min(dt,.1)*speed
                    while self.accumulator>=STEP and not self.player.finished:
                        self.player.step(); self.accumulator-=STEP
                        self.session=self.player.session; self.game=self.session.game
                        if self.director:
                            for event in self.game.events:
                                if event.name=='clear' and (event.data['count']==4 or event.data['spin'] or event.data['perfect'] or event.data['combo']>=4):
                                    self.slow_until=self.now+1
                                    rows=event.data['rows']; focus=sum(rows)/len(rows)-2 if rows else 10
                                    self.effects.action('focus',self.now,'I',((10,focus),))
                    if self.player.warning: self.notice=self.player.warning
            elif active:
                if self.game.state not in ('won','over'): self.game.state='playing'
                self.accumulator+=min(dt,.1)
                if self.screen=='autoplay' and self.game.state=='playing':
                    command=self.bot.next(self.game)
                    if command: self.session.command(command)
                while self.accumulator>=STEP:
                    self.session.step(); self.accumulator-=STEP
                if self.screen=='autoplay' and self.game.state in ('won','over'):
                    if not self.auto_restart: self.auto_restart=self.now+1.5
                    elif self.now>=self.auto_restart:
                        self.start('marathon',record=False); self.screen='autoplay'; self.game.state='playing'
                        self.bot=type(self.bot)(); self.auto_restart=0.
            elif self.screen!='analysis' and self.game.state not in ('won','over'):
                self.game.state='paused'; self.accumulator=0.
        self.process_events()
        if self.session and self.session.warning:
            self.notice=self.session.warning
        music=playable and self.screen in ('playing','autoplay','showcase','gallery','replay') and not (self.screen=='replay' and self.replay_paused or self.screen=='autoplay' and getattr(self,'auto_paused',False))
        self.audio.set_music(music)
        if hasattr(self.audio,'set_intensity'):
            self.audio.set_intensity(3 if self.effects.fever_until>self.now else min(3,self.effects.combo//2))
        try:
            self.audio.bells.get_nowait()
            if self.settings['sound'] and self.settings['volume'] > 0:
                curses.beep()
        except (queue.Empty,curses.error):
            pass

    def run(self):
        last = time.monotonic()
        try:
            while self.running:
                frame_start = time.monotonic()
                self.now = frame_start
                dt = min(.1,frame_start-last)
                last = frame_start
                # 입력 큐를 제한해 키 반복 폭주도 렌더링/시간 진행을 굶기지 않게 한다.
                for _ in range(32):
                    try:
                        key = self.win.get_wch()
                    except curses.error:
                        break
                    if key != curses.KEY_RESIZE:
                        self.handle(key)
                self.tick(dt)
                self.draw()
                cost=time.monotonic()-frame_start
                self.effects.quality=max(.4,self.effects.quality-.05) if cost>1/60 else min(1.,self.effects.quality+.005)
                time.sleep(max(0,1/60-(time.monotonic()-frame_start)))
        finally:
            self.audio.set_music(False)
            self.store.save()
