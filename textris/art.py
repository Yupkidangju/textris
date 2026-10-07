"""문자 아트의 좌표·깊이·보호 영역과 한정된 터미널 팔레트."""
from dataclasses import dataclass
import curses
import math
from functools import lru_cache

# 전경/배경을 미리 할당하므로 매 프레임 색상쌍을 만들지 않는다.
COLORS=(17,18,24,30,44,123,60,99,94,180,231,203,24,60,30,247,87,221,177,120,210,111,215)
BACKS=(16,)*12+(17,17,17,16)+(16,)*7
BASIC=(4,4,4,6,6,7,4,5,3,3,7,1,4,5,6,7,6,3,5,2,1,4,7)
THEME_COLORS={
    'cathedral': COLORS,
    'cyberpunk': (17,18,54,33,51,195,91,201,89,213,231,203,24,54,33,247)+COLORS[16:],
    'space': (17,17,18,25,75,153,60,105,94,223,231,203,18,60,25,247)+COLORS[16:],
    'fire': (52,52,88,160,208,229,94,202,130,220,231,196,88,94,160,247)+COLORS[16:],
    'crt': (22,22,28,34,82,157,29,46,58,154,231,203,22,28,34,247)+COLORS[16:],
    'mono': (233,235,238,244,250,255,240,247,245,255,255,250,235,237,239,250)+(255,)*7,
}

BRAILLE_BITS=((0,1,2,6),(3,4,5,7))


class Palette:
    def __init__(self):
        self.pairs={}
        self.theme='cathedral'
        self.limits=(0,0)

    def setup(self, colors, pairs,theme='cathedral'):
        self.theme=theme;self.limits=(colors,pairs)
        palette=THEME_COLORS[theme]
        self.pairs.clear()
        if colors<8 or pairs<=1:
            return
        # 1..7은 기존 블록/갤러리 색상용이다.
        for style in range(len(COLORS)):
            pair=8+style
            if pair>=pairs:
                pair=(0,5,4,2,6,3,1,7)[BASIC[style]]
                self.pairs[style]=pair if pair<pairs else 1
                continue
            try:
                curses.init_pair(pair,palette[style] if colors>=256 else BASIC[style],
                                 BACKS[style] if colors>=256 else curses.COLOR_BLACK)
                self.pairs[style]=pair
            except curses.error:
                break

    def attr(self, style, color=True):
        attr=curses.A_BOLD if style in (5,9,10) else 0
        if not color:
            return attr | (curses.A_DIM if style in (0,1,2,6,8,15) else 0)
        pair=self.pairs.get(style)
        return attr | (curses.color_pair(pair) if pair is not None else 0)


@dataclass(frozen=True)
class Layout:
    board: tuple
    origin: tuple
    protected: tuple


def game_layout(width, height):
    ox,oy=(width-64)//2,max(0,(height-28)//2)
    bx,by=ox+21,oy+3
    # 흔들리는 프레임도 배경에 묻히지 않도록 1셀 여유를 둔다.
    protected=((bx-1,by-1,24,24),(ox+1,oy+2,19,23),
               (ox+44,oy+2,19,23),(ox,oy,64,2),(ox,oy+25,64,3))
    return Layout((bx,by),(ox,oy),protected)


@dataclass(frozen=True)
class RenderContext:
    width: int
    height: int
    protected: tuple=()
    ascii_mode: bool=False
    braille: bool=True
    quality: float=1.


@dataclass(slots=True)
class Ink:
    glyph: str
    style: int
    depth: float
    mask: int=0


@lru_cache(maxsize=16)
def protected_cells(context):
    return frozenset((xx,yy) for x,y,w,h in context.protected
                     for yy in range(max(0,y),min(context.height,y+h))
                     for xx in range(max(0,x),min(context.width-1,x+w)))


class ArtCanvas:
    def __init__(self, context):
        self.context=context
        self.cells={}
        self.blocked=protected_cells(context)

    def accepts(self,x,y):
        return (0<=x<self.context.width-1 and 0<=y<self.context.height
                and (x,y) not in self.blocked)

    def put(self,x,y,glyph,style=3,depth=0):
        x,y=round(x),round(y)
        if not self.accepts(x,y): return
        old=self.cells.get((x,y))
        if old is None or depth<=old.depth:
            self.cells[x,y]=Ink(glyph,style,depth)

    def dot(self,x,y,style=3,depth=0):
        px,py=math.floor(x*2),math.floor(y*4)
        self._subpixel(px,py,style,depth)

    def _subpixel(self,px,py,style,depth):
        cx,cy=px//2,py//4
        if not self.accepts(cx,cy): return
        if self.context.ascii_mode or not self.context.braille:
            self.put(cx,cy,':' if self.context.ascii_mode else '·',style,depth)
            return
        mask=1<<BRAILLE_BITS[px%2][py%4]
        old=self.cells.get((cx,cy))
        if old is not None:
            if old.mask and old.style==style and abs(old.depth-depth)<.15:
                mask|=old.mask
                if mask==old.mask: return
                self.cells[cx,cy]=Ink(chr(0x2800+mask),style,min(old.depth,depth),mask)
                return
            elif depth>old.depth:
                return
        self.cells[cx,cy]=Ink(chr(0x2800+mask),style,depth,mask)

    def line(self,a,b,style=3,depth=0):
        if (max(a[0],b[0])<0 or min(a[0],b[0])>=self.context.width-1
                or max(a[1],b[1])<0 or min(a[1],b[1])>=self.context.height): return
        # 정수 서브셀에서 한 번씩만 순회해 연결성과 비용을 함께 보장한다.
        x,y=math.floor(a[0]*2),math.floor(a[1]*4)
        endx,endy=math.floor(b[0]*2),math.floor(b[1]*4)
        dx,dy=abs(endx-x),-abs(endy-y)
        sx,sy=1 if x<endx else -1,1 if y<endy else -1
        error=dx+dy
        while True:
            self._subpixel(x,y,style,depth)
            if x==endx and y==endy: break
            twice=error*2
            if twice>=dy: error+=dy; x+=sx
            if twice<=dx: error+=dx; y+=sy

    def curve(self,points,style=3,depth=0):
        previous=None
        for point in points:
            if previous is not None and (abs(point[0]-previous[0])>.5 or abs(point[1]-previous[1])>.25):
                self.line(previous,point,style,depth)
            else:
                self.dot(*point,style,depth)
            previous=point

    def paint(self,app):
        attrs=[app.art_attr(style) for style in range(len(COLORS))]
        target=getattr(app,'_canvas',None)
        if target is not None:
            # 배경은 빈 프레임에 먼저 합성하며 모든 글리프가 폭 1셀임을 보장한다.
            for (x,y),ink in self.cells.items(): target[y][x]=(ink.glyph,attrs[ink.style])
        else:
            for (x,y),ink in self.cells.items(): app.put(y,x,ink.glyph,attrs[ink.style])
