"""읽기 전용 오디오 감사: 실제 ffplay 재생과 Windows 출력 피크만 관측한다."""
from array import array
import ctypes as c
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import wave
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[2]))
from textris.audio import Audio, EFFECTS, command, find_backend, synthesize
from textris.storage import DEFAULTS, Store


class GUID(c.Structure):
    _fields_ = [('a', c.c_uint32), ('b', c.c_uint16), ('d', c.c_uint16), ('e', c.c_ubyte * 8)]


def guid(text):
    return GUID.from_buffer_copy(uuid.UUID(text).bytes_le)


def call(obj, slot, args, *values):
    table = c.cast(obj, c.POINTER(c.POINTER(c.c_void_p))).contents
    fn = c.WINFUNCTYPE(c.c_long, c.c_void_p, *args)(table[slot])
    result = fn(obj, *values)
    if result < 0:
        raise OSError(f'COM slot={slot} HRESULT=0x{result & 0xffffffff:08x}')
    return result


class Meter:
    def __init__(self):
        self.refs = []
        self.ole = c.OleDLL('ole32')
        self.ole.CoInitializeEx(None, 0)
        self.enumerator = c.c_void_p()
        self.ole.CoCreateInstance(c.byref(guid('BCDE0395-E52F-467C-8E3D-C4579291692E')),
                                 None, 23, c.byref(guid('A95664D2-9614-4F35-A746-DE8DB63617E6')),
                                 c.byref(self.enumerator))
        self.refs.append(self.enumerator)
        self.endpoint = c.c_void_p()
        call(self.enumerator, 4, [c.c_int, c.c_int, c.POINTER(c.c_void_p)],
             0, 1, c.byref(self.endpoint))
        self.refs.append(self.endpoint)
        self.meter = self.activate('C02216F6-8C67-4B5B-9D00-D008E73E0064')
        self.volume = self.activate('5CDF2C82-841E-4546-9722-0CF74078229A')
        endpoint_id = c.c_void_p()
        call(self.endpoint, 5, [c.POINTER(c.c_void_p)], c.byref(endpoint_id))
        self.endpoint_id = c.wstring_at(endpoint_id)
        self.ole.CoTaskMemFree(endpoint_id)

    def activate(self, iid):
        obj = c.c_void_p()
        call(self.endpoint, 3, [c.POINTER(GUID), c.c_uint32, c.c_void_p, c.POINTER(c.c_void_p)],
             c.byref(guid(iid)), 23, None, c.byref(obj))
        self.refs.append(obj)
        return obj

    def peak(self):
        value = c.c_float()
        call(self.meter, 3, [c.POINTER(c.c_float)], c.byref(value))
        return value.value

    def state(self):
        volume, mute = c.c_float(), c.c_int()
        call(self.volume, 9, [c.POINTER(c.c_float)], c.byref(volume))
        call(self.volume, 15, [c.POINTER(c.c_int)], c.byref(mute))
        return dict(endpoint_id=self.endpoint_id, master_volume=volume.value, master_muted=bool(mute.value))

    def close(self):
        for obj in reversed(self.refs):
            call(obj, 2, [])
        self.ole.CoUninitialize()


def sample(meter, duration):
    values = []
    until = time.monotonic() + duration
    while time.monotonic() < until:
        values.append(meter.peak())
        time.sleep(.01)
    return dict(samples=len(values), peak=max(values, default=0),
                positive_samples=sum(v > .0001 for v in values))


def wav_info(path):
    with wave.open(str(path), 'rb') as stream:
        values = array('h', stream.readframes(stream.getnframes()))
        return dict(rate=stream.getframerate(), channels=stream.getnchannels(),
                    width=stream.getsampwidth(), duration=stream.getnframes()/stream.getframerate(),
                    minimum=min(values), maximum=max(values),
                    rms=math.sqrt(sum(v*v for v in values)/len(values)))


def main():
    report = dict(python=sys.version, backend=find_backend(),
                  sdl_audio_env={k:v for k,v in os.environ.items() if k.startswith('SDL_AUDIO')})
    meter = Meter()
    try:
        report['endpoint'] = meter.state()
        report['baseline'] = sample(meter, .6)
        report['wav'] = {}
        for name in (*EFFECTS, 'music', 'music1', 'music2', 'music3'):
            path = ROOT/'waveforms'/f'{name}.wav'
            synthesize(name, path, .5)
            report['wav'][name] = wav_info(path)
        proc = subprocess.Popen(command(report['backend'], ROOT/'waveforms'/'tetris.wav')[:-2] +
                                ['info', str(ROOT/'waveforms'/'tetris.wav')],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        report['direct_ffplay'] = sample(meter, 1.5)
        _, output = proc.communicate(timeout=3)
        report['direct_ffplay']['returncode'] = proc.returncode
        (ROOT/'ffplay-stderr.log').write_bytes(output)
        launched = []
        original_popen = subprocess.Popen

        def record_launch(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            launched.append((list(args[0]), process))
            return process

        with patch('textris.audio.subprocess.Popen', side_effect=record_launch):
            settings = dict(DEFAULTS)
            audio = Audio(ROOT/'engine', settings)
            try:
                audio.play('tetris')
                report['engine_effect'] = sample(meter, 1.3)
                report['engine_effect']['status'] = audio.status
                audio.set_music(True)
                report['engine_music'] = sample(meter, 1.3)
                report['engine_music']['process_alive'] = bool(audio.music_process and audio.music_process.poll() is None)
                audio.set_music(False)
                report['engine_pause'] = sample(meter, .6)
                report['engine_pause']['music_stopped'] = audio.music_process is None
                audio.set_music(True)
                sample(meter, .4)
                settings['sound'] = False
                report['engine_mute'] = sample(meter, .6)
                report['engine_mute']['music_stopped'] = audio.music_process is None
                settings['sound'] = True
                settings['volume'] = 0
                audio.play('clear')
                report['engine_zero_volume'] = sample(meter, .3)
                settings['volume'] = .5
                audio.set_music(False)
                from textris.ui import App
                class Window:
                    def getmaxyx(self): return (28, 64)
                store = Store(ROOT/'ui-events')
                store.settings = settings
                with patch.object(App, '_setup'):
                    app = App(Window(), store, audio, seed=42)
                app.start('marathon', record=False)
                sample(meter, .5)
                app.screen = 'playing'
                app.game.state = 'playing'
                app.handle(' ')
                app.process_events()
                report['ui_drop_event'] = sample(meter, 1.2)
                report['ui_drop_event']['board_cells'] = sum(bool(k) for row in app.game.board for k in row)
                app.tick(.02)
                report['ui_music_tick'] = sample(meter, .6)
                app.handle('p')
                app.tick(.02)
                report['ui_pause_tick'] = sample(meter, .6)
                report['ui_pause_tick']['music_stopped'] = audio.music_process is None
            finally:
                audio.close()
            report['engine_closed'] = dict(thread_alive=audio.thread.is_alive(), status=audio.status,
                                          failed=audio.failed,
                                          launches=[dict(command=args, pid=p.pid, returncode=p.poll()) for args,p in launched])
        report['after_close'] = sample(meter, .3)
    finally:
        meter.close()
    with (ROOT/'audio-result.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
