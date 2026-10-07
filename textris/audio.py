"""배포 PCM 음원을 worker에서 디코딩하고 miniaudio 단일 장치로 재생한다."""
from array import array
from collections import deque
from importlib import resources
import math
from pathlib import Path
import random
import sys
import threading
import time
import wave

try:
    import miniaudio
except (ImportError, OSError):
    miniaudio = None

from .soundtrack import (AssetLibrary, BalancedShuffle, CueQueue, PcmMixer, ShuffleBag,
                         SAMPLE_RATE, CHANNELS, CHUNK_FRAMES, BUFFER_CHUNKS)
from .windows_audio import output_state
RATE = 22050
NATIVE_RETRY_DELAY = .5
NATIVE_FAILURE_LIMIT = 3
EFFECTS = {
    'move': [(240,.035)], 'rotate': [(440,.04),(660,.045)],
    'hold': [(660,.06),(440,.06)], 'drop': [(180,.08),(80,.09)],
    'lock': [(130,.055)], 'clear': [(523,.09),(659,.09),(784,.14)],
    'tetris': [(523,.07),(659,.07),(784,.07),(1047,.23)],
    'level': [(392,.09),(523,.09),(659,.09),(1047,.2)],
    'gameover': [(440,.15),(349,.15),(262,.15),(131,.35)],
    'win': [(523,.12),(659,.12),(784,.12),(1047,.4)],
}
# 기존 waveOut 소유권/PCM 회귀 테스트 전용 데이터. 제품 재생 경로에서는 사용하지 않는다.
MELODY = [64,67,71,67, 62,66,69,66, 60,64,67,72, 59,62,67,62,
          64,67,74,71, 62,66,73,69, 60,64,72,67, 59,62,67,71]
BASS = [40,40,38,38,36,36,43,43]


def frequency(midi):
    return 440 * 2**((midi-69)/12)


