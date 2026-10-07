"""검증된 리플레이 파일과 결정적 재생. 원본 데이터는 재생 중 변경하지 않는다."""
from copy import deepcopy
from datetime import datetime
import json
import re
from pathlib import Path
import tempfile
from .session import Session,COMMANDS

LIMIT=2*1024*1024
OWN_NAME=re.compile(r'replay-[0-9]{8}-[0-9]{6}-[0-9]{6}\.json\Z')


def validate(data):
    if not isinstance(data,dict) or data.get('version')!=1 or data.get('rules')!=1:
        raise ValueError('unsupported replay')
    if type(data.get('seed')) is not int or not -(2**64)<=data['seed']<=2**64:
        raise ValueError('invalid seed')
    if data.get('mode') not in ('marathon','sprint','ultra','boss'):
        raise ValueError('invalid mode')
    if type(data.get('level')) is not int or not 1<=data['level']<=15:
        raise ValueError('invalid level')
    end=data.get('end_tick')
    if type(end) is not int or not 0<=end<=432000: raise ValueError('invalid duration')
    actions=data.get('actions')
    if not isinstance(actions,list) or len(actions)>100000: raise ValueError('invalid actions')
    previous=-1
    for entry in actions:
        if (not isinstance(entry,list) or len(entry)!=2 or type(entry[0]) is not int
            or not previous<=entry[0]<end or entry[1] not in COMMANDS):
            raise ValueError('invalid action')
        previous=entry[0]
    checksum=data.get('checksum')
    if not isinstance(checksum,str) or len(checksum)!=64 or any(c not in '0123456789abcdef' for c in checksum):
        raise ValueError('invalid checksum')
    # 분석 정보는 검증된 코어로 재생하면서 재구축한다. 외부 파일의 보조 필드를 신뢰하지 않는다.
    return {key:deepcopy(data[key]) for key in ('version','rules','seed','mode','level','actions','end_tick','checksum')}


class ReplayStore:
    def __init__(self,directory):
        self.root=Path(directory).resolve()
        self.directory=self.root/'replays'
        self.warning=''

    def _path(self,name):
        if not isinstance(name,str) or not OWN_NAME.fullmatch(name):
            raise ValueError('invalid replay filename')
        path=self.directory/name
        if not path.resolve().is_relative_to(self.root) or path.is_symlink():
            raise ValueError('unsafe replay path')
        return path

    def list(self):
        try:
            if not self.directory.resolve().is_relative_to(self.root): raise ValueError('unsafe directory')
            return sorted((p.name for p in self.directory.glob('replay-*.json') if OWN_NAME.fullmatch(p.name) and not p.is_symlink()),reverse=True)[:20]
        except (OSError,ValueError): self.warning='replay_error'; return []

    def save(self,data):
        temporary=None
        try:
            validate(data)
            text=json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)
            if len(text.encode())>LIMIT: raise ValueError('replay too large')
            name='replay-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json'
            target=self._path(name)
            self.directory.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=self.directory,suffix='.tmp',delete=False) as f:
                temporary=Path(f.name); f.write(text)
            temporary.replace(target); temporary=None
            files=sorted((p for p in self.directory.glob('replay-*.json') if OWN_NAME.fullmatch(p.name) and not p.is_symlink()),reverse=True)
            for path in files[20:]:
                self._path(path.name).unlink()
            self.warning=''
            return name
        except (OSError,ValueError,TypeError): self.warning='replay_error'; return None
        finally:
            if temporary:
                try: temporary.unlink(missing_ok=True)
                except OSError: pass

    def load(self,name):
        path=self._path(name)
        if path.stat().st_size>LIMIT: raise ValueError('replay too large')
        return validate(json.loads(path.read_text(encoding='utf-8')))


class Player:
    def __init__(self,data):
        self.data=validate(data)
        self.session=Session(data['seed'],data['mode'],data['level'],record=False)
        self.actions=self.data['actions']
        self.index=0
        self.verified=False
        self.warning=''
        self.checkpoints={0:(deepcopy(self.session),0)}

    @property
    def finished(self): return self.session.tick>=self.data['end_tick']

    def step(self):
        if self.finished: self._verify(); return
        tick=self.session.tick
        while self.index<len(self.actions) and self.actions[self.index][0]==tick:
            self.session.command(self.actions[self.index][1]); self.index+=1
        self.session.step()
        if self.session.tick%300==0:
            snapshot=deepcopy(self.session); snapshot.game.events.clear(); snapshot._processed=[]
            self.checkpoints[self.session.tick]=(snapshot,self.index)
            if len(self.checkpoints)>24:
                del self.checkpoints[min(t for t in self.checkpoints if t)]
        if self.finished: self._verify()

    def _verify(self):
        self.verified=self.session.checksum()==self.data['checksum']
        if not self.verified: self.warning='replay_mismatch'

    def seek(self,tick):
        tick=max(0,min(self.data['end_tick'],int(tick)))
        start=max(t for t in self.checkpoints if t<=tick)
        snapshot,index=self.checkpoints[start]
        self.session=deepcopy(snapshot); self.index=index
        self.verified=False; self.warning=''
        while self.session.tick<tick:
            self.step(); self.session.game.events.clear(); self.session._processed=[]
        if self.finished: self._verify()
