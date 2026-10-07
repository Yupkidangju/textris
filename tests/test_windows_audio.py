"""실장치 없이 Windows PCM 소유권과 worker 실패 경계를 재현한다."""
import ctypes
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from textris.audio import Audio, find_backend, synthesize
from textris.storage import DEFAULTS
from tests.test_soundtrack_audio import AudioFixture


class FakeWaveOut:
    def __init__(self):
        self.calls = []
        self.headers = []
        self.next_handle = 42
        self.errors = {}

    def open(self, fmt):
        self.calls.append('open')
        if self.errors.get('open'):
            raise OSError('device unavailable')
        self.next_handle += 1
        return ctypes.c_void_p(self.next_handle)

    def prepare(self, handle, header):
        self.headers.append((handle.value, header))
        return self._result('prepare')

    def write(self, handle, header):
        return self._result('write')

    def reset(self, handle):
        result = self._result('reset')
        if not result:
            for owner, header in self.headers:
                if owner == handle.value:
                    header.dwFlags |= 1
        return result

    def unprepare(self, handle, header):
        return self._result('unprepare')

    def close(self, handle):
        return self._result('close')

    def _result(self, name):
        self.calls.append(name)
        return self.errors.get(name, 0)


class NativePlaybackTests(unittest.TestCase):
    def setUp(self):
        from textris import windows_audio
        self.native = windows_audio
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'move.wav'
        synthesize('move', self.path)
        self.api = FakeWaveOut()

    def voice(self):
        return self.native.NativePlayback(self.path, api=self.api)

    def test_short_effect_retains_exact_pcm_until_done_then_unprepares_and_closes(self):
        voice = self.voice()
        self.assertEqual(voice.header.dwBufferLength, round(22050 * .035) * 2)
        self.assertIsNone(voice.poll())
        self.assertIsNotNone(voice.buffer)
        self.assertNotIn('unprepare', self.api.calls)
        voice.header.dwFlags |= self.native.WHDR_DONE
        self.assertEqual(voice.poll(), 0)
        self.assertIsNone(voice.buffer)
        self.assertIsNone(voice.handle)
        self.assertEqual(self.api.calls, ['open', 'prepare', 'write', 'unprepare', 'close'])

    def test_stop_resets_before_unprepare_close_and_is_idempotent(self):
        voice = self.voice()
        voice.terminate()
        voice.terminate()
        self.assertEqual(self.api.calls[-3:], ['reset', 'unprepare', 'close'])
        self.assertEqual(self.api.calls.count('close'), 1)
        self.assertIsNone(voice.buffer)

    def test_failed_reset_keeps_driver_owned_memory_until_cleanup_recovers(self):
        voice = self.voice()
        self.api.errors['reset'] = 6
        voice.terminate()
        self.assertIsNotNone(voice.buffer)
        self.assertNotIn('unprepare', self.api.calls)
        self.assertTrue(self.native.has_retained_buffers())
        self.api.errors.clear()
        self.assertTrue(self.native.reap_retained())
        self.assertIsNone(voice.buffer)
        self.assertFalse(self.native.has_retained_buffers())

    def test_failed_unprepare_keeps_buffer_and_blocks_new_voice(self):
        voice = self.voice()
        voice.header.dwFlags |= self.native.WHDR_DONE
        self.api.errors['unprepare'] = 33
        self.assertEqual(voice.poll(), 1)
        self.assertIsNotNone(voice.buffer)
        with self.assertRaises(OSError):
            self.voice()
        self.api.errors.clear()
        self.assertTrue(self.native.reap_retained())
        self.assertIsNone(voice.buffer)

    def test_prepare_and_write_failures_close_resources(self):
        for operation in ('prepare', 'write'):
            with self.subTest(operation=operation):
                self.api = FakeWaveOut()
                self.api.errors[operation] = 7
                with self.assertRaises(OSError):
                    self.voice()
                self.assertEqual(self.api.calls[-1], 'close')
                self.assertEqual('unprepare' in self.api.calls, operation == 'write')
                self.assertFalse(self.native.has_retained_buffers())

    def test_stalled_driver_is_bounded_and_resets_its_buffer(self):
        voice = self.voice()
        with patch('textris.windows_audio.time.monotonic', return_value=voice.deadline + 1):
            self.assertEqual(voice.poll(), 1)
        self.assertEqual(self.api.calls[-3:], ['reset', 'unprepare', 'close'])
        self.assertIsNone(voice.buffer)

    def test_corrupt_or_oversized_wave_never_opens_device(self):
        self.path.write_bytes(b'not a wave file')
        with self.assertRaises(ValueError):
            self.voice()
        self.assertEqual(self.api.calls, [])
        import wave
        with wave.open(str(self.path), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(22050)
            stream.writeframes(bytes(22050 * 17 * 2))
        with self.assertRaises(ValueError):
            self.voice()
        self.assertEqual(self.api.calls, [])


class WorkerNativeTests(AudioFixture):
    def test_music_plus_six_effects_pause_mute_volume_and_close(self):
        self.start_track()
        for name in ('move', 'rotate', 'hold', 'drop', 'lock', 'tetris'):
            self.audio.play(name)
        self.wait_for(lambda: self.audio.diagnostics['active_voices'] == 6)
        self.audio.play('win')
        self.wait_for(lambda: any(voice['name'] == 'win' for voice in self.audio._mixer.voices))
        self.assertEqual(self.audio.diagnostics['active_voices'], 6)
        self.assertFalse(any(voice['name'] == 'move' for voice in self.audio._mixer.voices))
        self.audio.pause_audition(True); time.sleep(.025)
        position = self.audio.music_state['position']
        self.devices[-1].pump(441)
        self.assertEqual(self.audio.music_state['position'], position)
        self.settings['volume'] = 0
        self.wait_for(lambda: self.audio.diagnostics['active_voices'] == 0)
        self.assertFalse(any(self.devices[-1].pump()))
        self.settings['volume'] = .5; self.audio.pause_audition(False)
        self.wait_for(lambda: not self.audio.music_state['paused'])
        self.devices[-1].pump()
        self.assertGreater(self.audio.music_state['position'], position)
        self.audio.close()
        self.assertFalse(self.audio.thread.is_alive())
        self.assertTrue(all(device.closed for device in self.devices))

    def test_music_loops_only_after_consumed_eof_without_reopening_device(self):
        self.start_track(playlist=['t1'], repeat=True)
        time.sleep(.04)
        self.assertEqual(self.audio.diagnostics['completed_tracks'], 0)
        self.devices[-1].pump(11025)
        self.wait_for(lambda: self.audio.diagnostics['completed_tracks'] == 1)
        self.assertEqual(self.audio.diagnostics['last_completed_track'], 't1')
        self.assertEqual(self.audio.diagnostics['last_completed_frames'], 11025)
        self.assertEqual(len(self.devices), 1)

    def test_native_failures_retry_with_delay_and_stop_at_budget(self):
        with patch('textris.audio.open_device', side_effect=OSError('no device')) as launch, patch('textris.audio.NATIVE_RETRY_DELAY', .08):
            self.audio.set_music(True)
            self.wait_for(lambda: self.audio.failed)
            self.assertEqual(launch.call_count, 1)
            self.wait_for(lambda: launch.call_count == 3)
            time.sleep(.2)
            self.assertEqual(launch.call_count, 3)
            self.assertEqual(self.audio.status, 'audio_silent')
            self.assertTrue(self.audio.thread.is_alive())

    def test_one_device_failure_counts_once_and_recovery_keeps_history(self):
        with patch('textris.audio.NATIVE_RETRY_DELAY', .06):
            self.start_track()
            for expected in (1, 2, 3):
                old_device = self.devices[-1]
                self.audio.play('drop'); self.audio.play('win')
                old_device.running = False
                self.wait_for(lambda: self.audio.failure_count == expected)
                self.assertTrue(old_device.closed)
                self.assertEqual(self.audio.diagnostics['active_voices'], 0)
                if expected < 3:
                    self.wait_for(lambda: len(self.devices) == expected + 1)
                    self.assertFalse(self.audio.failed)
            count = len(self.devices); time.sleep(.25)
            self.assertEqual(len(self.devices), count)
            self.assertTrue(self.audio.failed)

    def test_failed_recovery_launches_consume_remaining_attempts(self):
        self.start_track()
        with patch('textris.audio.open_device', side_effect=OSError('gone')) as launch, patch('textris.audio.NATIVE_RETRY_DELAY', .03):
            self.devices[-1].running = False
            self.wait_for(lambda: self.audio.failure_count == 3)
            time.sleep(.12)
            self.assertEqual(launch.call_count, 2)
            self.assertTrue(self.audio.failed)

    def test_retry_recovers_without_replaying_stale_effects(self):
        with patch('textris.audio.open_device') as launch, patch('textris.audio.NATIVE_RETRY_DELAY', .08):
            launch.side_effect = lambda callback: (_ for _ in ()).throw(OSError('temporary')) if launch.call_count == 1 else self.open_device(callback)
            self.audio.set_music(True)
            self.wait_for(lambda: self.audio.failed)
            self.audio.play('drop')
            self.wait_for(lambda: launch.call_count == 2 and not self.audio.failed)
            self.assertEqual(self.audio.diagnostics['active_voices'], 0)
            self.assertTrue(self.audio.requests.empty())

    def test_effect_only_backend_recovers_on_fresh_request_after_delay(self):
        with patch('textris.audio.open_device', side_effect=OSError('temporary')):
            self.audio.play('drop')
            self.wait_for(lambda: self.audio.failed)
        self.wait_for(lambda: self.audio._can_launch())
        self.audio.play('win')
        self.wait_for(lambda: self.audio.diagnostics['active_voices'] == 1)
        self.assertFalse(self.audio.failed)
        self.assertEqual(self.audio.failure_count, 1)

    def test_callback_failure_is_contained_and_consumes_one_retry_event(self):
        self.start_track()
        with patch.object(self.audio._mixer, 'render', side_effect=ValueError('bad callback state')):
            self.assertFalse(any(self.devices[-1].pump()))
        self.wait_for(lambda: self.audio.failed)
        self.assertIn('bad callback state', self.audio.music_state['error'])
        self.assertEqual(self.audio.failure_count, 1)
        self.assertTrue(self.audio.thread.is_alive())


class DeviceSelectionTests(unittest.TestCase):
    def test_constructor_failure_releases_context_and_device_before_garbage_collection(self):
        import gc
        import miniaudio
        from unittest.mock import Mock
        from textris.audio import StreamingDevice
        original = miniaudio.lib
        class Library:
            ma_device_init = staticmethod(lambda *args: -1)
            ma_device_uninit = Mock()
            ma_context_uninit = Mock()
            def __getattr__(self, name): return getattr(original, name)
        lib = Library()
        enabled = gc.isenabled(); gc.disable()
        try:
            with patch.object(miniaudio, 'lib', lib), patch.object(StreamingDevice, '_make_context', side_effect=lambda *args: miniaudio.ffi.new('ma_context *')):
                try:
                    with self.assertRaises(miniaudio.MiniaudioError): StreamingDevice()
                    lib.ma_device_uninit.assert_called_once()
                    lib.ma_context_uninit.assert_called_once()
                finally:
                    gc.collect()
                lib.ma_device_uninit.assert_called_once()
                lib.ma_context_uninit.assert_called_once()
        finally:
            if enabled: gc.enable()

    def test_windows_wasapi_first_then_winmm_without_external_player(self):
        import miniaudio
        from textris.audio import open_device
        from tests.test_soundtrack_audio import FakeDevice
        callback = iter(())
        fallback = FakeDevice()
        with patch('textris.audio.sys.platform', 'win32'), patch('textris.audio.StreamingDevice', side_effect=[OSError('wasapi offline'), fallback]) as device:
            self.assertIs(open_device(callback), fallback)
        self.assertEqual(device.call_args_list[0].kwargs['backends'], [miniaudio.Backend.WASAPI])
        self.assertEqual(device.call_args_list[1].kwargs['backends'], [miniaudio.Backend.WINMM])

    def test_nonwindows_uses_native_default_and_null_backend_is_failure(self):
        from textris.audio import open_device
        from tests.test_soundtrack_audio import FakeDevice
        device = FakeDevice(); device.backend = 'Null'
        with patch('textris.audio.sys.platform', 'linux'), patch('textris.audio.StreamingDevice', return_value=device) as create:
            with self.assertRaises(OSError): open_device(iter(()))
        self.assertIsNone(create.call_args.kwargs['backends'])
        self.assertTrue(device.closed)

    def test_start_failure_closes_first_device_before_winmm_fallback(self):
        from textris.audio import open_device
        from tests.test_soundtrack_audio import FakeDevice
        first, second = FakeDevice(), FakeDevice()
        with patch.object(first, 'start', side_effect=OSError('start failure')), patch('textris.audio.sys.platform', 'win32'), patch('textris.audio.StreamingDevice', side_effect=[first, second]):
            self.assertIs(open_device(iter(())), second)
        self.assertTrue(first.closed)


class AudioCheckTests(unittest.TestCase):
    def test_endpoint_failure_keeps_explicit_unknown_fields(self):
        from textris.windows_audio import output_state
        with patch('textris.windows_audio.EndpointMeter', side_effect=OSError('endpoint disappeared')):
            result = output_state()
        self.assertEqual(result, dict(available=False, master_volume=None, master_muted=None,
                                     error='endpoint disappeared'))

    def test_check_reports_app_mute_without_creating_files_or_playing(self):
        from textris.audio import check_audio
        for settings in (dict(DEFAULTS, sound=False), dict(DEFAULTS, volume=0)):
            with tempfile.TemporaryDirectory() as tmp, patch('textris.audio.open_device') as launch:
                with patch('textris.audio.output_state', return_value={'available': False}):
                    result = check_audio(tmp, settings)
                self.assertTrue(result['app_muted'])
                self.assertFalse(result['backend_completed'])
                self.assertFalse(result['listening_confirmed'])
                self.assertEqual(list(Path(tmp).iterdir()), [])
                launch.assert_not_called()

    def test_packaged_effect_completion_does_not_claim_listening_when_os_muted(self):
        import threading
        from textris.audio import check_audio
        from tests.test_soundtrack_audio import make_assets, FakeDevice
        devices = []
        class PumpDevice(FakeDevice):
            def start(self, callback):
                super().start(callback)
                self.worker = threading.Thread(target=self.run)
                self.worker.start()
            def run(self):
                while self.running:
                    self.pump(); time.sleep(.01)
            def close(self):
                super().close(); self.worker.join(timeout=1)
        def launch(callback):
            device = PumpDevice(); device.start(callback); devices.append(device)
            return device
        os_state = dict(available=True, master_volume=0., master_muted=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'assets'; make_assets(root)
            with patch('textris.audio.resource_root', return_value=root), patch('textris.audio.open_device', side_effect=launch), patch('textris.audio.output_state', return_value=os_state):
                result = check_audio(Path(tmp) / 'data', dict(DEFAULTS))
        self.assertTrue(result['backend_completed'], result)
        self.assertFalse(result['app_muted'])
        self.assertEqual(result['os_output'], os_state)
        self.assertFalse(result['listening_confirmed'])
        self.assertEqual(result['diagnostics']['completed_effects'], 1)
        self.assertTrue(all(device.closed for device in devices))

    def test_check_timeout_closes_streaming_device(self):
        from textris.audio import check_audio
        from tests.test_soundtrack_audio import make_assets, FakeDevice
        device = FakeDevice()
        def launch(callback): device.start(callback); return device
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'assets'; make_assets(root)
            with patch('textris.audio.resource_root', return_value=root), patch('textris.audio.open_device', side_effect=launch):
                result = check_audio(Path(tmp) / 'data', dict(DEFAULTS), timeout=.15)
        self.assertFalse(result['backend_completed'])
        self.assertIn('timed out', result['error'])
        self.assertTrue(device.closed)


if __name__ == '__main__': unittest.main()
