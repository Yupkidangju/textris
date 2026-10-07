"""직접 합성한 PCM 음악/효과음과 중단 가능한 비동기 재생."""
from array import array
import math
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import wave

RATE = 22050
EFFECTS = {
    'move': [(240,.035)], 'rotate': [(440,.04),(660,.045)],
    'hold': [(660,.06),(440,.06)], 'drop': [(180,.08),(80,.09)],
    'lock': [(130,.055)], 'clear': [(523,.09),(659,.09),(784,.14)],
    'tetris': [(523,.07),(659,.07),(784,.07),(1047,.23)],
    'level': [(392,.09),(523,.09),(659,.09),(1047,.2)],
    'gameover': [(440,.15),(349,.15),(262,.15),(131,.35)],
    'win': [(523,.12),(659,.12),(784,.12),(1047,.4)],
}
# 창작 8초 루프: 외부 음원 없이 멜로디와 베이스를 합성한다.
MELODY = [64,67,71,67, 62,66,69,66, 60,64,67,72, 59,62,67,62,
          64,67,74,71, 62,66,73,69, 60,64,72,67, 59,62,67,71]
BASS = [40,40,38,38,36,36,43,43]


def frequency(midi):
    return 440 * 2**((midi-69)/12)


def synthesize(name, path: Path, volume=.5):
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


def find_backend():
    for name in ('paplay','aplay','ffplay','afplay'):
        executable = shutil.which(name)
        if executable:
            return name, executable
    return None


def command(backend, path):
    name, executable = backend
    options = {'paplay':[], 'aplay':['-q'], 'ffplay':['-nodisp','-autoexit','-loglevel','quiet'], 'afplay':[]}
    return [executable,*options[name],str(path)]


class Audio:
    def __init__(self, directory, settings):
        self.directory = Path(directory)
        self.settings = settings
        self.backend = find_backend()
        self.failed = False
        self.requests = queue.Queue(maxsize=24)
        self.music_wanted = False
        self.stopping = threading.Event()
        self.effects = []
        self.music_process = None
        self.intensity = 0
        self.music_started = 0.
        self.last_effect = 0.
        self.thread = threading.Thread(target=self._worker,name='textris-audio',daemon=True)
        self.thread.start()

    @property
    def status(self):
        return self.backend[0] if self.backend and not self.failed else 'audio_silent'

    def play(self, name):
        if not self.settings['sound'] or self.settings['volume'] <= 0 or name not in EFFECTS:
            return
        try:
            self.requests.put_nowait(name)
        except queue.Full:
            pass

    def set_music(self, enabled):
        self.music_wanted = enabled

    def set_intensity(self,value):
        self.intensity=max(0,min(3,int(value)))

    def visual_state(self,now):
        phase=max(0,now-self.music_started) if self.music_started and self.music_process else now
        return phase, max(0,math.sin(phase*math.tau*4))

    def _file(self, name):
        volume = round(self.settings['volume'],1)
        path = audio_path(self.directory,f'{name}-{int(volume*10)}.wav')
        if not path.exists():
            synthesize(name,path,volume)
        return path

    @staticmethod
    def _stop(process):
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=.5)

    def _launch(self, name):
        try:
            return subprocess.Popen(command(self.backend,self._file(name)),
                                    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        except (OSError,ValueError):
            self.failed = True
            return None

    def _worker(self):
        current_volume = self.settings['volume']
        try:
            while not self.stopping.is_set():
                active = []
                for process in self.effects:
                    code = process.poll()
                    if code is None:
                        active.append(process)
                    elif code != 0:
                        self.failed = True
                self.effects = active
                volume_changed = current_volume != self.settings['volume']
                current_volume = self.settings['volume']
                can_music = (self.music_wanted and self.settings['music'] and self.settings['sound']
                             and self.settings['volume'] > 0 and self.backend and not self.failed)
                if not can_music or volume_changed:
                    self._stop(self.music_process); self.music_process = None
                if not self.settings['sound'] or self.failed or volume_changed:
                    for process in self.effects:
                        self._stop(process)
                    self.effects.clear()
                if self.music_process is not None and self.music_process.poll() is not None:
                    if self.music_process.returncode != 0:
                        self.failed = True
                    self.music_process = None
                if can_music and not self.failed and self.music_process is None:
                    self.music_process = self._launch('music'+str(self.intensity) if self.intensity else 'music')
                    self.music_started=time.monotonic()
                try:
                    name = self.requests.get(timeout=.025)
                except queue.Empty:
                    continue
                if not self.settings['sound'] or self.settings['volume'] <= 0:
                    continue
                now = time.monotonic()
                if name in ('move','rotate','lock') and now-self.last_effect < .07:
                    continue
                self.last_effect = now
                if self.backend and not self.failed:
                    if len(self.effects) >= 3:
                        self._stop(self.effects.pop(0))
                    process = self._launch(name)
                    if process:
                        self.effects.append(process)
        finally:
            self._stop(self.music_process)
            for process in self.effects:
                self._stop(process)

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=3)
