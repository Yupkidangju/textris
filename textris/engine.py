"""화면과 I/O에 의존하지 않는 테트리스 규칙과 시간 진행."""
from collections import deque
from dataclasses import dataclass, field
import math
import random

WIDTH, HEIGHT, HIDDEN = 10, 22, 2
KINDS = 'IOTSZJL'
BASE = {
    'I': ((0,1),(1,1),(2,1),(3,1)),
    'O': ((1,0),(2,0),(1,1),(2,1)),
    'T': ((1,0),(0,1),(1,1),(2,1)),
    'S': ((1,0),(2,0),(0,1),(1,1)),
    'Z': ((0,0),(1,0),(1,1),(2,1)),
    'J': ((0,0),(0,1),(1,1),(2,1)),
    'L': ((2,0),(0,1),(1,1),(2,1)),
}
# SRS 표의 y-up 값을 보드의 y-down 좌표로 변환한다.
JLSTZ_KICKS = {
    (0,1): ((0,0),(-1,0),(-1,1),(0,-2),(-1,-2)),
    (1,0): ((0,0),(1,0),(1,-1),(0,2),(1,2)),
    (1,2): ((0,0),(1,0),(1,-1),(0,2),(1,2)),
    (2,1): ((0,0),(-1,0),(-1,1),(0,-2),(-1,-2)),
    (2,3): ((0,0),(1,0),(1,1),(0,-2),(1,-2)),
    (3,2): ((0,0),(-1,0),(-1,-1),(0,2),(-1,2)),
    (3,0): ((0,0),(-1,0),(-1,-1),(0,2),(-1,2)),
    (0,3): ((0,0),(1,0),(1,1),(0,-2),(1,-2)),
}
I_KICKS = {
    (0,1): ((0,0),(-2,0),(1,0),(-2,-1),(1,2)),
    (1,0): ((0,0),(2,0),(-1,0),(2,1),(-1,-2)),
    (1,2): ((0,0),(-1,0),(2,0),(-1,2),(2,-1)),
    (2,1): ((0,0),(1,0),(-2,0),(1,-2),(-2,1)),
    (2,3): ((0,0),(2,0),(-1,0),(2,1),(-1,-2)),
    (3,2): ((0,0),(-2,0),(1,0),(-2,-1),(1,2)),
    (3,0): ((0,0),(1,0),(-2,0),(1,-2),(-2,1)),
    (0,3): ((0,0),(-1,0),(2,0),(-1,2),(2,-1)),
}


@dataclass(frozen=True)
class Piece:
    kind: str
    rotation: int = 0
    x: int = 3
    y: int = 0


@dataclass
class Event:
    name: str
    data: dict = field(default_factory=dict)


def cells(piece: Piece) -> tuple[tuple[int, int], ...]:
    points = BASE[piece.kind]
    if piece.kind != 'O':
        edge = 3 if piece.kind == 'I' else 2
        for _ in range(piece.rotation % 4):
            points = tuple((edge-y, x) for x, y in points)
    return tuple((piece.x+x, piece.y+y) for x, y in points)


