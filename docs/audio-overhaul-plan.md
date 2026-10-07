# TEXTRIS 사운드 전면 개편 — 승인된 구현 기준

작성: 2026-10-08 (Asia/Seoul). 근거: 사용자가 승인·구현 요청한 26곡/30효과음 계획,
AGENTS.md, spec/designs, AI_IMPLEMENTATION_DOC_STANDARD.md, AI_CODING_STANDARD.md.
이번 작업은 기존 미커밋 수정 위에 병합한다. 2026-10-08 후속 사용자 요청으로
완료 후 패키징·커밋·v1.2.0 태그 푸시가 승인됐다. 기존 tag workflow의 Release 빌드도 확인한다.
OS 볼륨은 변경하지 않는다.

## 확정 범위와 제작
- 6테마별 창작 3곡 + 공통 Classic 8곡 = 26곡. 각 85~95초, 약 90초.
- MIDI 발음 채널은 lead/harmony/bass/drums 네 개(1/2/3/10); 템포 메타 트랙은 별도.
  4채널은 4동시음 제한이 아니다. 조성·박자·템포·화성·모티프와 섹션을 먼저 정의한다.
  무작위 음표 및 8초 복제 루프는 사용하지 않는다. 도입/주제/대조/변주/종결을 갖는다.
- 대성당: organ/strings/deep bass/restrained percussion — 장엄함/장미창/천체행진.
  cyberpunk: synth lead/electronic harmony/bass/drums — 네온/추격/야간질주.
  space: soft lead/pad/round bass/light percussion — 궤도/성운/별빛.
  fire: brass or guitar/harmony/strong bass/tight drums — 불씨/용광로/태양.
  crt: retro synth/electric piano/synth bass/electronic drums — 아케이드/스캔/전파.
  mono: piano/strings/acoustic bass/brush drums — 기하/야상/판화.
- Classic: Korobeiniki, Kalinka, Bach French Suite 3 Minuet, Tchaikovsky Trepak,
  Dance of the Sugar Plum Fairy, Dance of the Reed Flutes, Brahms Hungarian Dance 5,
  Mozart Rondo alla Turca. 원전 선율을 새로 편곡하고 출처/이용조건을 기록한다.
- FluidSynth + GeneralUser GS로 제작 단계에서만 렌더. MIDI와 무손실 마스터 보존.
  배포 음악은 44.1kHz stereo Ogg Vorbis q6, 목표 -18 LUFS±1, true peak ≤-1dBTP.
- Agent Audio 30종: ui_move/ui_select/ui_back/ui_toggle/ui_error,
  countdown/go/pause/resume, move/rotate/hold/drop/lock,
  clear_single/clear_double/clear_triple/tetris/tspin/all_clear,
  combo/b2b/fever_start/fever_end, level/danger/win/gameover, boss_hit/boss_break.
  순차 일괄 생성, 원본/receipt 보존, 실제 어택 trim/fade/정규화. 불합격만 제한 재생성.
  성공 조작/상태 진입에만 재생하고 주요 성취가 중복 드롭/착지보다 우선한다.

## 공통 자산 인터페이스
- runtime root: `textris/assets/audio/`. 별도 `music.json`, `sfx.json`은 UTF-8 객체:
  `{"version":1,"tracks":[...]}` / `{"version":1,"effects":[...]}`.
- Track 필수 필드: id, title, theme (`classic` 또는 6 theme ID), file (root 상대경로),
  duration (초), bpm (float), time_signature (`4/4` 등), instruments (4문자열 배열),
  sha256. 선택 composer/source/source_midi/sections 등 제작 provenance는 보존한다.
- Effect 필수 필드: id, file (root 상대경로), duration, gain (0..1), priority (int),
  cooldown (초), sha256. 생성 prompt/receipt/source는 제작 자료에 보존한다.
