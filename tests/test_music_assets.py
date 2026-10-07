"""Validate shipped recordings and their actual authored MIDI sources."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import unittest

try:
    import mido
except ImportError:
    mido=None
try:
    import miniaudio
except ImportError:
    miniaudio=None

ROOT=Path(__file__).resolve().parents[1]
AUDIO=ROOT/"textris/assets/audio"
PRODUCTION=ROOT/"assets/audio-production/music"


class MusicAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tracks=json.loads((AUDIO/"music.json").read_text(encoding="utf-8"))["tracks"]

    def test_catalog_has_all_themed_compositions_and_classics(self):
        self.assertEqual(len(self.tracks),26)
        self.assertEqual(len({t["id"] for t in self.tracks}),26)
        self.assertEqual(Counter(t["theme"] for t in self.tracks),dict(cathedral=3,cyberpunk=3,space=3,fire=3,crt=3,mono=3,classic=8))
        for track in self.tracks:
            with self.subTest(track=track["id"]):
                path=AUDIO/track["file"]
                self.assertTrue(path.resolve().is_relative_to(AUDIO.resolve()))
                self.assertEqual(path.suffix,".ogg")
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),track["sha256"])
                self.assertEqual(len(track["instruments"]),4)
                self.assertTrue(85<=track["duration"]<=95)
                self.assertGreater(path.stat().st_size,300_000)

    @unittest.skipIf(mido is None,"mido is a production verification dependency")
    def test_actual_midi_has_four_ended_parts_and_section_markers(self):
        for track in self.tracks:
            with self.subTest(track=track["id"]):
                midi=mido.MidiFile(ROOT/track["source_midi"])
                self.assertEqual(len(midi.tracks),5)
                self.assertTrue(85<=midi.length<=90)
                channels=set();markers=[];counts=Counter()
                for part in midi.tracks:
                    pending=Counter();tick=0
                    for msg in part:
                        tick+=msg.time
                        self.assertGreaterEqual(msg.time,0)
                        if msg.type=="marker":markers.append(msg.text)
                        if msg.type=="note_on" and msg.velocity:
                            channels.add(msg.channel);counts[msg.channel]+=1
                            self.assertTrue(24<=msg.note<=108)
                            pending[(msg.channel,msg.note)]+=1
                        elif msg.type=="note_off" or (msg.type=="note_on" and not msg.velocity):
                            self.assertGreater(pending[(msg.channel,msg.note)],0)
                            pending[(msg.channel,msg.note)]-=1
                    self.assertFalse(any(pending.values()))
                    self.assertEqual(part[-1].type,"end_of_track")
                self.assertEqual(channels,{0,1,2,9})
                for channel in channels:self.assertGreater(counts[channel],15)
                self.assertTrue({"intro","theme","contrast","variation","outro"}.issubset(markers))

    def test_authored_themes_are_unique_and_close_on_tonic(self):
        signatures=set()
        for track in self.tracks:
            score=json.loads((PRODUCTION/"scores"/(track["id"]+".json")).read_text(encoding="utf-8"))
            sections=score["sections"]
            self.assertEqual(sections[0]["start_beat"],0)
            self.assertEqual(sections[-1]["end_beat"],score["beats"])
            for left,right in zip(sections,sections[1:]):self.assertEqual(left["end_beat"],right["start_beat"])
            section=next(s for s in sections if s["name"]=="theme")
            melody=[n for n in score["notes"]["lead"] if section["start_beat"]<=n["beat"]<section["end_beat"]]
            signature=tuple((n["pitch"],round(n["duration"],3)) for n in melody)
            self.assertNotIn(signature,signatures);signatures.add(signature)
            if track["theme"]!="classic":
                for s in sections:
                    if s["name"] in ("theme","answer","contrast","variation"):
                        final_bar=int(s["end_beat"]/score["meter"])-1
                        self.assertEqual(score["chords"][final_bar],score["key"],track["id"]+s["name"])
                self.assertNotEqual(score["notes"]["lead"][4:12],score["notes"]["lead"][12:20])

    def test_render_evidence_matches_distributed_bytes_and_targets(self):
        for track in self.tracks:
            report=json.loads((PRODUCTION/"render-reports"/(track["id"]+".json")).read_text(encoding="utf-8"))
            with self.subTest(track=track["id"]):
                self.assertEqual(report["sha256"],track["sha256"])
                self.assertEqual(report["midi_sha256"],hashlib.sha256((ROOT/track["source_midi"]).read_bytes()).hexdigest())
                self.assertEqual((report["sample_rate"],report["channels"]),(44100,2))
                self.assertTrue(-19<=report["lufs"]<=-17)
                self.assertLessEqual(report["true_peak_dbtp"],-1)
                self.assertLess(report["peak"],1)
                self.assertGreater(report["rms"],.01)
                self.assertLess(report["leading_silence_seconds"],1)
                self.assertLessEqual(report["trailing_silence_seconds"],3)
                self.assertGreater(report["stereo_correlation"],-.15)
                self.assertEqual(report["human_listening"],"not performed")

    def test_register_answers_preserve_melodic_intervals(self):
        for track in self.tracks:
            score=json.loads((PRODUCTION/"scores"/(track["id"]+".json")).read_text(encoding="utf-8"))
            parts={s["name"]:s for s in score["sections"]}
            if "answer" not in parts:continue
            def pitches(section):
                return [n["pitch"] for n in score["notes"]["lead"] if section["start_beat"]<=n["beat"]<section["end_beat"]]
            theme=pitches(parts["theme"]);answer=pitches(parts["answer"])
            self.assertEqual(len(theme),len(answer))
            self.assertEqual([b-a for a,b in zip(theme,theme[1:])],[b-a for a,b in zip(answer,answer[1:])],track["id"])

    def test_mozart_pickup_and_bach_original_opening(self):
        mozart=json.loads((PRODUCTION/"scores/classic_rondo_turca.json").read_text(encoding="utf-8"))
        opening=[(n["beat"],n["pitch"]) for n in mozart["notes"]["lead"] if 7<=n["beat"]<=8]
        self.assertEqual(opening,[(7,71),(7.25,69),(7.5,68),(7.75,69),(8,72)])
        bach=json.loads((PRODUCTION/"scores/classic_bach_minuet.json").read_text(encoding="utf-8"))
        opening=[n["pitch"] for n in bach["notes"]["lead"] if 12<=n["beat"]<15]
        self.assertEqual(opening,[74,78,83,78,73,78])

    @unittest.skipIf(miniaudio is None,"miniaudio is required to verify the shipped decoder")
    def test_runtime_decoder_can_decode_every_complete_recording(self):
        for track in self.tracks:
            with self.subTest(track=track["id"]):
                decoded=miniaudio.decode_file(str(AUDIO/track["file"]),output_format=miniaudio.SampleFormat.SIGNED16,nchannels=2,sample_rate=44100)
                self.assertEqual(decoded.nchannels,2)
                self.assertEqual(decoded.sample_rate,44100)
                self.assertAlmostEqual(decoded.num_frames/44100,track["duration"],places=3)
                self.assertGreater(max(decoded.samples),1000)
                self.assertLess(min(decoded.samples),-1000)


if __name__=="__main__":unittest.main()
