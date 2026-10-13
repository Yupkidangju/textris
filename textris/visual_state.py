"""게임 판정과 독립인 읽기 전용 플레이어 표시 상태."""
from dataclasses import dataclass


@dataclass(frozen=True)
class VisualState:
    player_id: str='p1'
    danger: bool=False
    fever: bool=False
    combo: int=0
    b2b: bool=False
    level: int=1
