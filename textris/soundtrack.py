"""검증된 배포 음원, 독립 셔플백, 파일 I/O 없는 PCM 믹서."""
from array import array
from collections import deque
from hashlib import sha256
import json
import math
from pathlib import Path, PurePosixPath
import random
import re
import tempfile
import threading
from types import MappingProxyType

SAMPLE_RATE = 44100
CHANNELS = 2
CHUNK_FRAMES = 2048
BUFFER_CHUNKS = 8
MAX_VOICES = 6
MAX_ASSET_BYTES = 24 * 1024 * 1024
MAX_CACHE_BYTES = 128 * 1024 * 1024
LIMITER_CEILING = .87
LIMITER_ATTACK_STEP = 1. / (SAMPLE_RATE * .005)
LIMITER_RELEASE = math.exp(-1. / (SAMPLE_RATE * .08))
THEMES = {'cathedral', 'cyberpunk', 'space', 'fire', 'crt', 'mono', 'classic'}


def _number(value, low, high):
    return type(value) in (int, float) and low <= value <= high and math.isfinite(value)


def _relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('unsafe audio asset path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('..', '.') for part in value.split('/')):
        raise ValueError('unsafe audio asset path')
    return path.parts


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


class AssetLibrary:
    """카탈로그는 읽기 전용이며 파일 검증/추출은 오디오 worker에서만 실행한다."""
    def __init__(self, root, directory):
        self.root = root
        self.directory = Path(directory).resolve()
        self.tracks = ()
        self.effects = ()

    def _read_catalog(self, filename, key):
        with self.root.joinpath(filename).open('rb') as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('oversized audio catalog')
        data = json.loads(raw.decode('utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('unsupported audio catalog')
        rows = data.get(key)
        if not isinstance(rows, list) or len(rows) > 128:
            raise ValueError('invalid audio catalog rows')
        seen = set()
        checked = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('invalid audio catalog entry')
            name = row.get('id')
            if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', name) or name in seen:
                raise ValueError('invalid or duplicate audio id')
            seen.add(name)
            _relative(row.get('file'))
            if PurePosixPath(row['file']).suffix.lower() not in ('.ogg', '.wav', '.flac'):
                raise ValueError('unsupported audio asset extension')
            if not re.fullmatch(r'[0-9a-f]{64}', str(row.get('sha256', ''))):
                raise ValueError('invalid audio checksum')
            if not _number(row.get('duration'), .001, 600 if key == 'tracks' else 8):
                raise ValueError('invalid audio duration')
            if key == 'tracks':
                if (not isinstance(row.get('title'), str) or not 1 <= len(row['title']) <= 200
                        or row.get('theme') not in THEMES or not _number(row.get('bpm'), 1, 500)
                        or not re.fullmatch(r'[1-9][0-9]?/(1|2|4|8|16|32)', str(row.get('time_signature')))
                        or not isinstance(row.get('instruments'), list) or len(row['instruments']) != 4
                        or not all(isinstance(item, str) and 1 <= len(item) <= 100 for item in row['instruments'])):
                    raise ValueError('invalid track metadata')
            elif (not _number(row.get('gain'), 0, 1) or type(row.get('priority')) is not int
                  or not 0 <= row['priority'] <= 1000 or not _number(row.get('cooldown'), 0, 60)):
                raise ValueError('invalid effect metadata')
            checked.append(_freeze(row))
        return tuple(checked)

    def load(self):
        # 한 카탈로그의 실패가 다른 버스까지 없애지 않도록 Audio는 개별 오류도 표시한다.
        self.tracks = self._read_catalog('music.json', 'tracks')
        self.effects = self._read_catalog('sfx.json', 'effects')

    def _cache_path(self, filename):
        path = self.directory / 'audio-cache' / filename
        if not path.resolve().is_relative_to(self.directory):
            raise ValueError('audio cache escapes data root')
        return path

    @staticmethod
    def _hash(stream, target=None):
        digest = sha256(); size = 0
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_ASSET_BYTES:
                raise ValueError('oversized audio asset')
            digest.update(chunk)
            if target is not None:
                target.write(chunk)
        return digest.hexdigest()

    def path(self, row):
        parts = _relative(row['file'])
        resource = self.root.joinpath(*parts)
        if isinstance(resource, Path):
            path = resource.resolve()
            if not path.is_relative_to(self.root.resolve()):
                raise ValueError('audio asset escapes resource root')
            with path.open('rb') as stream:
                digest = self._hash(stream)
            if digest != row['sha256']:
                raise ValueError('audio asset checksum mismatch: ' + row['id'])
            return path
        # zipapp는 decoder에 파일 경로가 필요하므로 사용자 데이터 루트에만 추출한다.
        suffix = PurePosixPath(row['file']).suffix.lower()
        path = self._cache_path(row['sha256'] + suffix)
        if path.exists():
            with path.open('rb') as stream:
                if self._hash(stream) == row['sha256']:
                    return path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path(path.name)
        temp_path = None
        try:
            with resource.open('rb') as source, tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as dest:
                temp_path = Path(dest.name)
                digest = self._hash(source, dest)
            if digest != row['sha256']:
                raise ValueError('audio asset checksum mismatch: ' + row['id'])
            self._cache_path(path.name)
            temp_path.replace(path)
            try:
                self._prune_cache(path)
            except (OSError, ValueError):
                # 용량을 확보할 수 없으면 이번 추출만 되돌려 반복 실패로 캐시가 자라지 않는다.
                path.unlink(missing_ok=True)
                raise
            return path
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _prune_cache(self, keep):
        files = []
        for path in keep.parent.iterdir():
            if (path != keep and re.fullmatch(r'[0-9a-f]{64}\.(ogg|wav|flac)', path.name)
                    and path.is_file() and not path.is_symlink()
                    and path.resolve().is_relative_to(self.directory)):
                files.append((path.stat().st_mtime, path, path.stat().st_size))
        total = keep.stat().st_size + sum(item[2] for item in files)
        count = len(files) + 1
        for _, path, size in sorted(files):
            if total <= MAX_CACHE_BYTES and count <= 64:
                break
            try:
                path.unlink(); total -= size; count -= 1
            except OSError:
                continue
        if total > MAX_CACHE_BYTES or count > 64:
            raise ValueError('audio cache capacity exhausted')


class ShuffleBag:
    def __init__(self, ids, rng):
        self.ids = tuple(ids); self.rng = rng; self.bag = []; self.last = None

    def next(self):
        if not self.ids:
            return None
        if not self.bag:
            self.bag = list(self.ids)
            self.rng.shuffle(self.bag)
            if len(self.bag) > 1 and self.bag[-1] == self.last:
                self.bag[0], self.bag[-1] = self.bag[-1], self.bag[0]
        self.last = self.bag.pop()
        return self.last


class BalancedShuffle:
    """독립 RNG로 매 쌍마다 테마/Classic을 한 곡씩 선택한다."""
    def __init__(self, tracks, theme, rng=None):
        self.rng = rng or random.Random()
        self.bags = [ShuffleBag([r['id'] for r in tracks if r['theme'] == theme], self.rng),
                     ShuffleBag([r['id'] for r in tracks if r['theme'] == 'classic'], self.rng)]
        self.categories = []

    def next(self):
        if not self.categories:
            self.categories = [index for index, bag in enumerate(self.bags) if bag.ids]
            self.rng.shuffle(self.categories)
        return self.bags[self.categories.pop()].next() if self.categories else None


class CueQueue:
    """포화 시 가장 낮은 우선순위만 버린다. 오래된 입력은 복구 후 재생하지 않는다."""
    def __init__(self, maxsize=24):
        self.maxsize = maxsize; self.items = []; self.lock = threading.Lock(); self.serial = 0

    def put(self, name, priority):
        with self.lock:
            self.serial += 1
            item = (priority, self.serial, name)
            if len(self.items) >= self.maxsize:
                lowest = min(self.items)
                if priority < lowest[0]:
                    return
                self.items.remove(lowest)
            self.items.append(item)

    def take(self):
        with self.lock:
            result = sorted(self.items, reverse=True)
            self.items.clear()
        return [item[2] for item in result]

    def clear(self):
        with self.lock: self.items.clear()

    def qsize(self):
        with self.lock: return len(self.items)

    def empty(self):
        return self.qsize() == 0


class PcmMixer:
    """callback에서는 제한된 PCM 버퍼만 읽고 위치/진단 카운터만 갱신한다."""
    def __init__(self):
        self.lock = threading.RLock()
        self.music = deque(maxlen=BUFFER_CHUNKS)
        self.music_offset = 0
        self.music_frames = 0
        self.music_eof = False
        self.loading = False
        self.music_enabled = False
        self.master_gain = 1.
        self.music_gain = .75
        self.sfx_gain = .85
        self.voices = []
        self.duck_frames = 0
        self.fade_frames = 0
        self.fade_total = 0
        self.submitted_frames = 0
        self.underruns = 0
        self.completed_effects = 0
        self.max_active_voices = 0
        self.clipped_samples = 0
        self.limited_samples = 0
        self.invalid_samples = 0
        self.pre_limiter_peak = 0.
        self._limiter_gain = 1.
        self.output_peak = 0.
        self.last_callback = 0.

    def reset_music(self):
        with self.lock:
            self.music.clear(); self.music_offset = 0; self.music_frames = 0
            self.music_eof = False; self.loading = True; self.fade_frames = self.fade_total = 0

    def add_effect(self, name, samples, gain, priority):
        with self.lock:
            if len(self.voices) >= MAX_VOICES:
                lowest = min(self.voices, key=lambda voice: voice['priority'])
                if priority < lowest['priority']:
                    return False
                self.voices.remove(lowest)
            self.voices.append(dict(name=name, samples=samples, offset=0, gain=gain, priority=priority))
            self.max_active_voices = max(self.max_active_voices, len(self.voices))
            if priority >= 70 or name in {'tetris', 'tspin', 'all_clear', 'level', 'win', 'gameover',
                                         'boss_break', 'fever_start'}:
                self.duck_frames = max(self.duck_frames, min(len(samples) // CHANNELS, SAMPLE_RATE * 2))
            return True

    @property
    def finished(self):
        return self.music_eof and not self.music

    def render(self, frames):
        # 잠금 안에는 산술만 둔다. 파일/디코더/장치 close는 worker에서 실행한다.
        output = array('f', [0.]) * (frames * CHANNELS)
        with self.lock:
            self.submitted_frames += frames
            if self.master_gain <= 0:
                self.voices.clear()
                return output
            if self.music_enabled:
                target = 0
                gain = self.master_gain * self.music_gain * (.4 if self.duck_frames else 1.)
                while target < len(output) and self.music:
                    chunk = self.music[0]
                    count = min(len(output) - target, len(chunk) - self.music_offset)
                    for index in range(count):
                        fade = self.fade_frames / self.fade_total if self.fade_total else 1.
                        output[target + index] = chunk[self.music_offset + index] * gain * fade
                        if self.fade_frames and index % CHANNELS == CHANNELS - 1:
                            self.fade_frames -= 1
                    self.music_frames += count // CHANNELS
                    self.music_offset += count; target += count
                    if self.music_offset == len(chunk):
                        self.music.popleft(); self.music_offset = 0
                if target < len(output) and not self.music_eof:
                    self.underruns += 1
            active = []
            for voice in self.voices:
                samples = voice['samples']; offset = voice['offset']
                count = min(len(output), len(samples) - offset)
                gain = self.master_gain * self.sfx_gain * voice['gain']
                for index in range(count):
                    output[index] += samples[offset + index] * gain
                voice['offset'] += count
                if voice['offset'] < len(samples):
                    active.append(voice)
                else:
                    self.completed_effects += 1
            self.voices = active
            self.duck_frames = max(0, self.duck_frames - frames)
            self._limit(output)
        return output

    def _limit(self, output):
        # 현재 callback 안의 미래 PCM으로 5ms 선행 attack을 만든다. release는
        # callback 경계와 무관하게 sample마다 이어져 블록별 볼륨 펌핑을 피한다.
        targets = []
        for index in range(0, len(output), CHANNELS):
            for channel in range(CHANNELS):
                if not math.isfinite(output[index + channel]):
                    output[index + channel] = 0.
                    self.invalid_samples += 1
            peak = max(abs(output[index]), abs(output[index + 1]))
            self.pre_limiter_peak = max(self.pre_limiter_peak, peak)
            targets.append(min(1., LIMITER_CEILING / peak) if peak else 1.)
        for index in range(len(targets) - 2, -1, -1):
            targets[index] = min(targets[index], targets[index + 1] + LIMITER_ATTACK_STEP)
        gain = self._limiter_gain
        for frame, target in enumerate(targets):
            gain = min(target, 1. - (1. - gain) * LIMITER_RELEASE)
            if gain < .999999:
                self.limited_samples += CHANNELS
            for channel in range(CHANNELS):
                index = frame * CHANNELS + channel
                value = output[index] * gain
                if abs(value) > 1.:
                    self.clipped_samples += 1
                output[index] = max(-1., min(1., value))
                self.output_peak = max(self.output_peak, abs(output[index]))
        self._limiter_gain = gain
