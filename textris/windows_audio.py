"""stdlib waveOut PCM 재생과 읽기 전용 Windows 출력 장치 진단.

각 voice의 별도 handle을 Windows 공유 믹서가 합성한다. API 호출과 객체 수명은
Audio worker 하나가 소유하며 완료 또는 reset 전에는 PCM/WAVEHDR를 해제하지 않는다.
"""
import ctypes as c
import subprocess
import sys
import time
import uuid
import wave

WHDR_DONE = 1
WAVE_MAPPER = 0xffffffff
RATE = 22050


class WaveFormat(c.Structure):
    _fields_ = [('wFormatTag', c.c_uint16), ('nChannels', c.c_uint16),
                ('nSamplesPerSec', c.c_uint32), ('nAvgBytesPerSec', c.c_uint32),
                ('nBlockAlign', c.c_uint16), ('wBitsPerSample', c.c_uint16),
                ('cbSize', c.c_uint16)]


class WaveHeader(c.Structure):
    _fields_ = [('lpData', c.c_void_p), ('dwBufferLength', c.c_uint32),
                ('dwBytesRecorded', c.c_uint32), ('dwUser', c.c_size_t),
                ('dwFlags', c.c_uint32), ('dwLoops', c.c_uint32),
                ('lpNext', c.c_void_p), ('reserved', c.c_size_t)]


def _check(result, operation):
    if result:
        raise OSError(f'{operation}: MMRESULT {result}')


class WaveOutAPI:
    def __init__(self):
        if sys.platform != 'win32':
            raise OSError('waveOut requires Windows')
        self.dll = c.WinDLL('winmm')
        signatures = {
            'waveOutOpen': [c.POINTER(c.c_void_p), c.c_uint32, c.POINTER(WaveFormat),
                            c.c_size_t, c.c_size_t, c.c_uint32],
            'waveOutPrepareHeader': [c.c_void_p, c.POINTER(WaveHeader), c.c_uint32],
            'waveOutWrite': [c.c_void_p, c.POINTER(WaveHeader), c.c_uint32],
            'waveOutUnprepareHeader': [c.c_void_p, c.POINTER(WaveHeader), c.c_uint32],
            'waveOutReset': [c.c_void_p], 'waveOutClose': [c.c_void_p],
        }
        for name, args in signatures.items():
            fn = getattr(self.dll, name)
            fn.argtypes, fn.restype = args, c.c_uint32

    def open(self, fmt):
        handle = c.c_void_p()
        _check(self.dll.waveOutOpen(c.byref(handle), WAVE_MAPPER, c.byref(fmt), 0, 0, 0),
               'waveOutOpen')
        return handle

    def prepare(self, handle, header):
        return self.dll.waveOutPrepareHeader(handle, c.byref(header), c.sizeof(header))

    def write(self, handle, header):
        return self.dll.waveOutWrite(handle, c.byref(header), c.sizeof(header))

    def unprepare(self, handle, header):
        return self.dll.waveOutUnprepareHeader(handle, c.byref(header), c.sizeof(header))

    def reset(self, handle):
        return self.dll.waveOutReset(handle)

    def close(self, handle):
        return self.dll.waveOutClose(handle)


# 실패한 드라이버가 포인터를 여전히 소유하면 메모리를 보존하고 새 할당을 차단한다.
# 정상 종료에는 비어 있다. 반복 정리도 실패하면 프로세스 종료까지 제한된 voice만 보존한다.
_retained = set()


def has_retained_buffers():
    return bool(_retained)


def reap_retained():
    for voice in tuple(_retained):
        try:
            voice._release(reset=True)
        except OSError:
            pass
    return not _retained


class NativePlayback:
    """Popen의 최소 수명 인터페이스. poll의 성공은 청취가 아닌 장치 버퍼 완료다."""
    def __init__(self, path, *, api=None):
        if has_retained_buffers():
            raise OSError('previous waveOut buffers are still owned by the driver')
        try:
            with wave.open(str(path), 'rb') as stream:
                frames = stream.getnframes()
                if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (1, 2, RATE):
                    raise ValueError('unsupported PCM format')
                if not 0 < frames <= RATE * 16:
                    raise ValueError('invalid PCM length')
                pcm = stream.readframes(frames)
                if len(pcm) != frames * 2:
                    raise ValueError('truncated PCM')
        except (wave.Error, EOFError) as exc:
            raise ValueError('invalid WAV') from exc
        self.api = api if api is not None else WaveOutAPI()
        self.handle = None
        self.buffer = c.create_string_buffer(pcm, len(pcm))
        self.header = WaveHeader(lpData=c.cast(self.buffer, c.c_void_p), dwBufferLength=len(pcm))
        self.prepared = False
        self.submitted = False
        self.returncode = None
        self.error = None
        self.duration = frames / RATE
        self.deadline = time.monotonic() + self.duration + 2
        try:
            self.handle = self.api.open(WaveFormat(1, 1, RATE, RATE * 2, 2, 16, 0))
            _check(self.api.prepare(self.handle, self.header), 'waveOutPrepareHeader')
            self.prepared = True
            _check(self.api.write(self.handle, self.header), 'waveOutWrite')
            self.submitted = True
        except OSError:
            try:
                self._release(reset=True)
            except OSError:
                pass
            raise

    def _release(self, *, reset=False):
        try:
            if self.handle is not None:
                if reset and self.submitted and not self.header.dwFlags & WHDR_DONE:
                    _check(self.api.reset(self.handle), 'waveOutReset')
                    self.submitted = False
                if self.prepared:
                    _check(self.api.unprepare(self.handle, self.header), 'waveOutUnprepareHeader')
                    self.prepared = False
                _check(self.api.close(self.handle), 'waveOutClose')
                self.handle = None
            self.buffer = None
            _retained.discard(self)
        except OSError:
            _retained.add(self)
            raise

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        if self.header.dwFlags & WHDR_DONE:
            try:
                self._release()
                self.returncode = 0
            except OSError as exc:
                self.error, self.returncode = str(exc), 1
        elif time.monotonic() > self.deadline:
            self.terminate()
            self.error, self.returncode = 'waveOut completion timed out', 1
        return self.returncode

    def terminate(self):
        if self.handle is None:
            return
        try:
            self._release(reset=True)
            self.returncode = -15
        except OSError as exc:
            self.error, self.returncode = str(exc), 1

    kill = terminate

    def wait(self, timeout=None):
        deadline = time.monotonic() + timeout if timeout is not None else self.deadline + .1
        while self.poll() is None:
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired('waveout', timeout)
            time.sleep(.005)
        return self.returncode


