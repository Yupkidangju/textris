"""카탈로그/셔플과 실제 PCM 소비에 따른 스트리밍 계약을 검증한다."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import random
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave

from textris.audio import Audio, resource_root
from textris.soundtrack import AssetLibrary, BalancedShuffle, PcmMixer, LIMITER_CEILING
from textris.storage import DEFAULTS


def make_assets(root, duration=.25):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    effects = []
    for index, (name, theme) in enumerate((('t1', 'cathedral'), ('t2', 'cathedral'),
                                           ('c1', 'classic'), ('c2', 'classic'), ('c3', 'classic'))):
        path = root / (name + '.wav')
        with wave.open(str(path), 'wb') as stream:
            stream.setnchannels(2); stream.setsampwidth(2); stream.setframerate(44100)
            stream.writeframes(array('h', [3000, -3000] * round(44100 * duration)).tobytes())
        rows.append(dict(id=name, title=name.upper(), theme=theme, file=path.name,
                         duration=duration, bpm=120., time_signature='4/4',
                         instruments=['Lead', 'Harmony', 'Bass', 'Drums'],
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for index, name in enumerate(('move', 'rotate', 'hold', 'drop', 'lock', 'tetris', 'win')):
        effects.append(dict(id=name, file='t1.wav', duration=duration, gain=1.,
                            priority=index, cooldown=0., sha256=rows[0]['sha256']))
    (root / 'music.json').write_text(json.dumps(dict(version=1, tracks=rows)), encoding='utf-8')
    (root / 'sfx.json').write_text(json.dumps(dict(version=1, effects=effects)), encoding='utf-8')
    return rows


class FakeDevice:
    backend = 'WASAPI'
    def __init__(self):
        self.running = False; self.closed = False; self.callback_generator = None
    def start(self, callback):
        self.callback_generator = callback; self.running = True
    def pump(self, frames=441):
        return self.callback_generator.send(frames)
    def close(self):
        self.closed = True; self.running = False


class AudioFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'assets'
        self.rows = make_assets(self.root)
        self.settings = dict(DEFAULTS, music_volume=.75, sfx_volume=.85)
        self.devices = []
        self.asset_patch = patch('textris.audio.resource_root', return_value=self.root)
        self.asset_patch.start(); self.addCleanup(self.asset_patch.stop)
        self.device_patch = patch('textris.audio.open_device', side_effect=self.open_device)
        self.device_patch.start(); self.addCleanup(self.device_patch.stop)
        self.audio = Audio(Path(self.tmp.name) / 'data', self.settings)
        self.addCleanup(self.audio.close)
        self.wait_for(lambda: self.audio.ready.is_set())

    def open_device(self, callback):
        device = FakeDevice(); device.start(callback); self.devices.append(device)
        return device

    def wait_for(self, condition):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if condition(): return
            time.sleep(.005)
        self.fail('audio worker condition timed out: ' + str(self.audio.music_state))

    def start_track(self, track='t1', **options):
        self.audio.audition(track, **options)
        self.wait_for(lambda: self.audio.music_state['track_id'] == track and
                      self.audio._mixer.music_eof and not self.audio.music_state['buffering'] and bool(self.devices))


class CatalogTests(unittest.TestCase):
    def test_unsafe_duplicate_and_bad_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'assets'; rows = make_assets(root)
            for change in ({'file': '../escape.wav'}, {'file': 'C:/escape.wav'},
                           {'duration': float('nan')}, {'duration': 10**400}, {'sha256': 'wrong'},
                           {'instruments': ['only one']}):
                with self.subTest(change=change):
                    bad = dict(rows[0], **change)
                    (root / 'music.json').write_text(json.dumps(dict(version=1, tracks=[bad])))
                    with self.assertRaises(ValueError): AssetLibrary(root, Path(tmp) / 'data').load()
            (root / 'music.json').write_text(json.dumps(dict(version=1, tracks=[rows[0], rows[0]])))
            with self.assertRaises(ValueError): AssetLibrary(root, Path(tmp) / 'data').load()

    def test_file_hash_mismatch_is_never_decoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'assets'; make_assets(root)
            library = AssetLibrary(root, Path(tmp) / 'data'); library.load()
            (root / 't1.wav').write_bytes(b'corrupt')
            with self.assertRaises(ValueError): library.path(library.tracks[0])

    def test_two_bags_balance_and_no_early_or_boundary_repeat_without_global_rng(self):
        rows = [dict(id='t' + str(i), theme='cathedral') for i in range(3)]
        rows += [dict(id='c' + str(i), theme='classic') for i in range(8)]
        before = random.getstate()
        shuffle = BalancedShuffle(rows, 'cathedral', random.Random(17))
        chosen = [shuffle.next() for _ in range(192)]
        self.assertEqual(random.getstate(), before)
        for index in range(0, len(chosen), 2):
            self.assertEqual({chosen[index][0], chosen[index+1][0]}, {'t', 'c'})
        for prefix, size in (('t', 3), ('c', 8)):
            category = [item for item in chosen if item.startswith(prefix)]
            for index in range(0, len(category), size):
                group = category[index:index+size]
                self.assertEqual(len(set(group)), len(group))
            self.assertTrue(all(a != b for a, b in zip(category, category[1:])))


class MixerTests(unittest.TestCase):
    def test_peak_limiter_produces_finite_unclipped_pcm_and_releases_smoothly(self):
        import math
        mixer = PcmMixer(); mixer.sfx_gain = 1.
        for index in range(6):
            mixer.add_effect(str(index), array('f', [.8, -.8] * 100), 1., index)
        loud = mixer.render(100)
        self.assertTrue(all(math.isfinite(value) and abs(value) <= LIMITER_CEILING + .000001 for value in loud))
        self.assertEqual(mixer.clipped_samples, 0)
        self.assertGreater(mixer.limited_samples, 0)
        mixer.add_effect('quiet', array('f', [.1, .1] * 1000), 1., 1)
        quiet = mixer.render(1000)
        self.assertLess(quiet[0], .03)
        self.assertGreater(quiet[-1], quiet[0])
        self.assertLess(max(abs(a-b) for a, b in zip(quiet, quiet[1:])), .0001)

    def test_gain_duck_clipping_and_six_voice_priority_limit(self):
        mixer = PcmMixer(); mixer.music_enabled = True
        mixer.music.append(array('f', [.4, .4] * 100))
        mixer.master_gain = .5; mixer.music_gain = .75; mixer.sfx_gain = .5
        for priority in range(6):
            self.assertTrue(mixer.add_effect(str(priority), array('f', [.1, .1] * 100), 1., priority))
        self.assertFalse(mixer.add_effect('low', array('f', [.9, .9] * 100), 1., -1))
        self.assertTrue(mixer.add_effect('high', array('f', [.1, .1] * 100), 1., 100))
        self.assertEqual(len(mixer.voices), 6)
        raw = mixer.render(10)
        self.assertAlmostEqual(raw[0], .4 * .5 * .75 * .4 + .1 * .5 * .5 * 6, places=5)
        self.assertEqual(mixer.music_frames, 10)
        self.assertEqual(mixer.submitted_frames, 10)

    def test_pause_and_underrun_never_advance_music_clock(self):
        mixer = PcmMixer(); mixer.music.append(array('f', [.5, .5] * 20))
        self.assertFalse(any(mixer.render(10))); self.assertEqual(mixer.music_frames, 0)
        mixer.music_enabled = True
        mixer.render(30)
        self.assertEqual(mixer.music_frames, 20)
        self.assertEqual(mixer.underruns, 1)
        mixer.render(10)
        self.assertEqual(mixer.music_frames, 20)


class StreamingTests(AudioFixture):
    def test_pause_seek_mute_suspend_and_game_gate_preserve_audition_position(self):
        self.start_track(playlist=['t1', 'c1'])
        self.devices[-1].pump(2205)
        self.assertAlmostEqual(self.audio.music_state['position'], .05, places=4)
        self.audio.set_music(False)
        self.devices[-1].pump(441)
        self.assertAlmostEqual(self.audio.music_state['position'], .06, places=4)
        for pause, resume in ((lambda: self.audio.pause_audition(True), lambda: self.audio.pause_audition(False)),
                              (lambda: self.audio.set_suspended(True), lambda: self.audio.set_suspended(False)),
                              (lambda: self.settings.update(sound=False), lambda: self.settings.update(sound=True)),
                              (lambda: self.settings.update(music=False), lambda: self.settings.update(music=True))):
            pause(); time.sleep(.025)
            before = self.audio.music_state['position']; self.devices[-1].pump(441)
            self.assertEqual(self.audio.music_state['position'], before)
            resume(); time.sleep(.025)
        self.audio.seek_music(.1)
        self.wait_for(lambda: self.audio.music_state['position'] >= .159)
        self.audio.seek_music(-99)
        self.wait_for(lambda: self.audio.music_state['position'] == 0.)
        self.audio.next_track()
        self.wait_for(lambda: self.audio.music_state['track_id'] == 'c1')

    def test_eof_finishes_only_after_pcm_consumption_and_repeat_is_exact(self):
        self.start_track(playlist=['t1', 'c1'])
        time.sleep(.04)
        self.assertEqual(self.audio.music_state['track_id'], 't1')
        self.devices[-1].pump(11025)
        self.wait_for(lambda: self.audio.music_state['track_id'] == 'c1')
        self.audio.set_audition_options(repeat=True)
        self.wait_for(lambda: self.audio.music_state['repeat'] and self.audio._mixer.music_eof)
        self.devices[-1].pump(11025)
        self.wait_for(lambda: self.audio.music_state['track_id'] == 'c1' and
                      self.audio.music_state['position'] == 0. and not self.audio.music_state['buffering'])

    def test_catalog_immutable_and_reads_and_decoder_never_run_in_caller_or_callback(self):
        self.assertEqual(len(self.audio.catalog), 5)
        with self.assertRaises(TypeError): self.audio.catalog[0]['title'] = 'change'
        with patch('textris.soundtrack.AssetLibrary.path', wraps=self.audio._library.path) as io_call:
            self.start_track()
            count = io_call.call_count
            with patch('builtins.open', side_effect=AssertionError('callback opened a file')):
                self.devices[-1].pump()
                self.audio.play('tetris'); self.audio.pause_audition(True)
            self.assertEqual(io_call.call_count, count)

    def test_game_history_survives_audition_and_long_track_buffer_is_bounded(self):
        self.audio.set_music(True)
        self.wait_for(lambda: self.audio.music_state['track_id'] is not None and not self.audio.music_state['buffering'])
        track = self.audio.music_state['track_id']; self.devices[-1].pump(441)
        position = self.audio.music_state['position']
        self.start_track('t2')
        self.audio.stop_audition()
        self.wait_for(lambda: self.audio.music_state['mode'] == 'game' and not self.audio.music_state['buffering'])
        self.assertEqual(self.audio.music_state['track_id'], track)
        self.assertAlmostEqual(self.audio.music_state['position'], position, places=4)
        self.assertLessEqual(self.audio.diagnostics['buffered_chunks'], 8)

    def test_close_releases_device_worker_and_pending_requests(self):
        self.start_track()
        for _ in range(1000): self.audio.play('move')
        self.assertLessEqual(self.audio.requests.qsize(), 24)
        self.audio.close(); self.audio.close()
        self.assertFalse(self.audio.thread.is_alive())
        self.assertTrue(all(device.closed for device in self.devices))
        self.assertEqual(self.audio.diagnostics['active_voices'], 0)

    def test_slow_resource_io_does_not_block_ui_commands_or_snapshot(self):
        entered = threading.Event(); release = threading.Event()
        original = self.audio._library.path
        def slow_path(row):
            entered.set(); release.wait(2)
            return original(row)
        with patch.object(self.audio._library, 'path', side_effect=slow_path):
            self.audio.audition('t1')
            self.assertTrue(entered.wait(1))
            try:
                before = time.monotonic()
                self.audio.set_music(False); self.audio.play('move')
                self.audio.pause_audition(True); self.audio.seek_music(.1)
                snapshot = self.audio.music_state
                self.assertLess(time.monotonic() - before, .1)
                self.assertTrue(snapshot['buffering'])
            finally: release.set()

    def test_seek_to_end_does_not_falsely_count_a_full_track(self):
        self.start_track(playlist=['t1', 'c1'])
        self.audio.seek_music(999)
        self.wait_for(lambda: self.audio.music_state['track_id'] == 'c1')
        self.assertEqual(self.audio.diagnostics['completed_tracks'], 0)

    def test_broken_track_is_reported_without_infinite_advance_or_device_retry(self):
        (self.root / 'c1.wav').write_bytes(b'corrupt')
        self.audio.audition('c1')
        self.wait_for(lambda: bool(self.audio.music_state['error']))
        self.wait_for(lambda: self.audio.music_state['paused'])
        self.assertIn('checksum', self.audio.music_state['error'])
        self.assertEqual(self.audio.diagnostics['completed_tracks'], 0)
        self.assertEqual(self.audio.failure_count, 0)
        self.assertTrue(self.audio.thread.is_alive())

    def test_shuffle_audition_uses_filtered_pool_without_early_repeat_and_previous_works(self):
        self.start_track('t1', playlist=['t1', 'c1', 'c2'], shuffle=True)
        visited = ['t1']
        for _ in range(2):
            old = self.audio.music_state['track_id']
            self.audio.next_track()
            self.wait_for(lambda: self.audio.music_state['track_id'] != old)
            visited.append(self.audio.music_state['track_id'])
        self.assertEqual(set(visited), {'t1', 'c1', 'c2'})
        self.audio.next_track(-1)
        self.wait_for(lambda: self.audio.music_state['track_id'] == visited[-2])
        self.audio.next_track()
        self.wait_for(lambda: self.audio.music_state['track_id'] == visited[-1])


class LongStreamTests(unittest.TestCase):
    def test_decoder_seek_error_always_uninitializes_native_decoder(self):
        import miniaudio
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'assets'; make_assets(root)
            uninit = Mock(wraps=miniaudio.lib.ma_decoder_uninit)
            lib = SimpleNamespace(**{name: getattr(miniaudio.lib, name) for name in (
                'ma_decoder_config_init', 'ma_decoder_init_file_w', 'ma_decoder_init_file',
                'ma_format_f32', 'MA_SUCCESS', 'MA_AT_END')})
            lib.ma_decoder_seek_to_pcm_frame = lambda *args: -1
            lib.ma_decoder_uninit = uninit
            fake = SimpleNamespace(lib=lib, ffi=miniaudio.ffi, stream_file=miniaudio.stream_file,
                                   SampleFormat=miniaudio.SampleFormat)
            with patch('textris.audio.miniaudio', fake):
                with self.assertRaisesRegex(ValueError, 'seek'):
                    stream = Audio._stream(root / 't1.wav', .1)
                    next(stream)
            uninit.assert_called_once()

    def test_music_decoder_keeps_at_most_eight_chunks_and_closes_on_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'assets'; make_assets(root, duration=12)
            # 긴 음악이 효과음의 8초 검증 한도를 우회하지 않도록 SFX 목록은 비운다.
            (root / 'sfx.json').write_text(json.dumps(dict(version=1, effects=[])))
            device = FakeDevice()
            def launch(callback): device.start(callback); return device
            with patch('textris.audio.resource_root', return_value=root), patch('textris.audio.open_device', side_effect=launch):
                audio = Audio(Path(tmp) / 'data', dict(DEFAULTS))
                try:
                    self.assertTrue(audio.ready.wait(2))
                    audio.audition('t1')
                    deadline = time.monotonic() + 2
                    while audio.diagnostics['buffered_chunks'] < 8 and time.monotonic() < deadline:
                        time.sleep(.005)
                    self.assertEqual(audio.diagnostics['buffered_chunks'], 8)
                    self.assertIsNotNone(audio._decoder)
                    self.assertLessEqual(sum(len(chunk) for chunk in audio._mixer.music), 8 * 2048 * 2)
                    device.pump(2048)
                    time.sleep(.025)
                    self.assertEqual(audio.diagnostics['buffered_chunks'], 8)
                finally: audio.close()
                self.assertIsNone(audio._decoder)
                self.assertTrue(device.closed)


class PackagedMixTests(unittest.TestCase):
    def test_actual_boss_tetris_cues_at_max_bus_gains_do_not_clip(self):
        library = AssetLibrary(resource_root(), Path('.antigravity/audio-overhaul-20261008/test-cache'))
        library.load()
        effects = {row['id']: row for row in library.effects}
        names = ('tetris', 'combo', 'b2b', 'level', 'boss_hit', 'boss_break', 'fever_start')
        rows = sorted((effects[name] for name in names), key=lambda row: row['priority'], reverse=True)
        decoded = {}
        for row in rows:
            samples = array('f'); stream = Audio._stream(library.path(row))
            try:
                for chunk in stream: samples.extend(chunk)
            finally: stream.close()
            decoded[row['id']] = samples
        for offset in (0., 15., 45., 70.):
            with self.subTest(offset=offset):
                mixer = PcmMixer(); mixer.music_enabled = True
                mixer.master_gain = mixer.music_gain = mixer.sfx_gain = 1.
                stream = Audio._stream(library.path(library.tracks[0]), offset)
                try:
                    for block in range(60):
                        if block == 6:
                            for row in rows:
                                mixer.add_effect(row['id'], decoded[row['id']], row['gain'], row['priority'])
                        while len(mixer.music) < 8: mixer.music.append(next(stream))
                        samples = mixer.render(1764)
                        self.assertTrue(all(math.isfinite(value) and abs(value) <= LIMITER_CEILING + .000001 for value in samples))
                finally: stream.close()
                self.assertEqual(mixer.max_active_voices, 6)
                self.assertEqual(mixer.clipped_samples, 0)
                self.assertEqual(mixer.invalid_samples, 0)
                self.assertEqual(mixer.underruns, 0)


if __name__ == '__main__': unittest.main()
