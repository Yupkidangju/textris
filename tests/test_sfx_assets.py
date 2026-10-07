"""배포 효과음의 파일 계약, 제작 출처, 음량과 경계 안전성을 검증한다."""
from array import array
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "textris/assets/audio"
PRODUCTION = ROOT / "assets/audio-production/sfx"
EXPECTED_IDS = {
    "ui_move", "ui_select", "ui_back", "ui_toggle", "ui_error", "countdown", "go",
    "pause", "resume", "move", "rotate", "hold", "drop", "lock", "clear_single",
    "clear_double", "clear_triple", "tetris", "tspin", "all_clear", "combo", "b2b",
    "fever_start", "fever_end", "level", "danger", "win", "gameover", "boss_hit", "boss_break",
}


class SoundEffectAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((AUDIO / "sfx.json").read_text(encoding="utf-8"))
        cls.requests = json.loads((PRODUCTION / "requests.json").read_text(encoding="utf-8"))
        cls.inspection = json.loads((PRODUCTION / "inspection.json").read_text(encoding="utf-8"))

    def test_complete_catalog_is_unique_and_only_uses_local_relative_files(self):
        self.assertEqual(self.catalog["version"], 1)
        effects = self.catalog["effects"]
        self.assertEqual(len(effects), len(EXPECTED_IDS))
        self.assertEqual({item["id"] for item in effects}, EXPECTED_IDS)
        self.assertEqual({item["id"] for item in self.requests["effects"]}, EXPECTED_IDS)
        self.assertEqual(len({item["sha256"] for item in effects}), len(EXPECTED_IDS))
        for effect in effects:
            with self.subTest(effect=effect["id"]):
                self.assertEqual(effect["file"], f"sfx/{effect['id']}.wav")
                self.assertTrue((AUDIO / effect["file"]).resolve().is_relative_to(AUDIO.resolve()))
                self.assertIsInstance(effect["priority"], int)
                self.assertGreaterEqual(effect["cooldown"], 0)
                self.assertGreater(effect["gain"], 0)
                self.assertLessEqual(effect["gain"], 1)

    def test_wav_bytes_match_catalog_and_are_audible_without_clipping_or_boundary_clicks(self):
        requests = {item["id"]: item for item in self.requests["effects"]}
        for effect in self.catalog["effects"]:
            with self.subTest(effect=effect["id"]):
                path = AUDIO / effect["file"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), effect["sha256"])
                with wave.open(str(path), "rb") as source:
                    self.assertEqual(source.getframerate(), 44100)
                    self.assertEqual(source.getnchannels(), 2)
                    self.assertEqual(source.getsampwidth(), 2)
                    self.assertEqual(source.getcomptype(), "NONE")
                    frames = source.getnframes()
                    pcm = array("h", source.readframes(frames))
                if sys.byteorder != "little":
                    pcm.byteswap()
                self.assertAlmostEqual(frames / 44100, effect["duration"], places=5)
                self.assertGreaterEqual(effect["duration"], requests[effect["id"]]["min_duration"] - .0001)
                self.assertLessEqual(effect["duration"], requests[effect["id"]]["max_duration"] + .0001)
                self.assertEqual(list(pcm[:2]), [0, 0])
                self.assertEqual(list(pcm[-2:]), [0, 0])
                peak = max(abs(value) for value in pcm) / 32768
                rms = math.sqrt(sum(value * value for value in pcm) / len(pcm)) / 32768
                self.assertLess(peak, .9)
                self.assertGreater(rms, .0001)
                self.assertAlmostEqual(20 * math.log10(peak), requests[effect["id"]]["target_peak_db"], delta=.02)

    def test_every_effect_has_successful_generator_receipt_and_inspection(self):
        self.assertEqual(self.inspection["processor_sha256"], hashlib.sha256((ROOT / "scripts/prepare_sfx.py").read_bytes()).hexdigest())
        self.assertEqual(self.inspection["requests_sha256"], hashlib.sha256((PRODUCTION / "requests.json").read_bytes()).hexdigest())
        self.assertEqual(self.inspection["expected_count"], 30)
        self.assertEqual(self.inspection["completed_count"], 30)
        self.assertEqual(self.inspection["missing"], [])
        self.assertFalse(self.inspection["listening_verified"])
        inspections = {item["id"]: item for item in self.inspection["effects"]}
        self.assertEqual(set(inspections), EXPECTED_IDS)
        self.assertEqual(len({item["source_sha256"] for item in inspections.values()}), 30)
        for request in self.requests["effects"]:
            with self.subTest(effect=request["id"]):
                receipts = list((PRODUCTION / "receipts").glob(f"{request['id']}-*.json"))
                matching = []
                for path in receipts:
                    receipt = json.loads(path.read_text(encoding="utf-8"))
                    if receipt["request"]["source_file"] == request["source_file"]:
                        matching.append(receipt)
                self.assertEqual(len(matching), 1)
                receipt = matching[0]
                self.assertFalse(receipt["result"].get("isError", False))
                self.assertEqual(receipt["request"]["prompt"], request["prompt"])
                self.assertEqual(receipt["request"]["seconds"], 3)
                returned_path = receipt["result"]["structuredContent"]["result"].replace("\\", "/")
                self.assertTrue(returned_path.endswith(request["source_file"]))
                self.assertIn("no voice", request["prompt"].lower())
                self.assertIn("no music", request["prompt"].lower())
                inspection = inspections[request["id"]]
                self.assertEqual(inspection["source"], request["source_file"])
                effect = next(item for item in self.catalog["effects"] if item["id"] == request["id"])
                self.assertEqual(inspection["sha256"], effect["sha256"])
                for field in ("gain", "priority", "cooldown"):
                    self.assertEqual(effect[field], request[field])
                self.assertEqual(len(inspection["source_sha256"]), 64)
                self.assertGreaterEqual(inspection["trim_start"], 0)
                self.assertLessEqual(inspection["trim_end"], inspection["source_duration"])
                self.assertEqual(inspection["clipped_samples"], 0)
                self.assertTrue(inspection["finite"])
                self.assertGreaterEqual(inspection["fade_in"], .0029)
                self.assertLessEqual(inspection["fade_out"], .012)
                self.assertFalse(inspection["listening_verified"])

    def test_source_inventory_preserves_discarded_candidates_and_bounded_attempts(self):
        inventory = json.loads((PRODUCTION / "source_inventory.json").read_text(encoding="utf-8"))["sources"]
        self.assertEqual({item["id"] for item in inventory}, EXPECTED_IDS)
        selected = [item for item in inventory if item["selected"]]
        self.assertEqual(len(selected), 30)
        self.assertEqual(len({item["sha256"] for item in inventory}), len(inventory))
        for item in inventory:
            with self.subTest(effect=item["id"], attempt=item["attempt"]):
                self.assertIn(item["attempt"], (1, 2))
                self.assertEqual(item["duration"], 3)
                self.assertTrue((PRODUCTION / item["receipt"]).is_file())
        for effect_id in EXPECTED_IDS:
            self.assertLessEqual(sum(item["id"] == effect_id for item in inventory), 2)


if __name__ == "__main__":
    unittest.main()
