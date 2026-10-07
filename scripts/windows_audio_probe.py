"""외부 재생기를 금지한 waveOut 실장치 검사. OS 볼륨/mute는 읽기만 한다.

python scripts/windows_audio_probe.py --output .antigravity/audit-2-fix-audio/native-runtime
피크는 OS 마스터 감쇠 전 값이며 실제 사람 청취를 입증하지 않는다.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from textris.audio import Audio, EFFECTS, check_audio, find_backend, synthesize
from textris.storage import DEFAULTS, Store
from textris.windows_audio import EndpointMeter, NativePlayback, has_retained_buffers


def sample(meter, seconds, voices=()):
    peaks = []
    active_max = 0
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        peaks.append(meter.peak())
        active_max = max(active_max, sum(v.returncode is None for v in voices))
        time.sleep(.004)
    return dict(samples=len(peaks), peak=max(peaks, default=0),
                positive_samples=sum(v > .001 for v in peaks), active_max=active_max,
                tail_peak=max(peaks[-20:], default=0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('native Windows is required')
    args.output.mkdir(parents=True, exist_ok=True)
    result_path = args.output / 'result.json'
    if result_path.exists():
        parser.error('result already exists; choose a new output directory')
    report = dict(created=datetime.now(timezone.utc).isoformat(), python=sys.version,
                  platform=sys.platform, listening_confirmed=False,
                  physical_device_removal_tested=False, os_settings_changed=False,
                  backend=None, voices=[], checks={})
    meter = EndpointMeter(peak=True)
    voices = []
    started = time.monotonic()

    def launch(path):
        voice = NativePlayback(path)
        voices.append(voice)
        report['voices'].append(dict(name=path.stem, started=time.monotonic() - started,
                                     duration=voice.duration))
        return voice

    try:
        report['endpoint_before'] = meter.state()
        report['baseline'] = sample(meter, .4)
        # WAV 합성 비용이 loop/peak 표본 시점을 흔들지 않도록 재생 전에 준비한다.
        directory = args.output / 'data'
        for name in (*EFFECTS, 'music', 'music1', 'music2', 'music3'):
            synthesize(name, directory / 'audio' / f'{name}-5.wav', .5)
        with patch.dict(os.environ, {'PATH': ''}), patch('textris.audio.subprocess.Popen', side_effect=AssertionError('external player forbidden')):
            with patch('textris.audio.shutil.which', side_effect=AssertionError('external player lookup forbidden')):
                report['backend'] = find_backend()
                with patch('textris.audio.NativePlayback', side_effect=launch):
                    settings = dict(DEFAULTS)
                    audio = Audio(directory, settings)
                    try:
                        report['effects'] = {}
                        for name in EFFECTS:
                            audio.play(name)
                            report['effects'][name] = sample(meter, 1.05, voices)
                        report['short_repeats'] = []
                        for _ in range(4):
                            audio.play('move')
                            report['short_repeats'].append(sample(meter, .3, voices))
                        audio.set_music(True)
                        report['loop'] = sample(meter, 9.1, voices)
                        report['loop']['music_launches'] = sum(v['name'].startswith('music') for v in report['voices'])
                        for name in ('gameover', 'win', 'tetris'):
                            audio.play(name)
                        report['simultaneous'] = sample(meter, .25, voices)
                        audio.set_music(False)
                        report['pause'] = sample(meter, 1., voices)
                        report['pause']['music_stopped'] = audio.music_process is None
                        audio.set_music(True)
                        sample(meter, .15, voices)
                        audio.play('win')
                        sample(meter, .1, voices)
                        settings['sound'] = False
                        report['mute'] = sample(meter, .5, voices)
                        report['mute']['voices_stopped'] = not audio.effects and audio.music_process is None
                        settings['sound'] = True
                        sample(meter, .2, voices)
                        audio.play('win')
                        sample(meter, .1, voices)
                        settings['volume'] = 0
                        report['volume_zero'] = sample(meter, .5, voices)
                        report['volume_zero']['voices_stopped'] = not audio.effects and audio.music_process is None
                        settings['volume'] = .5
                        audio.set_music(False)
                        sample(meter, .1, voices)
                        from textris.ui import App
                        class Window:
                            def getmaxyx(self):
                                return (28, 64)
                        store = Store(args.output / 'ui-data')
                        store.settings = settings
                        with patch.object(App, '_setup'):
                            app = App(Window(), store, audio, seed=42)
                        app.start('marathon', record=False)
                        app.screen = app.game.state = 'playing'
                        app.handle(' ')
                        app.process_events()
                        report['ui_drop'] = sample(meter, .7, voices)
                        report['ui_drop']['board_cells'] = sum(bool(v) for row in app.game.board for v in row)
                        app.tick(.02)
                        sample(meter, .3, voices)
                        app.handle('p')
                        app.tick(.02)
                        report['ui_pause'] = sample(meter, .5, voices)
                        report['ui_pause']['music_stopped'] = audio.music_process is None
                    finally:
                        audio.close()
                    report['close'] = dict(worker_alive=audio.thread.is_alive(),
                                           retained_buffers=has_retained_buffers(), failed=audio.failed,
                                           handles_open=sum(v.handle is not None for v in voices))
                    report['after_close'] = sample(meter, .4, voices)
                    report['audio_check'] = check_audio(args.output / 'cli-check', settings)
        report['endpoint_after'] = meter.state()
        for record, voice in zip(report['voices'], voices):
            record.update(returncode=voice.returncode, handle_open=voice.handle is not None,
                          buffer_retained=voice.buffer is not None, error=voice.error)
        threshold = max(.001, report['baseline']['peak'] + .001)
        checks = report['checks']
        checks['native_without_external_player'] = report['backend'][0] == 'waveout'
        for name, result in report['effects'].items():
            checks[f'effect_signal_{name}'] = result['peak'] > threshold
        checks['short_move_repeated'] = all(v['peak'] > threshold for v in report['short_repeats'])
        checks['music_loop'] = report['loop']['music_launches'] >= 2 and report['loop']['tail_peak'] > threshold
        checks['one_music_three_effects'] = report['simultaneous']['active_max'] == 4 and report['simultaneous']['peak'] > threshold
        for name in ('pause', 'mute', 'volume_zero', 'ui_pause'):
            result = report[name]
            checks[f'{name}_stopped'] = result.get('voices_stopped', result.get('music_stopped')) and result['tail_peak'] < threshold
        checks['ui_command_signal'] = report['ui_drop']['peak'] > threshold and report['ui_drop']['board_cells'] == 4
        checks['close_reclaims'] = not any(report['close'].values())
        checks['after_close_silent'] = report['after_close']['tail_peak'] < threshold
        checks['os_state_unchanged'] = report['endpoint_before'] == report['endpoint_after']
        checks['backend_check_completed'] = report['audio_check']['backend_completed']
        checks['all_handles_released'] = all(not v['handle_open'] and not v['buffer_retained'] for v in report['voices'])
        checks['no_driver_errors'] = all(v['returncode'] in (0, -15) and v['error'] is None for v in report['voices'])
        report['passed'] = all(checks.values())
    finally:
        meter.close()
        with result_path.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
    print(json.dumps(dict(path=str(result_path), passed=report.get('passed', False),
                          checks=report['checks'], endpoint=report.get('endpoint_after')), indent=2))
    return 0 if report.get('passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
