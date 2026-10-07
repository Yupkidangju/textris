"""Agent Audio 원본의 어택과 감쇠를 찾아 배포 WAV와 제작 증거를 만든다."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".antigravity/audio-overhaul-20261008/deps"))
import numpy as np

RATE = 44100
PRODUCTION = ROOT / "assets/audio-production/sfx"
RUNTIME = ROOT / "textris/assets/audio"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_audio(path: Path) -> np.ndarray:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ar", str(RATE),
         "-ac", "2", "pipe:1"], check=True, capture_output=True)
    samples = np.frombuffer(result.stdout, dtype="<f4").reshape(-1, 2).copy()
    if len(samples) < RATE // 50 or not np.isfinite(samples).all():
        raise ValueError(f"유효하지 않은 원본: {path}")
    if float(np.max(np.abs(samples))) < 1e-5:
        raise ValueError(f"무음 원본: {path}")
    return samples


def select_event(samples: np.ndarray, minimum: float, maximum: float) -> tuple[int, int, dict]:
    # 파편/성과음은 짧은 틈도 한 사건에 포함한다. 단일 클릭과 같은 창을 쓰면 몸통을 잃는다.
    clustered = minimum >= .3
    block = max(1, round(RATE * (.01 if clustered else .002)))
    power = np.mean(samples.astype(np.float64) ** 2, axis=1)
    padded = np.pad(power, (0, (-len(power)) % block))
    envelope = np.sqrt(padded.reshape(-1, block).mean(axis=1))
    peak_index = int(np.argmax(envelope))
    peak = float(envelope[peak_index])
    threshold = max(peak * (.08 if clustered else .10), 1e-5)
    quiet_blocks = max(1, round((.060 if clustered else .020) * RATE / block))
    if clustered:
        start_block = 0
        for index in range(peak_index - quiet_blocks, -1, -1):
            if np.all(envelope[index:index + quiet_blocks] <= threshold):
                start_block = index + quiet_blocks
                break
    else:
        before = np.flatnonzero(envelope[:peak_index] <= threshold)
        start_block = int(before[-1] + 1) if len(before) else 0
    # 한 사건의 중간 작은 골 때문에 어택을 잘라내지 않도록 최대 12ms 뒤로 확장한다.
    start = max(0, start_block * block - round(RATE * .012))
    end = len(samples)
    for index in range(peak_index + 1, len(envelope) - quiet_blocks):
        if np.all(envelope[index:index + quiet_blocks] <= threshold):
            end = min(len(samples), (index + quiet_blocks) * block + round(RATE * .012))
            break
    minimum_frames = round(minimum * RATE)
    maximum_frames = round(maximum * RATE)
    natural_end = end
    end = min(len(samples), max(start + minimum_frames, min(end, start + maximum_frames)))
    if end - start < minimum_frames:
        start = max(0, end - minimum_frames)
    if not start <= peak_index * block < end:
        # 긴 상승음은 strongest peak를 포함하는 최대 길이 구간으로 이동한다.
        start = max(0, peak_index * block - maximum_frames // 3)
        end = min(len(samples), start + maximum_frames)
    return start, end, {
        "selection": ("strongest 10ms RMS event cluster; 60ms quiet boundary; natural decay boundary"
                      if clustered else "strongest 2ms RMS event; preceding quiet boundary; natural decay boundary"),
        "source_peak_time": round(peak_index * block / RATE, 6),
        "source_event_rms_peak": round(peak, 8),
        "source_natural_end": round(natural_end / RATE, 6),
        "duration_limited": natural_end > end,
    }


def prepare(request: dict) -> tuple[dict, dict]:
    source = ROOT / request["source_file"]
    samples = read_audio(source)
    with wave.open(str(source), "rb") as source_wave:
        source_format = {"sample_rate": source_wave.getframerate(),
                         "channels": source_wave.getnchannels(),
                         "sample_width": source_wave.getsampwidth(),
                         "frames": source_wave.getnframes()}
    start, end, selection = select_event(samples, request["min_duration"], request["max_duration"])
    if "trim_start" in request:
        start = round(request["trim_start"] * RATE)
        end = min(len(samples), round(request["trim_end"] * RATE))
        selection["selection"] = "explicit reviewed source event window"
    result = samples[start:end].astype(np.float64)
    if len(result) == 0:
        raise ValueError(f"빈 어택 구간: {request['id']}")
    # DC 제거와 짧은 양끝 fade로 연결부 클릭을 억제하고 사건의 자연스러운 꼬리는 보존한다.
    result -= np.mean(result, axis=0)
    fade_in = min(round(RATE * .003), len(result) // 4)
    fade_out = min(round(RATE * .010), len(result) // 4)
    result[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    result[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    source_peak = float(np.max(np.abs(result)))
    before_rms = float(np.sqrt(np.mean(result ** 2)))
    input_crest = 20 * float(np.log10(source_peak / max(before_rms, 1e-20)))
    transient_control = request["min_duration"] >= .3 and input_crest > 24
    if transient_control:
        # 드문 파편 피크 하나가 정규화 전체를 지배해 몸통을 묻지 않도록 부드럽게 제한한다.
        threshold = source_peak * .25
        result = np.tanh(result / threshold) * threshold
        source_peak = float(np.max(np.abs(result)))
    peak_target = 10 ** (request["target_peak_db"] / 20)
    scale = peak_target / source_peak
    result *= scale
    pcm = np.rint(np.clip(result, -1, 1) * 32767).astype("<i2")
    target = RUNTIME / "sfx" / f"{request['id']}.wav"
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(pcm.tobytes())
    final = pcm.astype(np.float64) / 32768
    peak = float(np.max(np.abs(final)))
    rms = float(np.sqrt(np.mean(final ** 2)))
    correlation = float(np.corrcoef(final[:, 0], final[:, 1])[0, 1])
    effect = {key: request[key] for key in ("id", "gain", "priority", "cooldown")}
    effect.update(file=f"sfx/{request['id']}.wav", duration=round(len(final) / RATE, 6),
                  sha256=digest(target))
    report = {
        "id": request["id"], "source": request["source_file"], "source_sha256": digest(source),
        "file": str(target.relative_to(ROOT)).replace("\\", "/"),
        "sha256": effect["sha256"], "source_duration": round(len(samples) / RATE, 6),
        "source_format": source_format,
        "source_peak_dbfs": round(20 * float(np.log10(float(np.max(np.abs(samples))))), 3),
        "source_clipped_samples": int(np.count_nonzero(np.abs(samples) >= 32767 / 32768)),
        "trim_start": round(start / RATE, 6), "trim_end": round(end / RATE, 6),
        "duration": effect["duration"], "sample_rate": RATE, "channels": 2, "sample_width": 2,
        "fade_in": round(fade_in / RATE, 6), "fade_out": round(fade_out / RATE, 6),
        "normalization_db": round(20 * float(np.log10(scale)), 3),
        "transient_control": {"enabled": transient_control, "shape": "tanh",
                              "threshold_relative_to_peak": .25,
                              "input_crest_db": round(input_crest, 3)},
        "peak_dbfs": round(20 * float(np.log10(max(peak, 1e-20))), 3),
        "rms_dbfs": round(20 * float(np.log10(max(rms, 1e-20))), 3),
        "dc": [round(float(x), 8) for x in np.mean(final, axis=0)],
        "stereo_correlation": round(correlation, 6),
        "clipped_samples": int(np.count_nonzero(np.abs(pcm.astype(np.int32)) >= 32767)),
        "finite": bool(np.isfinite(final).all()), "first_sample": pcm[0].tolist(),
        "last_sample": pcm[-1].tolist(), "gain": request["gain"],
        "effective_peak_dbfs": round(20 * float(np.log10(max(peak * request["gain"], 1e-20))), 3),
        "listening_verified": False, **selection,
    }
    if rms < .0001 or peak >= .99 or not np.isfinite(correlation):
        raise ValueError(f"기술 검사 실패: {request['id']}: {report}")
    return effect, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partial", action="store_true", help="존재하는 원본만 처리한다")
    arguments = parser.parse_args()
    requests = json.loads((PRODUCTION / "requests.json").read_text(encoding="utf-8"))["effects"]
    effects, reports, missing = [], [], []
    for request in requests:
        if not (ROOT / request["source_file"]).is_file():
            missing.append(request["id"])
            continue
        effect, report = prepare(request)
        effects.append(effect)
        reports.append(report)
    if missing and not arguments.partial:
        raise SystemExit(f"원본 누락: {', '.join(missing)}")
    (RUNTIME / "sfx.json").write_text(json.dumps({"version": 1, "effects": effects}, indent=2) + "\n", encoding="utf-8")
    report = {"version": 1, "generator": "Agent Audio / Stable Audio 3 Medium",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "generation_backend": "local tflite", "expected_count": len(requests),
              "processor_sha256": digest(Path(__file__)),
              "requests_sha256": digest(PRODUCTION / "requests.json"),
              "rebuild_command": "python scripts/prepare_sfx.py",
              "completed_count": len(effects), "missing": missing,
              "listening_verified": False,
              "quality_limit": "Technical metrics and source event selection do not prove prompt adherence or human listening quality.",
              "effects": reports}
    (PRODUCTION / "inspection.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    selected = {request["id"]: request["source_file"] for request in requests}
    inventory = []
    for receipt_path in sorted((PRODUCTION / "receipts").glob("*.json")):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        source_name = receipt["request"]["source_file"]
        source_path = ROOT / source_name
        if not source_path.is_file():
            continue
        with wave.open(str(source_path), "rb") as source_wave:
            inventory.append({"id": receipt["id"], "attempt": receipt["attempt"],
                              "source": source_name, "sha256": digest(source_path),
                              "sample_rate": source_wave.getframerate(),
                              "channels": source_wave.getnchannels(),
                              "sample_width": source_wave.getsampwidth(),
                              "duration": source_wave.getnframes() / source_wave.getframerate(),
                              "selected": selected[receipt["id"]] == source_name,
                              "receipt": f"receipts/{receipt_path.name}"})
    (PRODUCTION / "source_inventory.json").write_text(
        json.dumps({"version": 1, "sources": inventory}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"completed": len(effects), "missing": missing,
                      "total_runtime_seconds": round(sum(x["duration"] for x in effects), 3)}, indent=2))


if __name__ == "__main__":
    main()
