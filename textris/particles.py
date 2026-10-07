"""중력·충돌과 마찰을 사용하는 유한 수명 문자 파편."""
from dataclasses import dataclass


@dataclass
class Particle:
    start: float
    x: float
    y: float
    vx: float
    vy: float
    life: float
    kind: str
    shape: int
    last: float

    def advance(self,now):
        remaining=max(0,min(.2,now-self.last)); self.last=now
        while remaining>0:
            dt=min(.02,remaining); remaining-=dt
            self.vy+=26*dt; self.x+=self.vx*dt; self.y+=self.vy*dt
            if self.x<0: self.x=0; self.vx=abs(self.vx)*.55
            if self.x>20: self.x=20; self.vx=-abs(self.vx)*.55
            if self.y>20:
                self.y=20; self.vy=-abs(self.vy)*.45; self.vx*=.7
