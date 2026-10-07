# TEXTRIS 1.2.0 사운드 개편 검증

작성: 2026-10-08 (Asia/Seoul). 근거: 승인된 `audio-overhaul-plan.md`, 실제 코드·음원·
Windows 실행 결과. 기존 감사2 수정과 증거를 보존하고 그 위에 사운드를 확장했다.
현재 상태: 구현·자산·단위·실제 Windows UI/장치 재생·패키지 검증 완료.
원격 플랫폼 CI와 태그 릴리스는 문서 끝의 GitHub 실행 기록을 기준으로 확인한다.

## 제작 결과와 범위

- 테마별 창작18곡 + Classic8곡 =26곡. 각90.000초, 총2340초(39분).
  4 MIDI 발음채널(lead/harmony/bass/drums), 별도 템포/섹션 메타 트랙.
- MIDI26개, 악보JSON26개, FLAC마스터26개, Ogg26개, 개별검사26개와 출처를 보존했다.
  배포음악44.1kHz stereo Vorbis q6, 45,234,782bytes.
  측정 loudness -18.03~-17.96 LUFS, 모든 true peak≤-2.33dBTP.
- Agent Audio / Stable Audio3 Medium / local TFLite로30효과음 제작.
  총32번 생성(콤보/피버종료만 각1회 추가). 원본/요청/영수증/해시를 보존했다.
  배포PCM16 stereo44100Hz, 총14.480초/2,555,672bytes, 30/30 decode, clipping0.
- 원본 마스터/생성 WAV는 `.antigravity/audio-overhaul-20261008/production/`,
  MIDI/스코어/출처/제작보고서는 `assets/audio-production/`, 게임용은 `textris/assets/audio/`.
- 모든 곡을 단순무작위 음표/짧은오디오loop복제로 만들지 않았다. 원곡주제/대조/응답/
  변주/종결을 갖고 원전 선율을 새4파트로 편곡했다. 클래식은90초 발췌 편곡이다.

제작 근거: [음악 결과](../assets/audio-production/music/validation-summary.json),
[효과음 결과](../assets/audio-production/sfx/validation.json).

## 음악적 검토와 수정

독립 검토에서 다음을 발견해 스코어/MIDI를 수정하고 재렌더했다.

- 지속된 으뜸음과 V 반주의 미해결 충돌: 프레이즈 종지는 tonic, 도입은 별도 dominant로 수정.
- 음별 octave 임계치로 생긴8~10반음 역방향 도약: 프레이즈 단위 register 이동으로 수정.
- 대성당 타악기와 불꽃 기타 program/이름 불일치: 실제 SoundFont preset48/29와 일치.
- Mozart 못갖춘마디: intro마지막박7에 pickup, beat8에 원전첫강박/저음/타악을 정렬.
- Reed Flutes 음높이/32분음표, Brahms대조부, Trepak오프비트구간을 원전시각표본과 대조.

재검토에서26개JSON과MIDI의 음·시간·세기가 일치했고, MIDI→render보고서→FLAC→Ogg→
catalog 해시 연결을 독립 확인했다. 독립검토 범위에서 남은 구체적 악보 결함을 찾지 못했다.
이것은 사람 청취나 음색/감상 수용을 대신하지 않는다. 원전 대조도 전악보 독립재채보가 아닌
핵심 구간의 시각적 표본 검토다. 청취 성공을 수치 결과로 주장하지 않는다.

## 재생·화면 변경

- miniaudio1.71, Windows WASAPI 우선/WINMM fallback, 외부재생기 없음.
- 음악1곡 스트리밍 + SFX최대6voice, master/music/SFX gain, 성취duck,
  0.87ceiling limiter(5ms buffer내lookahead/80msrelease).