class Game:
    def __init__(self, seed=None, mode='marathon', start_level=1):
        if mode not in ('marathon', 'sprint', 'ultra'):
            raise ValueError('invalid mode')
        if not isinstance(start_level, int) or not 1 <= start_level <= 15:
            raise ValueError('start_level must be 1..15')
        self.rng = random.Random(seed)
        self.mode, self.start_level = mode, start_level
        self.board = [[None] * WIDTH for _ in range(HEIGHT)]
        self.queue = deque()
        self.events = []
        self.held = None
        self.hold_used = False
        self.score = self.lines = 0
        self.level = start_level
        self.elapsed = self.gravity_elapsed = self.lock_elapsed = 0.0
        self.lock_resets = 0
        self.combo = -1
        self.b2b = False
        self.last_rotate = False
        self.state = 'playing'
        self.active = Piece('T')
        self._spawn()

    @property
    def gravity(self):
        return max(.05, .8 * .8 ** (self.level - 1))

    def emit(self, name, **data):
        self.events.append(Event(name, data))

    def _fill_queue(self):
        while len(self.queue) < 6:
            bag = list(KINDS)
            self.rng.shuffle(bag)
            self.queue.extend(bag)

    def fits(self, piece):
        return all(0 <= x < WIDTH and 0 <= y < HEIGHT and self.board[y][x] is None
                   for x, y in cells(piece))

    def _spawn(self, kind=None):
        self._fill_queue()
        self.active = Piece(kind or self.queue.popleft())
        self._fill_queue()
        self.gravity_elapsed = self.lock_elapsed = 0.0
        self.lock_resets = 0
        self.last_rotate = False
        if not self.fits(self.active):
            self.state = 'over'
            self.emit('gameover')
        else:
            self.emit('spawn', kind=self.active.kind)

    def grounded(self):
        p = self.active
        return not self.fits(Piece(p.kind, p.rotation, p.x, p.y+1))

    def _reset_lock(self, was_grounded):
        if was_grounded and self.lock_resets < 15:
            self.lock_elapsed = 0.0
            self.lock_resets += 1

    def move(self, dx, dy, soft=False):
        if self.state != 'playing':
            return False
        p = self.active
        moved = Piece(p.kind, p.rotation, p.x+dx, p.y+dy)
        if not self.fits(moved):
            return False
        was_grounded = self.grounded()
        self.active = moved
        if dx or soft:
            self.last_rotate = False
        if dx:
            self._reset_lock(was_grounded)
            self.emit('move',kind=self.active.kind,cells=cells(self.active))
        if soft:
            self.score += max(0, dy)
            self.gravity_elapsed = 0.0
        return True

    def rotate(self, direction):
        if self.state != 'playing' or direction not in (-1, 1):
            return False
        p = self.active
        if p.kind == 'O':
            self._reset_lock(self.grounded())
            self.emit('rotate',kind=self.active.kind,cells=cells(self.active))
            return True
        target = (p.rotation+direction) % 4
        table = I_KICKS if p.kind == 'I' else JLSTZ_KICKS
        was_grounded = self.grounded()
        for dx, dy in table[(p.rotation,target)]:
            rotated = Piece(p.kind,target,p.x+dx,p.y-dy)
            if self.fits(rotated):
                self.active = rotated
                self.last_rotate = True
                self._reset_lock(was_grounded)
                self.emit('rotate',kind=self.active.kind,cells=cells(self.active))
                return True
        return False

    def hold(self):
        if self.state != 'playing' or self.hold_used:
            return False
        previous, self.held = self.held, self.active.kind
        self._spawn(previous)
        self.hold_used = True
        self.emit('hold',kind=self.active.kind,cells=cells(self.active))
        return True

    def ghost_y(self):
        p = self.active
        y = p.y
        while self.fits(Piece(p.kind,p.rotation,p.x,y+1)):
            y += 1
        return y

    def hard_drop(self):
        if self.state != 'playing':
            return
        p = self.active
        y = self.ghost_y()
        self.score += 2*(y-p.y)
        if y != p.y:
            self.last_rotate = False
        self.emit('drop', cells=cells(p), distance=y-p.y,kind=p.kind)
        self.active = Piece(p.kind,p.rotation,p.x,y)
        self.lock()

    def _tspin(self):
        if self.active.kind != 'T' or not self.last_rotate:
            return False
        cx, cy = self.active.x+1, self.active.y+1
        corners = [(cx-1,cy-1),(cx+1,cy-1),(cx-1,cy+1),(cx+1,cy+1)]
        return sum(x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT
                   or self.board[y][x] is not None for x,y in corners) >= 3

    def lock(self):
        if self.state != 'playing':
            return
        spin = self._tspin()
        for x,y in cells(self.active):
            self.board[y][x] = self.active.kind
        self.emit('lock', cells=cells(self.active),kind=self.active.kind)
        rows = [i for i,r in enumerate(self.board) if all(r)]
        removed=[(x,y,kind) for y in rows for x,kind in enumerate(self.board[y])]
        n = len(rows)
        level = self.level
        points = (400,800,1200,1600)[n] if spin else (0,100,300,500,800)[n]
        difficult = n > 0 and (n == 4 or spin)
        if difficult and self.b2b:
            points = points * 3 // 2
        if n:
            self.combo += 1
            points += 50 * self.combo
            if difficult:
                self.b2b = True
            else:
                self.b2b = False
            self.board = [[None]*WIDTH for _ in rows] + [r for i,r in enumerate(self.board) if i not in rows]
            perfect = not any(any(r) for r in self.board)
            if perfect:
                points += 3500
            self.lines += n
            self.emit('clear', rows=rows, count=n, spin=spin, combo=self.combo,
                      b2b=difficult and self.b2b, perfect=perfect, points=points*level,cleared_cells=removed)
        else:
            self.combo = -1
            if spin:
                self.emit('clear', rows=[], count=0, spin=True, combo=-1,
                          b2b=False, perfect=False, points=points*level)
        self.score += points * level
        new_level = self.start_level + self.lines//10
        if new_level != self.level:
            self.level = new_level
            self.emit('level', level=new_level)
        if self.mode == 'sprint' and self.lines >= 40:
            self.state = 'won'; self.emit('win'); return
        if any(any(r) for r in self.board[:HIDDEN]):
            self.state = 'over'; self.emit('gameover'); return
        self.hold_used = False
        self._spawn()

    def update(self, dt):
        if not math.isfinite(dt) or dt < 0:
            raise ValueError('dt must be finite and nonnegative')
        if self.state != 'playing':
            return
        self.elapsed += dt
        if self.mode == 'ultra' and self.elapsed >= 120:
            self.elapsed = 120
            self.state = 'won'; self.emit('win'); return
        # 작은 시간 단위로 진행해 긴 프레임도 착지 이전 시간을 lock delay로 세지 않는다.
        remaining = dt
        while remaining > 0 and self.state == 'playing':
            step = min(remaining, .02)
            remaining -= step
            if self.grounded():
                self.lock_elapsed += step
                if self.lock_elapsed >= .5:
                    self.lock()
            else:
                self.lock_elapsed = 0.0
                self.gravity_elapsed += step
                if self.gravity_elapsed >= self.gravity:
                    self.gravity_elapsed -= self.gravity
                    self.move(0,1)
