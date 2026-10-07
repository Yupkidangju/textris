# 음악 제작 재현

작성: 2026-10-08. 승인 기준: `docs/audio-overhaul-plan.md`.

`scores/*.json`은 26곡의 조성, 박자, 악기, BPM, 화성, 섹션, 모든 노트의
onset/duration/pitch/velocity를 보존한다. `midi/*.mid`는 각 JSON과 대응하는
conductor + lead/harmony/bass/drums 트랙이다. 실제 발음 채널은 1/2/3/10이다.

```powershell
$env:PYTHONPATH='.antigravity/audio-overhaul-20261008/deps'
python scripts/compose_soundtrack.py
python scripts/render_soundtrack.py --jobs 2
python -m unittest tests.test_music_assets -v
```

제작 의존성: Python, mido1.3.3, NumPy, FluidSynth2.6.1, GeneralUser GS2.0.3,
FFmpeg/libvorbis. 정확한 파일 해시는 `provenance.json`을 참조한다.
기본 제작 도구 경로는 `.antigravity/audio-overhaul-20261008/`이며 다른 환경은
렌더 스크립트의 `--fluidsynth` / `--soundfont` 옵션으로 지정한다.

렌더는 원시 WAV → high/low-pass 및 짧은 양끝 fade → 측정된 2-pass loudnorm →
FLAC master → Ogg q6 순서이다. 원시/준비 WAV와 무손실 master는 프로젝트 로컬
`.antigravity/audio-overhaul-20261008/production/masters`에 남는다.
`render-reports/*.json`은 최종 Ogg의 실제 디코딩 결과를 측정한다.
음압, true peak, peak/RMS, 스테레오 상관, 앞뒤 무음, 대역별 에너지를 기록한다.

`catalog-pending.json`은 제작 입력이다. 게임이 읽는 `textris/assets/audio/music.json`은
인코딩·측정 게이트가 성공한 후에만 갱신된다. MIDI를 수정한 후 재렌더하지 않으면
해시 정합성 테스트가 실패한다. 해시를 바꾸어 그 실패를 숨기지 않는다.

출처와 트랙별 이용 조건은 `ATTRIBUTION.md`를 참조한다. 원곡 전체 공연 녹음이
아닌 새 발췌 편곡이며, 청취 심미 평가는 자동 분석으로 대체하지 않는다.