- 두 범주의 independent shuffle bag으로 테마/Classic1:1, 범주 소진전 반복 및 경계연속반복 방지.
- pause/help/confirm/작은창/mute는 음악 위치 보존. seek·곡변경·테마변경·실패건너뛰기 지원.
- Extras Soundtrack의26곡 필터/스크롤/재생/탐색/셔플/반복/볼륨/메타데이터.
- 기존 settings version1 유지, music_volume=.75/sfx_volume=.85 추가; 게임 RNG와 독립.

콜백에는 파일I/O/디코딩을 두지 않았다. 음악8×2048frame PCM(약128KiB),
SFX캐시32MiB, 요청24개, 제어명령32개, 효과음8초 상한,
zip추출캐시128MiB/64파일/개별24MiB, 장치실패3회 및2초콜백정지감시로 경계를 둔다.

## 발견 후 수정한 구현 문제

1. 장치 생성 실패가 순환참조GC 전까지 native context를 보유함 → 즉시close/uninit 검증.
2. maxgain합법적보스성취 중첩 hardclipping → limiter추가. 실제배포PCM4위치검사에서
   true peak -1.13~-1.14dBTP, post-output clipping0. 경계 gain 점프도 측정했다.
3. zipcache용량초과 시 새파일잔존 → rollback; 잠긴기존파일 실패주입으로 검증.
4. 배포검사가 개수/해시만보고 잘못된BPM/누락cueID를 통과 → 런타임schema/정확한30ID 검사공유.
5. replay/analysis seek가 이전B2B/danger/fever관측을 유지 → 복원Game상태로 재동기화.
6. 깨끗한 checkout에 없는 `.antigravity`를 전제한테마test → 자체생성TemporaryDirectory.
   격리한clean복사본에서RED(FileNotFoundError)→GREEN을 확인했다.

## 현재 확인된 검사

| 검사 | 결과 | 근거 |
| --- | --- | --- |
| 전체 Windows unittest discover |217개 중207PASS/10명시skip, 종료0 |[전체로그](audio-evidence/unit-tests.log) |
| 음악자산/MIDI/전곡decode |7/7PASS,26/26decode |assets/audio-production/music/validation-summary.json |
| SFX자산 |4/4PASS,30/30decode |assets/audio-production/sfx/validation.json |
| schema/패키지 gate |5/5PASS,잘못된BPM/ID RED→GREEN |[로그](../.antigravity/audio-overhaul-20261008/package-schema-green.log) |
| maxgain실배포PCM혼합 |4위치 모두TP≤-1,clipping0 |[독립측정](audio-evidence/max-gain-mix.json) |
| 실제 Windows Soundtrack UI |4/4PASS,13전이/case |[native UI](audio-evidence/native-soundtrack-ui.json) |
| 실제 게임 입력과 장치 효과음 |5/5PASS, 각7~12효과음 완료 |[게임 오디오](audio-evidence/native-game-audio.json) |
| 600초 실제 음악/SFX 혼합 |7247요청, 최대6voice, 실패/underrun/clipping0 |[혼합 결과](audio-evidence/native-mixed.json) |
| 새 EXE 실제 오디오 |WASAPI 완료, exit0, PATH/PYTHONPATH 비움 |[진단 출력](audio-evidence/exe-audio.log) |
| 새 EXE 실제 감상·게임·종료 |Soundtrack Playing, 게임 조작/PAUSED/Q→Y, exit0 |[종료 결과](audio-evidence/exe-live.json) |
| 패키지 EXE/pyz/wheel |63runtime파일 및 hash일치 |[archive검사](audio-evidence/package-archive.json) |
| PATH/PYTHONPATH없는EXE진단 |6회 모두exit0 |[실행측정](audio-evidence/package-launch.json) |
| 고정runtime의존성audit |알려진취약점0 |[결과](audio-evidence/dependency-audit.json) |

10skip은 Unix PTY6개 및 Windows symlink권한4개다. 별도 실제Windows junction2개는 통과했다.
로컬프로젝트 자체는 dependency advisory대상이 아니어서 -e 항목에서제외됐고,
cffi2.1.1/miniaudio1.71/pycparser3.0/windows-curses2.4.2를 검사했다.

