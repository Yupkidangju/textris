"""현행 Audio worker/miniaudio/PcmMixer의 Windows 실장치 검사.

python scripts/windows_audio_probe.py --output .antigravity/windows-audio-probe
OS 볼륨/mute를 읽기만 하며, callback PCM 제출과 사람 청취를 구분한다.
"""
import argparse
from collections import deque
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from textris.audio import Audio, find_backend
from textris.soundtrack import MAX_VOICES
from textris.storage import DEFAULTS
from textris.windows_audio import EndpointMeter


class ProbeFailure(RuntimeError):
    pass


def run_probe(output, timeout=5.):
    """각 대기를 제한하고 실패와 정리 결과도 result.json에 남긴다."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / 'result.json'
    if result_path.exists():
        raise FileExistsError('result already exists; choose a new output directory')
    report = dict(schema_version=2, created=datetime.now(timezone.utc).isoformat(),
                  python=sys.version, platform=sys.platform, backend=None,
                  listening_confirmed=False, physical_device_removal_tested=False,
                  os_settings_changed=False, backend_completed=False, passed=False,
                  checks={}, stages={}, errors=[],
                  evidence_scope='Real Audio worker, packaged decoder and device callbacks; '
                                 'PCM completion is not a human listening test. Endpoint peaks '
                                 'may include other applications.',
                  instrumentation=['PcmMixer.add_effect observer', 'PcmMixer.render PCM observer'])
    audio = meter = None
    stage = 'initialization'
    blocks = deque(maxlen=256)
    admissions = []
    settings = dict(DEFAULTS, sound=True, music=True, volume=.5,
                    music_volume=.75, sfx_volume=.85)

    def snapshot():
        return dict(diagnostics=dict(audio.diagnostics), music_state=dict(audio.music_state))

    def require(name, passed):
        report['checks'][name] = bool(passed)
        if not passed:
            raise ProbeFailure(name)

    def wait_for(condition, label):
        deadline = time.monotonic() + timeout
        while True:
            if condition():
                return
            if audio.failed or not audio.thread.is_alive():
                raise ProbeFailure(label + ': audio worker/device failed: ' + audio.music_state['error'])
            if time.monotonic() >= deadline:
                raise ProbeFailure(label + ': timed out')
            time.sleep(.005)

    def observe(seconds=.15):
        start = time.monotonic()
        deadline = start + seconds
        while time.monotonic() < deadline:
            if audio.failed or not audio.thread.is_alive():
                raise ProbeFailure('audio worker/device failed: ' + audio.music_state['error'])
            time.sleep(.005)
        rows = [row for row in tuple(blocks) if row['at'] >= start]
        result = snapshot()
        result.update(callbacks=len(rows), pcm_peak=max((r['peak'] for r in rows), default=0.),
                      endpoint_peak=meter.peak())
        require(stage + '_callbacks', bool(rows))
        return result

    def frozen(label, operation):
        nonlocal stage
        stage = label
        operation()
        wait_for(lambda: audio.music_state['paused'], label + ' paused')
        # worker 설정 반영과 장치의 이전 버퍼 소진을 먼저 기다린다.
        observe(.12)
        before = audio.music_state
        sample = observe(.18)
        after = sample['music_state']
        sample['position_before'] = before['position']
        report['stages'][label] = sample
        require(label + '_preserves_position', before['track_id'] == after['track_id'] and
                abs(before['position'] - after['position']) < .0001)
        return sample

    def resumed(label, operation):
        nonlocal stage
        stage = label
        before = audio.music_state
        operation()
        wait_for(lambda: not audio.music_state['paused'] and
                 audio.music_state['position'] > before['position'] + .03, label)
        after = audio.music_state
        report['stages'][label] = snapshot()
        require(label + '_same_track', before['track_id'] == after['track_id'])

    try:
        if sys.platform != 'win32':
            raise ProbeFailure('native Windows is required')
        report['backend'] = find_backend()
        require('miniaudio_available', bool(report['backend']) and report['backend'][0] == 'miniaudio')
        meter = EndpointMeter(peak=True)
        report['endpoint_before'] = meter.state()
        report['baseline_endpoint_peak'] = meter.peak()
        audio = Audio(output / 'data', settings)
        stage = 'asset_loading'
        wait_for(audio.ready.is_set, stage)
        report['stages'][stage] = snapshot()
        require('packaged_assets_loaded', len(audio.catalog) == 26 and len(audio._samples) == 30 and
                not audio.diagnostics['asset_errors'])

        # 원본 함수를 그대로 호출하고 반환한다. 관측은 제품 동작을 대체하지 않는다.
        mixer = audio._mixer
        original_add, original_render = mixer.add_effect, mixer.render
        def add_effect(name, samples, gain, priority):
            with mixer.lock:
                accepted = original_add(name, samples, gain, priority)
                admissions.append(dict(name=name, accepted=accepted, priority=priority,
                                       active=[voice['name'] for voice in mixer.voices]))
                return accepted
        def render(frames):
            pcm = original_render(frames)
            blocks.append(dict(at=time.monotonic(), frames=frames,
                               peak=max((abs(value) for value in pcm), default=0.)))
            return pcm
        mixer.add_effect, mixer.render = add_effect, render

        stage = 'effects'
        report['stages'][stage] = {}
        for name in audio._effect_meta:
            completed = audio.diagnostics['completed_effects']
            first = len(admissions)
            audio.play(name)
            wait_for(lambda: audio.diagnostics['completed_effects'] > completed, 'effect ' + name)
            require('effect_completed_' + name, any(row['name'] == name and row['accepted']
                                                   for row in admissions[first:]))
            report['stages'][stage][name] = snapshot()
        require('physical_backend', str(audio.diagnostics['device_backend']).lower() in ('wasapi', 'winmm'))
        require('pcm_signal', audio.diagnostics['output_peak'] > .001)

        stage = 'cooldown'
        first = len(admissions)
        audio.play('go')
        wait_for(lambda: len(admissions) > first, 'initial cooldown cue')
        audio.play('go')
        observe(.1)
        rows = admissions[first:]
        require('cooldown_suppresses_duplicate', sum(row['name'] == 'go' for row in rows) == 1)
        wait_for(lambda: audio.diagnostics['active_voices'] == 0, 'cooldown drain')
        # 배포 cooldown(.3초) 뒤의 같은 입력이 다시 허용되는지도 확인한다.
        time.sleep(.32)
        audio.play('go')
        wait_for(lambda: len(admissions) > first + 1, 'cooldown repeat')
        report['stages'][stage] = dict(admissions=admissions[first:], **snapshot())
        wait_for(lambda: audio.diagnostics['active_voices'] == 0, 'repeat drain')

        stage = 'overlap_priority'
        first = len(admissions)
        for name in ('all_clear', 'win', 'fever_start', 'boss_break', 'tetris', 'clear_triple'):
            audio.play(name)
        wait_for(lambda: audio.diagnostics['active_voices'] == MAX_VOICES, 'six overlapping cues')
        audio.play('move')
        wait_for(lambda: any(row['name'] == 'move' for row in admissions[first:]), 'low priority rejection')
        audio.play('gameover')
        wait_for(lambda: any(row['name'] == 'gameover' for row in admissions[first:]), 'high priority replacement')
        rows = admissions[first:]
        require('low_priority_rejected', any(row['name'] == 'move' and not row['accepted'] for row in rows))
        require('high_priority_retained', any(row['name'] == 'gameover' and row['accepted'] and
                len(row['active']) == MAX_VOICES and 'clear_triple' not in row['active'] for row in rows))
        report['stages'][stage] = dict(admissions=rows, **observe())
        wait_for(lambda: audio.diagnostics['active_voices'] == 0, 'overlap drain')

        stage = 'music_start'
        audio.set_music(True)
        wait_for(lambda: audio.music_state['position'] > .08, stage)
        report['stages'][stage] = observe()
        frozen('pause', lambda: audio.set_suspended(True))
        resumed('resume', lambda: audio.set_suspended(False))
        frozen('music_off', lambda: settings.update(music=False))
        # 음악만 끈 상태에서도 SFX는 실제 callback에서 끝나야 한다.
        stage = 'music_off_sfx'
        before = audio.diagnostics['completed_effects']
        audio.play('move')
        wait_for(lambda: audio.diagnostics['completed_effects'] > before, stage)
        require('music_off_sfx_completed', audio.music_state['paused'])
        resumed('music_on', lambda: settings.update(music=True))

        for label, key, value in (('mute', 'sound', False), ('volume_zero', 'volume', 0.)):
            audio.play('gameover')
            wait_for(lambda: audio.diagnostics['active_voices'] > 0, label + ' active cue')
            sample = frozen(label, lambda: settings.update({key: value}))
            require(label + '_silent_pcm', sample['pcm_peak'] == 0. and
                    sample['diagnostics']['active_voices'] == 0 and sample['diagnostics']['pending_requests'] == 0)
            resumed(label + '_restore', lambda: settings.update({key: True if key == 'sound' else .5}))
            # gameover의 cooldown을 넘겨 다음 mute 검사가 이전 입력에 의존하지 않게 한다.
            observe(.52)

        stage = 'volume'
        settings.update(volume=.25, music_volume=.35, sfx_volume=.45)
        observe(.12)
        with mixer.lock:
            gains = dict(master=mixer.master_gain, music=mixer.music_gain, sfx=mixer.sfx_gain)
        report['stages'][stage] = dict(gains=gains, **observe())
        require('volume_applied', gains == dict(master=.25, music=.35, sfx=.45))

        stage = 'audition'
        saved = audio.music_state
        target = next(row['id'] for row in audio.catalog if row['id'] != saved['track_id'])
        audio.audition(target)
        wait_for(lambda: audio.music_state['track_id'] == target and audio.music_state['position'] > .03, stage)
        frozen('audition_pause', lambda: audio.pause_audition(True))
        resumed('audition_resume', lambda: audio.pause_audition(False))
        stage = 'stop_audition'
        audio.stop_audition()
        wait_for(lambda: audio.music_state['mode'] == 'game' and
                 audio.music_state['track_id'] == saved['track_id'], stage)
        restored = audio.music_state
        report['stages'][stage] = dict(saved_game=saved, **snapshot())
        require('stop_restores_game_position', saved['position'] <= restored['position'] < saved['position'] + .5)
        sample = frozen('stop_music', lambda: audio.set_music(False))
        require('stop_silent_pcm', sample['pcm_peak'] == 0.)
        # PCM 소비 완료 후 장치 출력 버퍼(40ms)보다 길게 배출 시간을 준다.
        report['device_drain_seconds'] = .12
        observe(.12)
        report['backend_completed'] = True
    except Exception as exc:
        report['errors'].append(dict(stage=stage, type=type(exc).__name__, message=str(exc)))
        if audio is not None:
            report['failure_snapshot'] = snapshot()
    finally:
        if audio is not None:
            try:
                audio.close()
                final = dict(audio.diagnostics)
                report['closed_diagnostics'] = final
                report['checks']['worker_closed'] = not final['worker_alive']
                report['checks']['voices_and_queue_released'] = final['active_voices'] == 0 and final['pending_requests'] == 0
                report['checks']['device_and_decoder_closed'] = audio._device is None and audio._decoder is None
                report['checks']['no_device_failures'] = final['failure_count'] == 0 and not audio.failed
                report['checks']['valid_unclipped_pcm'] = final['invalid_samples'] == 0 and final['clipped_samples'] == 0
                report['checks']['six_voice_limit'] = final['max_active_voices'] <= MAX_VOICES
            except Exception as exc:
                report['errors'].append(dict(stage='audio_cleanup', type=type(exc).__name__, message=str(exc)))
        if meter is not None:
            try:
                report['endpoint_after'] = meter.state()
                report['checks']['os_state_unchanged'] = report['endpoint_before'] == report['endpoint_after']
            except Exception as exc:
                report['errors'].append(dict(stage='endpoint_after', type=type(exc).__name__, message=str(exc)))
            finally:
                try:
                    meter.close()
                except Exception as exc:
                    report['errors'].append(dict(stage='meter_cleanup', type=type(exc).__name__, message=str(exc)))
        report['checks']['backend_completed'] = report['backend_completed']
        report['passed'] = not report['errors'] and all(report['checks'].values())
        with result_path.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=5., help='maximum seconds per worker/device wait (default: 5)')
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or not .1 <= args.timeout <= 30:
        parser.error('--timeout must be finite and between 0.1 and 30 seconds')
    try:
        report = run_probe(args.output, args.timeout)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(dict(path=str(args.output / 'result.json'), passed=report['passed'],
                          backend_completed=report['backend_completed'], checks=report['checks'],
                          errors=report['errors']), indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