class GUID(c.Structure):
    _fields_ = [('a', c.c_uint32), ('b', c.c_uint16), ('d', c.c_uint16), ('e', c.c_ubyte * 8)]


def _guid(text):
    return GUID.from_buffer_copy(uuid.UUID(text).bytes_le)


def _com_call(obj, slot, args, *values):
    table = c.cast(obj, c.POINTER(c.POINTER(c.c_void_p))).contents
    result = c.WINFUNCTYPE(c.c_int32, c.c_void_p, *args)(table[slot])(obj, *values)
    if result < 0:
        raise OSError(f'COM slot={slot}: HRESULT 0x{result & 0xffffffff:08x}')
    return result


class EndpointMeter:
    """현재 스레드의 COM 수명을 관리하는 읽기 전용 진단기. OS 설정은 바꾸지 않는다."""
    def __init__(self, *, peak=False):
        if sys.platform != 'win32':
            raise OSError('Windows endpoint diagnostics unavailable')
        self.refs = []
        self.initialized = False
        self.ole = c.WinDLL('ole32')
        self.ole.CoInitializeEx.argtypes = [c.c_void_p, c.c_uint32]
        self.ole.CoInitializeEx.restype = c.c_int32
        self.ole.CoCreateInstance.argtypes = [c.POINTER(GUID), c.c_void_p, c.c_uint32,
                                            c.POINTER(GUID), c.POINTER(c.c_void_p)]
        self.ole.CoCreateInstance.restype = c.c_int32
        self.ole.CoUninitialize.argtypes = []
        self.ole.CoUninitialize.restype = None
        try:
            result = self.ole.CoInitializeEx(None, 0)
            # RPC_E_CHANGED_MODE는 기존 apartment를 재사용하되 Uninitialize하지 않는다.
            if result < 0 and result != -2147417850:
                raise OSError(f'CoInitializeEx: {result}')
            self.initialized = result >= 0
            enumerator = c.c_void_p()
            result = self.ole.CoCreateInstance(c.byref(_guid('BCDE0395-E52F-467C-8E3D-C4579291692E')),
                         None, 23, c.byref(_guid('A95664D2-9614-4F35-A746-DE8DB63617E6')), c.byref(enumerator))
            if result < 0:
                raise OSError(f'CoCreateInstance: {result}')
            self.refs.append(enumerator)
            self.endpoint = c.c_void_p()
            _com_call(enumerator, 4, [c.c_int, c.c_int, c.POINTER(c.c_void_p)], 0, 1, c.byref(self.endpoint))
            self.refs.append(self.endpoint)
            self.volume = self._activate('5CDF2C82-841E-4546-9722-0CF74078229A')
            self.meter = self._activate('C02216F6-8C67-4B5B-9D00-D008E73E0064') if peak else None
        except OSError:
            self.close()
            raise

    def _activate(self, iid):
        obj = c.c_void_p()
        _com_call(self.endpoint, 3, [c.POINTER(GUID), c.c_uint32, c.c_void_p, c.POINTER(c.c_void_p)],
                  c.byref(_guid(iid)), 23, None, c.byref(obj))
        self.refs.append(obj)
        return obj

    def state(self):
        volume, mute = c.c_float(), c.c_int32()
        _com_call(self.volume, 9, [c.POINTER(c.c_float)], c.byref(volume))
        _com_call(self.volume, 15, [c.POINTER(c.c_int32)], c.byref(mute))
        return dict(available=True, master_volume=volume.value, master_muted=bool(mute.value))

    def peak(self):
        if self.meter is None:
            raise ValueError('peak measurement was not requested')
        value = c.c_float()
        _com_call(self.meter, 3, [c.POINTER(c.c_float)], c.byref(value))
        return value.value

    def close(self):
        for obj in reversed(self.refs):
            _com_call(obj, 2, [])
        self.refs.clear()
        if self.initialized:
            self.ole.CoUninitialize()
            self.initialized = False


def output_state():
    try:
        meter = EndpointMeter()
        try:
            return meter.state()
        finally:
            meter.close()
    except OSError as exc:
        return dict(available=False, master_volume=None, master_muted=None, error=str(exc))