실제UI는64×28/120×40 ×ASCII/모노에서 App.run/handle/tick과Audio를 교체하지 않았다.
PDCurses의unget_wch/ungetch(KEY_UP)이str U+0103을 반환한 검사도구문제를 확인하고
WriteConsoleInputW의실제KEY_EVENT로 바꿨다. 정수KEY_UP259 반환을 확인했다.
기능키오류는 제품키처리 결함으로 분류하지 않는다. 게임/기록/replay생성없음과 설정저장도 확인했다.

## 패키지와 라이선스

EXE/pyz/wheel에26Ogg+30WAV+2catalog+5notice가포함되고 byte hash가 일치한다.
MIDI/SF2/모델/마스터/NumPy는 runtime에서 제외한다. pyz/wheel의25소스파일과
EXE에서 사용되는24모듈bytecode를 현재소스와 대조했다.
미사용particles모듈은 PyInstaller의 정상 의존성분석으로EXE에포함되지 않는다.

빈PATH의새EXE프로세스 진단은1.226~1.598초, aggregateprocessworking-set표본은약44~48MiB였다.
이는OS cold-cache를비운측정이나게임전체메모리측정이아니다.
BachMinuet자산은CC BY-SA4.0; sourceeditor와변경사항을MUSIC_ATTRIBUTION.txt에보존했다.
GeneralUserGS원문/역사적샘플출처한계, miniaudio/CFFI/pycparser, 프로젝트Apache원문과
SFX생성provenance고지를패키지에포함했다. 모델terms를사용자대신수락하지않았다.

## 최종 게이트

- 실제26곡 정상속도39분 완주: 2339.999초에26곡을 각1회 완료했다. source/catalog가
  전후 일치하고 underrun/device failure/clipping은0, 종료 후worker정리와200msdrain을 확인했다.
  [원본 결과](audio-evidence/native-soak.json)의passed=false/exit1은 보존한다.
  유일한 실패는 OS상태비교다. 시작master100%/unmuted였고, 종료 후 별도조회는39%/unmuted였다.
  [조회 기록](audio-evidence/post-soak-endpoint.json). 앱 소스에는 OS볼륨/음소거 setter가 없으며,
  사용자가 검사 중 Windows 볼륨을 직접 변경했다고 명시적으로 확인했다.
  [환경 변화 해석](audio-evidence/environment-clarification.json)에 사용자 확인과
  재생 기능7항목 통과를 분리해 기록했다. 원본failed표시는 그대로 보존했다.
- 별도 혼합검사는600.036초 동안7247효과음요청, 종료 시5494효과음완료를 확인했다.
  최대6voice, underrun/device failure/invalid sample/clipping0, 종료 후voice/buffer/queue0,
  worker=false였고 이 실행의OS출력상태는 전후같았다.
- 실제게임키입력→오디오는5/5통과했다. 새EXE도 외부플레이어 없이 WASAPI로
  SFX검사를 완료하고, 실제TTY에서 감상→게임조작→일시정지→정상종료를 확인했다.
- source 배포에는 MIDI/스코어/제작 보고서·스크립트를 포함하며 무손실 마스터와 모델은 runtime에서 제외한다.
- 배포 순서는 main 커밋/푸시→플랫폼 CI 확인→v1.2.0 태그 푸시→Release 빌드 확인이다.
  원격 실행 상태는 [Actions](https://github.com/Yupkidangju/textris/actions),
  확정 배포 파일은 [v1.2.0 Release](https://github.com/Yupkidangju/textris/releases/tag/v1.2.0)를 따른다.
- OS음소거/볼륨변경없음. 현재장치실행의OS상태는해당result.json에기록한다.
  이전감사당시의mute=true/volume0을현재상태로재사용하지않는다.
