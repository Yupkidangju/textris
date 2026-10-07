"""벽 차기를 포함한 도달 가능한 배치를 시간 예산 안에서 탐색한다."""
from collections import deque
from copy import deepcopy
import time
from .engine import Piece,cells


def value(board,clears):
    heights=[]; holes=0
    for x in range(10):
        first=next((y for y in range(22) if board[y][x]),22)
        heights.append(22-first)
        holes+=sum(board[y][x] is None for y in range(first,22))
    return 9*clears*clears-4.5*sum(heights)-7.5*holes-2*sum(abs(a-b) for a,b in zip(heights,heights[1:]))


class Autoplayer:
    def __init__(self):
        self.signature=None; self.search=None; self.path=deque(); self.delay=0

    def _search(self,game):
        best=(-float('inf'),['drop'])
        roots=[(deepcopy(game),[])]
        if not game.hold_used:
            held=deepcopy(game); held.hold(); roots.append((held,['hold']))
        for root,prefix in roots:
            if root.state!='playing': continue
            queue=deque([(root.active,[])])
            visited=set()
            while queue and len(visited)<900:
                piece,path=queue.popleft()
                if piece in visited: continue
                visited.add(piece)
                trial=deepcopy(root); trial.active=piece; trial.events=[]
                trial.hard_drop()
                score=value(trial.board,trial.lines-root.lines)
                if trial.state=='over': score-=10000
                if score>best[0]: best=score,prefix+path+['drop']
                for command in ('left','right','cw','ccw'):
                    trial.state='playing'
                    trial.board=root.board
                    trial.active=piece
                    if command in ('left','right'): changed=trial.move(-1 if command=='left' else 1,0)
                    else: changed=trial.rotate(1 if command=='cw' else -1)
                    if changed and trial.active not in visited: queue.append((trial.active,path+[command]))
                yield None
        yield best[1]

    def next(self,game):
        signature=(id(game),game.active.kind,game.score,game.held,game.hold_used,tuple(tuple(row) for row in game.board))
        if signature!=self.signature:
            self.signature=signature; self.search=self._search(game); self.path.clear()
        if self.search:
            deadline=time.perf_counter()+.004
            while time.perf_counter()<deadline:
                result=next(self.search,None)
                if result is not None:
                    self.path=deque(result); self.search=None; break
            return None
        self.delay+=1
        if self.delay<5 or not self.path: return None
        self.delay=0
        return self.path.popleft()