def synthesize(name, path: Path, volume=.5):
    """이전 PCM 테스트용 fixture 생성기. Audio와 check_audio의 폴백이 아니다."""
    volume = max(0.,min(1.,volume))
    samples = array('h')
    if name.startswith('music'):
        notes = [(frequency(n),.25) for n in MELODY]
    else:
        notes = EFFECTS[name]
    position=0.
    for i,(freq,duration) in enumerate(notes):
        end=position+RATE*duration
        count=round(end)-round(position); position=end
        for j in range(count):
            t = j/RATE
            # 클릭 없는 attack/release와 약한 배음으로 읽기 쉬운 chiptune 음색.
            envelope = min(1,j/(RATE*.008),(count-j)/(RATE*.035))
            signal = math.sin(2*math.pi*freq*t)*.7 + math.sin(4*math.pi*freq*t)*.18
            if name.startswith('music'):
                bass = frequency(BASS[i//4])
                intensity=int(name[-1]) if name[-1].isdigit() else 0
                signal = .5*signal + .3*math.sin(2*math.pi*bass*t)
                signal += intensity*.035*math.sin(2*math.pi*70*t)*math.exp(-t*25)
                signal=max(-1.,min(1.,signal))
            samples.append(int(signal*envelope*volume*24000))
    if sys.byteorder != 'little':
        samples.byteswap()
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(RATE)
        f.writeframes(samples.tobytes())


def audio_path(directory, filename):
    root = Path(directory).resolve()
    path = root/'audio'/filename
    if not path.resolve().is_relative_to(root):
        raise ValueError('audio path escapes data root')
    return path


def resource_root():
    return resources.files('textris').joinpath('assets', 'audio')


def find_backend():
    """외부 실행파일 탐색 없이 설치된 decoder 사용 가능 여부만 보고한다."""
    return ('miniaudio', 'native') if miniaudio is not None else None


class StreamingDevice(miniaudio.PlaybackDevice if miniaudio is not None else object):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, **kwargs)
        except Exception:
            # CFFI handle의 self cycle 때문에 __del__/GC에 장치 정리를 맡길 수 없다.
            self.close()
            raise

    def close(self):
        # miniaudio 1.71 PlaybackDevice는 직접 만든 context의 해제를 누락한다.
        # 장치를 먼저 끝낸 뒤 context를 딱 한 번 해제하여 재시도 누적을 막는다.
        if getattr(self, '_device', None) is not None:
            super().close()
        context = getattr(self, '_context', None)
        if context is not None:
            miniaudio.lib.ma_context_uninit(context)
            self._context = None
        self._ffi_handle = None


def open_device(callback):
    if miniaudio is None:
        raise OSError('miniaudio is not installed')
    backends = ([miniaudio.Backend.WASAPI], [miniaudio.Backend.WINMM]) if sys.platform == 'win32' else (None,)
    error = None
    for backend in backends:
        device = None
        try:
            device = StreamingDevice(output_format=miniaudio.SampleFormat.FLOAT32,
                                     nchannels=CHANNELS, sample_rate=SAMPLE_RATE,
                                     buffersize_msec=40, backends=backend, app_name='TEXTRIS')
            if device.backend.lower() == 'null':
                raise OSError('no physical audio output backend')
            device.start(callback)
            return device
        except Exception as exc:
            error = exc
            if device is not None:
                device.close()
    raise OSError('audio device unavailable: ' + str(error))


class Audio:
    def __init__(self, directory, settings):
        self.directory = Path(directory)
        self.settings = settings
        self.backend = find_backend()
        self.failed = False
        self.failure_count = 0
        self.retry_at = 0.
        self.requests = CueQueue(24)
        self.music_wanted = False
        self.stopping = threading.Event()
        self.ready = threading.Event()
        self._wake = threading.Event()
        self._state_lock = threading.RLock()
        self._command_lock = threading.Lock()
        self._commands = deque(maxlen=32)
        self._mixer = PcmMixer()
        self._library = None
        self._catalog = ()
        self._tracks = {}
        self._effect_meta = {}
        self._samples = {}
        self._cooldowns = {}
        self._asset_errors = []
        self._bad_tracks = set()
        self._decoder = None
        self._device = None
        self._device_opened = 0.
        self._callback_error = ''
        self._error = ''
        self._theme = settings.get('theme', 'cathedral')
        self._rng = random.Random()
        self._game_shuffle = None
        self._track = None
        self._position_base = 0.
        self._mode = 'game'
        self._paused = False
        self._suspended = False
        self._shuffle = False
        self._repeat = False
        self._playlist = []
        self._audition_bag = None
        self._audition_history = []
        self._history_index = -1
        self._saved_game = None
        self._pending_theme = None
        self._theme_deadline = 0.
        self._finished_tracks = 0
        self._last_completed_track = None
        self._track_completions = {}
        self._natural_eof = False
        self._last_completed_frames = 0
        self._decoded_frames = 0
        self.intensity = 0
        self.music_started = 0.
        self.thread = threading.Thread(target=self._worker, name='textris-audio', daemon=True)
        self.thread.start()

    @property
    def catalog(self):
        return self._catalog

    @property
    def status(self):
        if self.failed or not self.backend:
            return 'audio_silent'
        return self._device.backend.lower() if self._device is not None else 'miniaudio'

    @property
    def music_state(self):
        with self._state_lock, self._mixer.lock:
            row = self._track or {}
            position = self._position()
            enabled = self._music_enabled()
            return dict(track_id=row.get('id'), title=row.get('title', ''),
                        theme=row.get('theme', self._theme), position=position,
                        duration=row.get('duration', 0.), bpm=row.get('bpm', 0.),
                        instruments=row.get('instruments', ()), paused=not enabled,
                        buffering=bool(row and not self._mixer.music and not self._mixer.music_eof),
                        mode=self._mode, shuffle=self._shuffle, repeat=self._repeat,
                        error=self._error)

    @property
    def diagnostics(self):
        with self._state_lock, self._mixer.lock:
            return dict(submitted_frames=self._mixer.submitted_frames,
                        music_frames=self._mixer.music_frames, underruns=self._mixer.underruns,
                        active_voices=len(self._mixer.voices), buffered_chunks=len(self._mixer.music),
                        completed_effects=self._mixer.completed_effects,
                        completed_tracks=self._finished_tracks,
                        last_completed_track=self._last_completed_track,
                        last_completed_frames=self._last_completed_frames,
                        track_completions=dict(self._track_completions),
                        max_active_voices=self._mixer.max_active_voices,
                        clipped_samples=self._mixer.clipped_samples,
                        limited_samples=self._mixer.limited_samples,
                        invalid_samples=self._mixer.invalid_samples,
                        pre_limiter_peak=self._mixer.pre_limiter_peak,
                        output_peak=self._mixer.output_peak,
                        device_backend=self._device.backend if self._device is not None else None,
                        failure_count=self.failure_count, worker_alive=self.thread.is_alive(),
                        asset_errors=tuple(self._asset_errors), pending_requests=self.requests.qsize())

    def play(self, name):
        name = 'clear_single' if name == 'clear' else name
        if self.stopping.is_set() or not self._sound_enabled() or (self.failed and not self._can_launch()):
            return
        row = self._effect_meta.get(name)
        if row is not None:
            self.requests.put(name, row['priority'])
            self._wake.set()

    def set_music(self, enabled):
        if self.music_wanted != bool(enabled):
            self.music_wanted = bool(enabled)
            self._wake.set()

    def set_theme(self, theme):
        self._command('theme', theme)

    def audition(self, track_id, *, playlist=None, shuffle=False, repeat=False):
        self._command('audition', track_id, tuple(playlist) if playlist is not None else None,
                      bool(shuffle), bool(repeat))

    def set_audition_options(self, shuffle=None, repeat=None):
        self._command('options', shuffle, repeat)

    def pause_audition(self, paused):
        self._command('pause', bool(paused))

    def seek_music(self, delta_seconds):
        if type(delta_seconds) in (int, float) and math.isfinite(delta_seconds):
            self._command('seek', float(delta_seconds))

    def next_track(self, direction=1):
        self._command('next', -1 if direction < 0 else 1)

    def stop_audition(self):
        self._command('stop_audition')

    def set_suspended(self, suspended):
        if self._suspended != bool(suspended):
            self._suspended = bool(suspended)
            self._wake.set()

    def set_intensity(self, value):
        self.intensity = max(0, min(3, int(value)))

    def visual_state(self, now):
        if not hasattr(self, '_mixer'):
            phase = max(0, now - self.music_started) if self.music_started and self.music_process else now
            return phase, max(0, math.sin(phase * math.tau * 4))
        state = self.music_state
        phase = state['position'] if state['track_id'] else now
        beat = state['bpm'] / 60. if state['bpm'] else 2.
        return phase, max(0, math.sin(phase * math.tau * beat))

    def _command(self, *command):
        if not self.stopping.is_set():
            with self._command_lock:
                self._commands.append(command)
            self._wake.set()

    def _sound_enabled(self):
        return bool(self.settings.get('sound', True) and self.settings.get('volume', .5) > 0)

    def _music_enabled(self):
        return (self._sound_enabled() and self.settings.get('music', True)
                and self.settings.get('music_volume', .75) > 0 and not self._suspended
                and not self.failed and not self._paused
                and (self._mode == 'audition' or self.music_wanted))

    def _position(self):
        position = self._position_base + self._mixer.music_frames / SAMPLE_RATE
        return min(self._track['duration'], position) if self._track else 0.

    def _close_decoder(self):
        decoder, self._decoder = self._decoder, None
        if decoder is not None:
            decoder.close()

    def _load_assets(self):
        self._library = AssetLibrary(resource_root(), self.directory)
        for filename, key in (('music.json', 'tracks'), ('sfx.json', 'effects')):
            try:
                rows = self._library._read_catalog(filename, key)
                setattr(self._library, key, rows)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self._asset_errors.append(str(exc))
        self._catalog = self._library.tracks
        self._tracks = {row['id']: row for row in self._catalog}
        self._effect_meta = {row['id']: row for row in self._library.effects}
        self._game_shuffle = BalancedShuffle(self._catalog, self._theme, self._rng)
        total_samples = 0
        if miniaudio is not None:
            for row in self._library.effects:
                if self.stopping.is_set():
                    break
                stream = None
                try:
                    path = self._library.path(row)
                    stream = self._stream(path)
                    samples = array('f')
                    for chunk in stream:
                        if len(samples) + len(chunk) > SAMPLE_RATE * CHANNELS * 8:
                            raise ValueError('effect exceeds eight seconds: ' + row['id'])
                        samples.extend(chunk)
                    if not samples or total_samples + len(samples) > 8 * 1024 * 1024:
                        raise ValueError('effect PCM cache exceeds 32 MiB')
                    self._samples[row['id']] = samples
                    total_samples += len(samples)
                except Exception as exc:
                    self._asset_errors.append(str(exc))
                finally:
                    if stream is not None:
                        stream.close()
        if self._asset_errors:
            self._error = self._asset_errors[0]

    @staticmethod
    def _stream(path, position=0.):
        # 1.71 stream_file는 초기 seek 실패 시 decoder를 해제하지 않는다.
        # 동일 miniaudio C API에 try/finally를 붙여 실패와 generator.close를 보장한다.
        ffi, lib = miniaudio.ffi, miniaudio.lib
        decoder = ffi.new('ma_decoder *')
        config = lib.ma_decoder_config_init(lib.ma_format_f32, CHANNELS, SAMPLE_RATE)
        if sys.platform == 'win32':
            result = lib.ma_decoder_init_file_w(ffi.new('wchar_t[]', str(path)), ffi.addressof(config), decoder)
        else:
            result = lib.ma_decoder_init_file(str(path).encode(sys.getfilesystemencoding()), ffi.addressof(config), decoder)
        if result != lib.MA_SUCCESS:
            raise ValueError('failed to initialize audio decoder: ' + str(result))
        try:
            if position > 0 and lib.ma_decoder_seek_to_pcm_frame(decoder, round(position * SAMPLE_RATE)) != lib.MA_SUCCESS:
                raise ValueError('failed to seek audio decoder')
            buffer = ffi.new('float[]', CHUNK_FRAMES * CHANNELS)
            frames_read = ffi.new('ma_uint64 *')
            while True:
                result = lib.ma_decoder_read_pcm_frames(decoder, buffer, CHUNK_FRAMES, frames_read)
                if result not in (lib.MA_SUCCESS, lib.MA_AT_END):
                    raise ValueError('failed to decode audio frames: ' + str(result))
                count = frames_read[0]
                if count:
                    samples = array('f')
                    samples.frombytes(ffi.buffer(buffer, count * CHANNELS * 4))
                    yield samples
                if not count or result == lib.MA_AT_END:
                    break
        finally:
            lib.ma_decoder_uninit(decoder)

    def _select(self, track_id, position=0.):
        self._close_decoder()
        self._natural_eof = False
        self._decoded_frames = 0
        with self._state_lock, self._mixer.lock:
            self._mixer.reset_music()
            self._track = self._tracks.get(track_id)
            self._position_base = max(0., min(float(self._track['duration']), position)) if self._track else 0.
        if self._track is None:
            if track_id is not None:
                self._error = 'Track is unavailable: ' + str(track_id)
            return
        if self._position_base >= self._track['duration']:
            self._mixer.music_eof = True
            return
        if miniaudio is None:
            self._error = 'miniaudio is not installed'
            return
        try:
            path = self._library.path(self._track)
            self._decoder = self._stream(path, self._position_base)
            self._bad_tracks.discard(track_id)
            self._error = ''
            self.music_started = time.monotonic() - self._position_base
        except Exception as exc:
            self._error = str(exc)
            self._bad_tracks.add(track_id)
            self._mixer.music_eof = True

    def _next_game(self):
        if self._game_shuffle is not None:
            for _ in range(len(self._catalog) * 2):
                name = self._game_shuffle.next()
                if name is None or name not in self._bad_tracks:
                    return name
        return None

    def _next_audition(self, direction=1, automatic=False):
        if not self._playlist:
            return None
        current = self._track['id'] if self._track else None
        if automatic and self._repeat:
            return current
        if direction < 0 and self._shuffle and self._history_index > 0:
            self._history_index -= 1
            return self._audition_history[self._history_index]
        if self._shuffle:
            if self._history_index + 1 < len(self._audition_history):
                self._history_index += 1
                return self._audition_history[self._history_index]
            name = self._audition_bag.next()
            self._audition_history.append(name)
            if len(self._audition_history) > 128:
                self._audition_history.pop(0)
            self._history_index = len(self._audition_history) - 1
            return name
        index = self._playlist.index(current) if current in self._playlist else -1
        return self._playlist[(index + direction) % len(self._playlist)]

    def _new_audition_bag(self, current):
        self._audition_bag = ShuffleBag(self._playlist, self._rng)
        self._audition_bag.bag = [name for name in self._playlist if name != current]
        self._rng.shuffle(self._audition_bag.bag)
        self._audition_bag.last = current
        self._audition_history = [current] if current else []
        self._history_index = len(self._audition_history) - 1

    def _handle_commands(self):
        with self._command_lock:
            commands = tuple(self._commands)
            self._commands.clear()
        for command, *args in commands:
            if command == 'theme':
                theme = args[0]
                if theme == self._theme or theme not in ('cathedral', 'cyberpunk', 'space', 'fire', 'crt', 'mono'):
                    continue
                self._theme = theme
                self._game_shuffle = BalancedShuffle(self._catalog, theme, self._rng)
                if self._mode == 'game':
                    if self._track and self._music_enabled():
                        self._pending_theme = theme
                        self._theme_deadline = time.monotonic() + .15
                        with self._mixer.lock:
                            self._mixer.fade_frames = self._mixer.fade_total = round(SAMPLE_RATE * .1)
                    else:
                        self._select(self._next_game())
                else:
                    self._saved_game = None
            elif command == 'audition':
                name, playlist, shuffle, repeat = args
                if name not in self._tracks:
                    self._error = 'Track is unavailable: ' + str(name)
                    continue
                if self._mode == 'game':
                    self._saved_game = (self._track['id'], self._position()) if self._track else None
                self._pending_theme = None
                self._mode = 'audition'; self._paused = False
                self._shuffle = shuffle; self._repeat = repeat
                self._playlist = list(dict.fromkeys(item for item in (playlist or self._tracks) if item in self._tracks))
                if name not in self._playlist:
                    self._playlist.insert(0, name)
                self._new_audition_bag(name)
                self._select(name)
            elif command == 'options':
                shuffle, repeat = args
                if shuffle is not None:
                    self._shuffle = bool(shuffle)
                    self._new_audition_bag(self._track['id'] if self._track else None)
                if repeat is not None:
                    self._repeat = bool(repeat)
            elif command == 'pause' and self._mode == 'audition':
                self._paused = args[0]
            elif command == 'seek' and self._track:
                position = max(0., min(self._track['duration'], self._position() + args[0]))
                self._select(self._track['id'], position)
            elif command == 'next':
                self._select(self._next_audition(args[0]) if self._mode == 'audition' else self._next_game())
            elif command == 'stop_audition' and self._mode == 'audition':
                self._mode = 'game'; self._paused = False; self._shuffle = False; self._repeat = False
                self._select(*self._saved_game) if self._saved_game else self._select(None)
                self._saved_game = None

    def _fill_music(self):
        while self._decoder is not None and len(self._mixer.music) < BUFFER_CHUNKS:
            if self.stopping.is_set():
                return
            try:
                chunk = next(self._decoder)
                if not chunk:
                    raise StopIteration
                self._decoded_frames += len(chunk) // CHANNELS
                with self._mixer.lock:
                    self._mixer.music.append(chunk)
                    self._mixer.loading = False
            except StopIteration:
                self._close_decoder()
                self._natural_eof = bool(self._decoded_frames)
                if not self._natural_eof:
                    self._error = 'Track contains no decodable audio: ' + self._track['id']
                    self._bad_tracks.add(self._track['id'])
                self._mixer.music_eof = True
            except Exception as exc:
                self._close_decoder()
                self._error = str(exc)
                self._bad_tracks.add(self._track['id'])
                self._mixer.music_eof = True

    def _callback(self):
        frames = yield array('f')
        while True:
            self._mixer.last_callback = time.monotonic()
            try:
                # UI 설정 변경은 다음 PCM callback부터 적용한다. 디코드 선행량과 무관하다.
                self._sync_mixer()
                output = self._mixer.render(frames)
            except Exception as exc:
                self._callback_error = str(exc)
                output = array('f', [0.]) * (frames * CHANNELS)
            frames = yield output

    def _close_device(self):
        device, self._device = self._device, None
        if device is not None:
            device.close()

    def _failure(self, error):
        self.failure_count += 1
        self.retry_at = time.monotonic() + NATIVE_RETRY_DELAY * self.failure_count
        self.failed = True
        self._error = str(error)
        self.requests.clear()
        with self._mixer.lock:
            self._mixer.voices.clear()
            self._mixer.music_enabled = False
        try:
            self._close_device()
        except Exception as exc:
            self._error = str(error) + '; close: ' + str(exc)

    def _can_launch(self):
        return bool(self.backend and (not self.failed or
                    (self.failure_count < NATIVE_FAILURE_LIMIT and time.monotonic() >= self.retry_at)))

    def _ensure_device(self):
        if self._device is not None:
            return True
        if not self._can_launch():
            return False
        callback = self._callback(); next(callback)
        try:
            self._device = open_device(callback)
            self._device_opened = time.monotonic()
            self._mixer.last_callback = self._device_opened
            self._callback_error = ''
            self.failed = False
            self._error = ''
            return True
        except Exception as exc:
            callback.close()
            self._failure(exc)
            return False

    def _sync_mixer(self):
        with self._mixer.lock:
            self._mixer.master_gain = max(0., min(1., self.settings.get('volume', .5))) if self._sound_enabled() and not self._suspended else 0.
            self._mixer.music_gain = max(0., min(1., self.settings.get('music_volume', .75)))
            self._mixer.sfx_gain = max(0., min(1., self.settings.get('sfx_volume', .85)))
            self._mixer.music_enabled = self._music_enabled() and not self._mixer.loading
            if not self._sound_enabled() or self._suspended:
                self._mixer.voices.clear()
                self.requests.clear()

    def _step(self):
        self._handle_commands()
        if self._pending_theme and (self._mixer.fade_frames == 0 or time.monotonic() >= self._theme_deadline):
            self._pending_theme = None
            self._select(self._next_game())
        # 실패 상태에서도 재시도 허용 시점에 game/audition 의도를 유지한다.
        wants_music = (self._sound_enabled() and self.settings.get('music', True)
                       and self.settings.get('music_volume', .75) > 0 and not self._suspended
                       and not self._paused and (self._mode == 'audition' or self.music_wanted))
        if self._track is None and wants_music and self._mode == 'game':
            self._select(self._next_game())
        self._fill_music()
        if wants_music and self._track and self._mixer.finished and not self._pending_theme:
            if self._track['id'] in self._bad_tracks:
                if self._mode == 'audition':
                    self._paused = True
                else:
                    self._select(self._next_game())
            else:
                if self._natural_eof and self._mixer.music_frames:
                    with self._state_lock:
                        self._finished_tracks += 1
                        self._last_completed_track = self._track['id']
                        self._last_completed_frames = self._mixer.music_frames
                        self._track_completions[self._track['id']] = self._track_completions.get(self._track['id'], 0) + 1
                self._select(self._next_audition(automatic=True) if self._mode == 'audition' else self._next_game())
            self._fill_music()
        if self._device is not None:
            if (not self._device.running or self._device.callback_generator is None
                    or self._callback_error or time.monotonic() - self._mixer.last_callback > 2.):
                self._failure(self._callback_error or 'audio device stopped or stalled')
        names = self.requests.take()
        if (wants_music and self._track and self._mixer.music) or names:
            if not self._ensure_device():
                names = []
        self._sync_mixer()
        now = time.monotonic()
        for name in names:
            row = self._effect_meta[name]
            if name in self._samples and now - self._cooldowns.get(name, -math.inf) >= row['cooldown']:
                if self._mixer.add_effect(name, self._samples[name], row['gain'], row['priority']):
                    self._cooldowns[name] = now

    def _worker(self):
        try:
            self._load_assets()
            self.ready.set()
            while not self.stopping.is_set():
                self._step()
                self._wake.wait(.01)
                self._wake.clear()
        except Exception as exc:
            self._error = str(exc)
            self.failed = True
        finally:
            self.ready.set()
            self._close_decoder()
            try:
                self._close_device()
            except Exception as exc:
                self._error = str(exc)
            with self._mixer.lock:
                self._mixer.voices.clear(); self._mixer.reset_music()
            self.requests.clear()
            self._samples.clear()

    def close(self):
        self.stopping.set()
        self._wake.set()
        self.thread.join(timeout=3)


def check_audio(directory, settings, timeout=5):
    """실제 배포 SFX의 PCM 소비 완료, 앱/OS 설정과 청취 여부를 분리한다."""
    backend = find_backend()
    result = dict(backend=backend[0] if backend else None, backend_completed=False,
                  app_sound=settings['sound'], app_music=settings['music'], app_volume=settings['volume'],
                  app_muted=not settings['sound'] or settings['volume'] <= 0,
                  os_output=output_state(), listening_confirmed=False)
    if not backend or result['app_muted']:
        return result
    audio = Audio(directory, settings)
    deadline = time.monotonic() + timeout
    try:
        if not audio.ready.wait(max(0., deadline - time.monotonic())):
            result['error'] = 'audio asset loading timed out'
            return result
        if 'tetris' not in audio._samples:
            result['error'] = audio.music_state['error'] or 'packaged tetris sound is unavailable'
            return result
        audio.play('tetris')
        while time.monotonic() < deadline:
            state = audio.diagnostics
            if state['completed_effects']:
                # 프레임 제출 뒤 장치의 한 출력 버퍼가 끝날 시간을 준다.
                time.sleep(.08)
                result['backend_completed'] = not audio.failed
                result['backend'] = state['device_backend'] or result['backend']
                break
            if audio.failed:
                break
            time.sleep(.01)
        if not result['backend_completed']:
            result['error'] = audio.music_state['error'] or 'audio playback timed out'
        result['diagnostics'] = audio.diagnostics
    finally:
        audio.close()
    return result
