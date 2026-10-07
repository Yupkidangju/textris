"""검증된 설정과 모드별 상위 기록의 원자 저장."""
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile

DEFAULTS = dict(language='en',sound=True,music=True,volume=.5,ascii=False,color=True,
                theme='cathedral',fx_intensity=.75,fx_speed=1.,fx_density=.75,
                shake=True,flash=True,braille=True)
MODES = ('marathon','sprint','ultra','boss')


class Store:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.path = self.directory/'records.json'
        self.settings = deepcopy(DEFAULTS)
        self.records = {m: [] for m in MODES}
        self.warning = ''
        self.read_only = False

    @staticmethod
    def valid_record(r):
        return (isinstance(r,dict)
                and all(type(r.get(k)) is int and 0 <= r[k] <= 10**12 for k in ('score','lines','level'))
                and type(r.get('seconds')) in (int,float) and 0 <= r['seconds'] <= 10**12 and math.isfinite(r['seconds'])
                and type(r.get('completed')) is bool
                and isinstance(r.get('date'),str) and len(r['date']) <= 32)

    def load(self):
        try:
            if not self.path.exists():
                return
            if self.path.is_symlink() or self.path.stat().st_size > 1024*1024:
                raise ValueError('unsafe or oversized save')
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data,dict) or data.get('version') != 1:
                raise ValueError('unsupported save version')
            settings = data.get('settings',{})
            if isinstance(settings,dict):
                for key, default in DEFAULTS.items():
                    value = settings.get(key, default)
                    if key == 'language':
                        value='en'
                        valid = True
                    elif key == 'theme':
                        valid = isinstance(value,str) and value in ('cathedral','cyberpunk','space','fire','crt','mono')
                    elif key in ('fx_intensity','fx_density','fx_speed'):
                        valid = type(value) in (int,float) and math.isfinite(value) and (.5 if key=='fx_speed' else .25) <= value <= (2 if key=='fx_speed' else 1)
                    elif key == 'volume':
                        valid = type(value) in (int,float) and 0 <= value <= 1 and math.isfinite(value)
                    else:
                        valid = type(value) is bool
                    if valid:
                        self.settings[key] = value
            records = data.get('records',{})
            if isinstance(records,dict):
                for mode in MODES:
                    rows = records.get(mode,[])
                    if isinstance(rows,list):
                        self.records[mode] = [r for r in rows if self.valid_record(r)]
                        self._sort(mode)
        except (OSError,ValueError,TypeError):
            self.warning = 'save_read'
            self.read_only = True

    def _sort(self, mode):
        if mode in ('sprint','boss'):
            self.records[mode].sort(key=lambda r: (not r['completed'],r['seconds'] if r['completed'] else -r['lines'],-r['score']))
        else:
            self.records[mode].sort(key=lambda r: (-r['score'],-r['lines'],r['seconds']))
        self.records[mode] = self.records[mode][:10]

    def record(self, mode, row):
        if mode not in MODES or not self.valid_record(row):
            raise ValueError('invalid record')
        self.records[mode].append(dict(row))
        self._sort(mode)
        self.save()

    def save(self):
        if self.read_only:
            return False
        temp_path = None
        try:
            self.directory.mkdir(parents=True,exist_ok=True)
            data = dict(version=1,settings=self.settings,records=self.records)
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.tmp',dir=self.directory,delete=False) as f:
                temp_path = Path(f.name)
                json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
                f.write('\n')
            temp_path.replace(self.path)
            self.warning = ''
            return True
        except (OSError,ValueError):
            self.warning = 'save_write'
            return False
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    self.warning = 'save_write'
