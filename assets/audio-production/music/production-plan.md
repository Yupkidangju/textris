# 26곡 편곡 제작 기록

작성: 2026-10-08. 기준: `docs/audio-overhaul-plan.md`.

창작 18곡은 각각 고정 조성, 화성 진행, 두 독립 주제와 변주를 갖는 악보를 작성한다.
발음 트랙은 lead/harmony/bass/drums, MIDI 채널은 1/2/3/10이다. 섹션별 밀도,
다이내믹, 종지와 반주 형태를 바꾸며 무작위 음표와 오디오 루프 복제는 쓰지 않는다.
클래식은 아래 출처의 선율을 보존한 발췌 편곡이며 원곡 전체 연주라는 뜻은 아니다.

## 출처
- Bach BWV 814 Menuet: Mutopia #100, Knute Snortum. Bach-Gesellschaft 1863 원본,
  디지털 판본 CC BY-SA 4.0. 해당 MIDI/편곡/녹음은 CC BY-SA 4.0로 명시한다.
- Mozart KV331 Rondo alla Turca: Mutopia #108, Rune Zedeler / Chris Sawer,
  디지털 판본 public domain. 원전 상성부/저성부를 사용한다.
- Tchaikovsky Op.71a: 작곡가 피아노 편곡, Jurgenson 1892 / Rahter 1898,
  IMSLP #57454 public domain. Trepak 및 Mirlitons 주제를 직접 전사한다.
- Sugar Plum Fairy: 같은 작곡가 원전 13쪽의 선율을 직접 전사하여 celesta로 편곡한다.
  검토 초기에 받은 2023 flute arrangement MIDI는 제작 입력에서 제외한다.
- Korobeiniki: 전통 선율, Jack Campin Nine-Note Tunebook 판본을 대조한다.
- Kalinka: Ivan Larionov (1830–1889), John Chambers ABC 판본을 대조한다.
- Brahms Hungarian Dance 5: 19세기 원전 공개 악보와 도입/대조 선율을 대조한다.

## 제작 및 검증
`scripts/compose_soundtrack.py`가 악보 JSON과 MIDI를 만든다.
`scripts/render_soundtrack.py`가 FluidSynth 2.6.1 / GeneralUser GS 2.0.3으로 렌더하고
FFmpeg 2-pass loudnorm으로 -18 LUFS, true peak -1.5 dBTP 여유를 둔다.
44.1 kHz stereo Ogg Vorbis q6과 FLAC master를 보존하고 최종 Ogg를 다시 측정한다.
MIDI 발음 종료/음역/섹션/출처/네 채널, 음원 길이/해시/음량/peak/무음/스테레오를 검사한다.
사람 청취 평가는 자동 신호 분석 결과에 포함하지 않는다.

GeneralUser GS upstream은 음악 제작을 허용하지만 오래된 일부 샘플의 원래 출처가
완전히 확인되지 않는다는 한계를 자체 license에 밝힌다. 원문을 함께 보존한다.

## 독립 악보 검토 수정 (2026-10-08)
- 창작 A/B 마지막 긴 으뜸음과 반주 V가 충돌하던 종지를 I/i로 해결한다.
  Rose Window의 단음계 7음과 장조 V의 반음 충돌은 bVII–i 모달 종지로 바꾼다.
- 응답/변주의 음역 변경은 음표별 임계치가 아닌 구절 전체의 옥타브 이동을 사용한다.
  긴 음표를 짧은 원음/상옥타브 답으로 나누는 변주는 일관된 12반음 규칙을 사용한다.
- Cathedral drum preset을 실제 Orchestral 48, Fire guitar를 Overdriven 29로 맞춘다.
- 원래 짧은 경과음·전타음은 자동 양자화하지 않고, 원전 선율은 그대로 유지한다.
  변경 전 렌더와 악보는 프로젝트 로컬 revision archive에 보존한다.
- Mozart 원전의 1박 못갖춘마디는 intro 마지막 박에 두고, 원전 첫 온마디의
  강박을 반주/타악 강박과 일치시킨다. 이후 발췌 경계도 온마디에 맞춘다.
- Reed Flutes는 각 시스템의 오선 기준으로 6–18마디 음고·32분음표를 다시 읽어
  수정했다. Brahms B의 9–16마디를 원전 음역으로 복원하고, Trepak B에는
  원전 중간부의 여덟 마디 엇박 주제를 사용한다.
- Sugar Plum의 반음계 선율에 맞춰 B→Bm, A→Am 등 필요한 화음을 마디 안에서
  바꾸어 긴 장/단3도 충돌을 해소했다. 원전 선율은 반주에 맞추어 양자화하지 않았다.

## 최종 제작 검증
- 26곡 (창작18 + Classic8), 각각90.000초, 총39분. Ogg44.1kHz/stereo/q6.
- 최종 LUFS -18.03~-17.96, 최대 true peak -2.33dBTP.
- `python -m unittest tests.test_music_assets -v`: 7/7 통과. MIDI의 실제 네 채널,
  모든 note-off, 섹션/종지/일관된 선율 간격, Mozart pickup, 전체26곡 runtime decode,
  source MIDI→report→Ogg→catalog 해시를 검사했다.
- 별도 악보 검토자가 26/26 MIDI/JSON 일치와 MIDI/FLAC/Ogg/catalog 해시를 재확인했다.
  확인한 원전 악보 표본에서 추가 확정 결함은 발견하지 않았다. 이 검토는 원전 전체를
  독립 재입력하여 diff한 전수 음악학 검증은 아니다.
- 최종 catalog SHA256: `d72a186d8124afa44e860f13de4880500939ecc1d6706df75defc17bf6828c17`.
  상세 수치: `validation-summary.json`, 개별 최종 신호: `render-reports/*.json`.
- 사람 청취 평가는 수행하지 않았다. Windows 실제 재생/39분 정상속도 soak 및
  패키지 검증은 부모 통합 작업의 별도 증거에 따른다.
