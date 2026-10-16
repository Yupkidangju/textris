"""프로브의 실패 JSON, 대기 제한 및 자원 정리 계약을 검증한다."""
import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import windows_audio_probe as probe
from textris.soundtrack import PcmMixer


class FakeMeter:
    instances = []

    def __init__(self, peak=False):
        self.closed = False
        self.instances.append(self)

    def state(self):
        return dict(available=True, master_volume=.37, master_muted=True)

    def peak(self):
        return 0.

    def close(self):
        self.closed = True


class StalledAudio:
    instances = []

    def __init__(self, directory, settings):
        self.closed = False
        self.failed = False
        self.ready = threading.Event()
        self.thread = SimpleNamespace(is_alive=lambda: not self.closed)
        self._device = self._decoder = None
        self.instances.append(self)

    @property
    def music_state(self):
        return dict(error='', paused=True, track_id=None, position=0.)

    @property
    def diagnostics(self):
        return dict(worker_alive=not self.closed, active_voices=0, pending_requests=0,
                    failure_count=int(self.failed), invalid_samples=0, clipped_samples=0,
                    max_active_voices=0)

    def close(self):
        self.closed = True


class FailedDeviceAudio(StalledAudio):
    def __init__(self, directory, settings):
        super().__init__(directory, settings)
        self.catalog = [dict(id=str(index)) for index in range(26)]
        self._samples = {str(index): () for index in range(30)}
        self._effect_meta = {'go': {}}
        self._mixer = PcmMixer()
        self.ready.set()

    @property
    def diagnostics(self):
        return dict(super().diagnostics, asset_errors=(), completed_effects=0)

    @property
    def music_state(self):
        return dict(super().music_state, error='synthetic device unavailable' if self.failed else '')

    def play(self, name):
        self.failed = True


class ProbeFailureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='.audio-probe-test-', dir=probe.ROOT)
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / 'evidence'
        FakeMeter.instances.clear()
        StalledAudio.instances.clear()
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(probe.sys, 'platform', 'win32'))
        self.stack.enter_context(patch.object(probe, 'EndpointMeter', FakeMeter))

    def read_report(self):
        return json.loads((self.output / 'result.json').read_text(encoding='utf-8'))

    def test_missing_miniaudio_is_explicit_failed_json_without_opening_device(self):
        with patch.object(probe, 'find_backend', return_value=None), patch.object(probe, 'Audio') as audio:
            report = probe.run_probe(self.output)
        self.assertFalse(report['passed'])
        self.assertFalse(report['backend_completed'])
        self.assertFalse(report['checks']['miniaudio_available'])
        self.assertEqual(report['errors'][0]['stage'], 'initialization')
        self.assertIn('miniaudio_available', report['errors'][0]['message'])
        self.assertEqual(self.read_report(), report)
        audio.assert_not_called()
        self.assertFalse(FakeMeter.instances)

    def test_loading_timeout_preserves_failure_report_and_closes_audio_and_meter(self):
        with patch.object(probe, 'find_backend', return_value=('miniaudio', 'native')),\
             patch.object(probe, 'Audio', StalledAudio):
            report = probe.run_probe(self.output, timeout=.01)
        self.assertFalse(report['passed'])
        self.assertIn('timed out', report['errors'][0]['message'])
        self.assertEqual(report['errors'][0]['stage'], 'asset_loading')
        self.assertTrue(report['checks']['worker_closed'])
        self.assertTrue(report['checks']['device_and_decoder_closed'])
        self.assertTrue(report['checks']['os_state_unchanged'])
        self.assertTrue(StalledAudio.instances[0].closed)
        self.assertTrue(FakeMeter.instances[0].closed)
        self.assertFalse(self.read_report()['passed'])

    def test_device_failure_is_explicit_and_cannot_pass_via_silent_fallback(self):
        with patch.object(probe, 'find_backend', return_value=('miniaudio', 'native')),\
             patch.object(probe, 'Audio', FailedDeviceAudio):
            report = probe.run_probe(self.output, timeout=.01)
        self.assertFalse(report['passed'])
        self.assertFalse(report['backend_completed'])
        self.assertIn('synthetic device unavailable', report['errors'][0]['message'])
        self.assertFalse(report['checks']['no_device_failures'])
        self.assertTrue(report['checks']['worker_closed'])
        self.assertTrue(FakeMeter.instances[0].closed)

    def test_endpoint_failure_still_writes_failed_report(self):
        with patch.object(probe, 'find_backend', return_value=('miniaudio', 'native')),\
             patch.object(probe, 'EndpointMeter', side_effect=OSError('endpoint unavailable')):
            report = probe.run_probe(self.output)
        self.assertEqual(report['errors'][0]['type'], 'OSError')
        self.assertIn('endpoint unavailable', report['errors'][0]['message'])
        self.assertFalse(self.read_report()['passed'])

    def test_existing_report_is_preserved(self):
        self.output.mkdir()
        target = self.output / 'result.json'
        target.write_text('existing evidence', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            probe.run_probe(self.output)
        self.assertEqual(target.read_text(encoding='utf-8'), 'existing evidence')

    def test_cli_returns_failure_and_prints_report_location(self):
        with patch.object(probe, 'find_backend', return_value=None), contextlib.redirect_stdout(io.StringIO()) as stream:
            result = probe.main(['--output', str(self.output)])
        self.assertEqual(result, 1)
        self.assertEqual(json.loads(stream.getvalue())['path'], str(self.output / 'result.json'))
        self.assertFalse(self.read_report()['listening_confirmed'])

    def test_cli_rejects_unbounded_waits_before_creating_evidence(self):
        for value in ('nan', 'inf', '-1', '0', '31'):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    probe.main(['--output', str(self.output), '--timeout', value])
                self.assertEqual(result.exception.code, 2)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()