- production 원본/MIDI/스코어/출처/검사 보고서는 `assets/audio-production/`,
  큰 WAV/FLAC master와 생성 raw WAV는 `.antigravity/audio-overhaul-20261008/production/`에 보존.
  런타임/EXE에는 music/*.ogg, sfx/*.wav, 두 catalog와 필요한 license만 포함한다.
- 라이브러리 miniaudio 1.71은 제품 의존성; mido, FluidSynth, FFmpeg는 제작 도구만 사용.
  기존 프로젝트 내부 의존성과 새 `.antigravity/audio-overhaul-20261008/deps`로 검증한다.

## 재생 및 UI 인터페이스
- Audio(directory,settings), play(name), set_music(bool), close(), status, set_intensity,
  visual_state는 호출 호환성을 유지하되 기존 oscillator는 제품 경로에서 제거한다.
- Audio.catalog: 읽기 전용 track dict 목록. `set_theme(theme)`,
  `audition(track_id, *, playlist=None, shuffle=False, repeat=False)`,
  `set_audition_options(shuffle=None, repeat=None)`, `pause_audition(bool)`,
  `seek_music(delta_seconds)`, `next_track(direction=1)`, `stop_audition()`를 제공한다.
- `music_state` snapshot dict: track_id/title/theme/position/duration/bpm/instruments,
  paused/buffering/mode (`game`/`audition`)/shuffle/repeat/error. UI는 snapshot만 읽는다.
- UI tick의 set_music(bool)는 game 허용 여부만 바꾸고 audition을 덮지 않는다.
  `set_suspended(bool)`는 창 축소의 공통 정지. master mute/music off는 두 모드 모두 적용.
  pause/help/confirm/작은창/off 시 위치 보존; 감상 종료는 audition 정지, 게임 이력 불변.
- miniaudio PCM 스트리밍/믹서: Windows WASAPI 우선 WINMM fallback, 음악1+효과음6.
  디코딩/I/O는 UI 및 장치 callback에서 수행하지 않는다. 큐/버퍼를 제한한다.
  software gain(master×music/sfx), 주요 cue duck, 실패 제한 재시도, 종료 resource 회수.
- 테마/Classic 두 셔플백 + 두 범주를 섞은 쌍으로 1:1, 범주 내 소진 전 반복 금지,
  경계 즉시 반복 금지. 게임 RNG/세이브/리플레이 checksum과 독립적이다.
- 테마 변경은 짧은 fade-out 후 새 eligible pool. 다른 BPM의 곡을 길게 겹치지 않는다.
- settings version1 보존: volume은 master 유지, music_volume=.75/sfx_volume=.85 추가.
- Extras의 마지막 항목 Soundtrack. 위/아래 선택, Enter 재생, Space pause,
  N/P 다음/이전, 좌/우 ±5초, Tab filter(현재테마/Classic/전체), S shuffle, R repeat,
  M master mute, B music, +/- music volume, Esc/Q back. 64×28 스크롤/고정 안내.
  제목/분류/시간/진행/BPM/4악기/오류 표시. 영문 UI, ASCII/모노 유지.

## 구현 순서·책임
1. 본 문서/spec/designs 갱신 → 공통 catalog/API 동결.
2. 병렬 독립 작업: 26곡 작곡/렌더, 30SFX 생성, audio engine/catalog tests,
   Soundtrack/UI/event router/tests. 부모는 의존성/패키징/통합·증거를 담당한다.
3. 음악/SFX 전체 파일과 catalog 검증 후 연결, 기존 회귀 갱신(수치 낮추기 금지).
4. 독립 리뷰 → Windows native + 장곡 26전곡 정상 속도 완주(약39분) + 혼합 부하.
5. EXE/pyz/패키지 staging 검사, no-external-player 실행, 문서/증거 동기화.

## 완료 기준·제약
- MIDI 26개 4발음 채널/종료/음역/화성/섹션, 85~95초, Ogg/마스터 음량/peak/상관/무음.
- SFX 30종 생성 provenance/어택/길이/음량, 실제 사용자 명령/엔진 사건과 대응.
- shuffle balance/repeat/filter, pause/seek/master/bus volumes, corrupt/missing/device failure,
  render/input/game/checksum 불변, 최소창 UI 접근과 저장 이행.
- native Windows endpoint 출력, 26전곡 정상속도 완주, 혼합 부하, 정확한 종료/메모리,
  EXE/pyz source/cat/asset hash 일치. 실제 미실행 검증은 명시한다.
- 악보/수치/출력은 사람 청취 평가를 대신하지 않는다. 가능한 청취 도구가 없으면
  그 범위를 남기고 최종 Soundtrack에서 사용자 감상을 가능하게 한다.
- 음악적 결함은 문서화 후 수정한다. 생성 실패는 절차적 beep로 대체해 완료하지 않는다.
- 비용 서비스/자동 license 수락/OS 음소거 변경을 하지 않는다.
  패키징·커밋·태그 푸시는 모든 완료 게이트 뒤 수행한다.

## 진행 기록
- 2026-10-08: 승인 계획과 인터페이스를 코드 변경 전에 확정했다.
- 악보 독립 검토: 원곡18개의 종지 설계에서 지속된 으뜸음/V 반주 불일치를 찾았고,
  그중 3음 반주를 쓰는 대성당/우주/불꽃 등에서는 실제 인접 반음 충돌이 확인됐다.
  프레이즈 종지의 화음을 실제 종지 선율에 맞추고 미해결 4→3 충돌을 제거한다.
  악보/MIDI 대조·강박 화성 검사를 추가하고 변경 MIDI를 재렌더한 뒤 장곡 검증한다.
- 실제 SoundFont preset 번호/카탈로그 악기명도 대조한다. 대성당 타악기 bank와
  불꽃 기타 program 불일치는 의도한 악기 선택으로 수정하고 재렌더한다.
- 독립 검토에서 음높이 임계값별 octave 이동이 선율의 순차 진행을 8~10반음 도약으로
  바꾼 점을 확인했다. 응답/발전부는 프레이즈 전체 register 이동 또는 명시적 재작곡으로
  처리하며 원전/주제의 선율 윤곽을 음별 조건부 octave 접기로 훼손하지 않는다.
- 장치 생성 도중 실패도 즉시 close/uninit한다. Python 순환 참조 GC를 기다리는
  CFFI context 회수는 WASAPI→WINMM fallback의 정상 정리로 인정하지 않는다.
- 최대 master/music/SFX=1의 합법적 동시 보스 성취에서 실제 PCM clipping이 재현됐다.
  마스터 후단에 envelope를 가진 limiter/headroom을 적용해 hard clamp 왜곡을 방지하고
  최대 설정·실제 배포 SFX 조합을 회귀/실장치 검사한다. 제한 동작과 실제 clipping 통계는 구분한다.
- 배포 검사도 런타임 catalog schema와 정확한30 cue ID를 검증한다. 개수/해시만
  맞고 런타임이 거부하는 bpm/악기/볼륨/ID 메타데이터를 release 통과시키지 않는다.
- 리플레이/분석 하이라이트 seek 뒤 효과음 관측 상태를 복원된 Game.b2b·위험 보드에
  맞춰 재동기화한다. 이전 시점의 B2B/danger/fever를 새 시점의 사건에 남기지 않는다.
- miniaudio의 선택적 NumPy import가 제작용 설치를 따라 EXE에 포함되는 것을 확인했다.
  제품은 array PCM만 사용하므로 PyInstaller에서 NumPy를 제외하고, NumPy 없는
  decoder/PCM 경로를 검증한다. 제작 도구용 NumPy와 게임 의존성은 구분한다.
- 깨끗한 CI checkout에서 없는 `.antigravity`를 전제한 기존 테마 테스트 임시 경로를
  자체 생성되는 TemporaryDirectory로 교체한다. 로컬 증거 디렉터리 유무와 테스트를 분리한다.
