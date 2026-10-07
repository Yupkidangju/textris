# Windows 표시·독립 오디오·전체 테마 상태 점검

작성일: 2026-10-07 (Asia/Seoul). 상태: 점검 완료 / 요구 수준 보완 필요.
대상: TEXTRIS 1.1.0, 시작 HEAD `8fd1671`, 시작 작업 트리 clean.
근거: 사용자의 세 항목 상태 확인 요청, AGENTS.md, spec.md, designs.md,
AI_AUDIT_DOC_STANDARD.md, 현재 소스·테스트·실행 결과.

## 범위와 검증 계획

제품 소스·테스트·설정·사용자 데이터는 변경하지 않는다. 이번 점검에서 생성하는
보고서와 프로젝트 내부의 고유 증거 디렉터리만 쓴다. 기존 감사·캡처는 보존한다.

1. Windows 11 / CP949에서 자동 ASCII 및 명시 Unicode 선택 → 블록·프리뷰·최종 출력까지 추적한다.
2. 오디오를 게임과 분리하여 WAV 신호, 백엔드 선택, 실제 재생 프로세스, 게임 이벤트 연결을 확인한다.
3. 대성당과 다른 다섯 테마의 무대·색상·보호 영역·성취 연출·표시 모드·렌더 비용을 비교한다.
4. 기존 회귀 테스트를 실행하고 실제 장치/폰트 검증과 mock/offscreen 증거를 구분한다.

환경 초기 관찰: Windows 11 build 26200, Python 3.14.3, locale CP949.
시스템 Python에는 `_curses`가 없다. 검증용 windows-curses는 프로젝트 내부의
`.antigravity/audit-20261007-status/deps`에만 설치하며 시스템 Python을 변경하지 않는다.

완료 기준: 세 항목 각각에 현재 상태, 근거, 미확인 범위, 필요한 수정과 재검증 조건을 기록한다.
Windows 10 실기 비교, 사용자의 터미널 프로필/폰트, 배포 EXE 버전 및 물리적 청취는
확인 가능한 증거가 없으면 미확인으로 남긴다. Git 커밋·푸시·배포는 범위 밖이다.

## 결과 요약

| 지적사항 | 현재 상태 | 판단 |
| --- | --- | --- |
| Windows 11에서 타일 대신 `[]` | 실제 재현. Windows 자동 ASCII 모드가 의도적으로 출력하는 문자. `--unicode`의 `██` 출력은 실제 curses에서 정상 | 기본 타일 표시 요구는 미충족. Windows 10/11 차이의 정확한 원인은 미확인 |
| 사운드 없음 | 합성·실재생·게임 이벤트·음악 반복은 작동. 현재 기본 출력 장치는 음소거 true / 볼륨 0% | 엔진 전체 미동작으로 단정할 수 없음. 외부 플레이어 없는 독립 재생은 미구현 |
| 다른 테마가 대성당 수준인가 | 5개 모두 고유 구도와 공통 합성기·보호·팔레트 사용. 이벤트 종류/강도 반응은 대성당보다 제한적 | 배경 업그레이드 확인, 성취 연출까지 동등한 수준은 미충족 |

## Pass 1: 구현과 요구의 정합성

### T1 — Major / Confirmed: Windows 기본 표시와 타일 기대의 차이

- 근거: `textris/terminal.py:6-12`, `textris/ui.py:67`, `:102-103`, `:238`, `:250-265`.
- 현재 계약: Windows는 출력 인코딩이나 Windows 버전에 관계없이 자동 ASCII.
  ASCII 블록은 `[]`, Unicode 블록은 `██`, 고스트는 각각 `::` / `░░`.
- 실제: Windows 11 / CP949 / windows-curses 2.4.2에서 CLI와 실제 curses wrapper를 통과시켰다.
  Codex가 제공한 Windows 콘솔 PTY에서 `App.run`만 유한한 점검 루프로 대체해
  실제 그리기·화면 버퍼 읽기·입력 큐를 검사했다. 이는 사용자의 Windows Terminal
  프로필·폰트의 픽셀 캡처 또는 전체 사람 입력 검증은 아니다.

| CLI 모드 | 실제 모드 | `[]` 수 | `██` 수 | `░░` 수 | 종료 |
| --- | --- | ---: | ---: | ---: | ---: |
| 기본 | ASCII | 24 | 0 | 0 | 0 |
| `--unicode` | Unicode | 0 | 24 | 4 | 0 |
| `--ascii` | ASCII | 24 | 0 | 0 | 0 |

- 세 실행 모두 실제 curses 키 큐의 `a`를 읽고 활성 블록 x=3→2를 확인했다.
  locale CP949, console input CP949, output CP65001, curses encoding CP65001이었다.
- 설정의 `ASCII-safe art=Off`만으로 Windows 자동 ASCII가 해제되지 않는 것도 확인했다.
  저장 설정 false여도 `terminal_ascii=True`이므로 최종 표시 모드는 true이다.
- 해석: `[]` 자체는 인코딩이 깨져 생긴 빈 글리프가 아니다. 코드가 선택한 대체 문자다.
  Windows 10도 같은 코드 분기를 타므로 OS 버전만으로 두 환경 차이를 설명할 수 없다.
  사용자는 두 환경 모두 Windows Terminal / Cascadia Mono이며 EXE도 동일할 것으로
  답했다. 이 정보는 반영하지만 EXE 해시·버전·옵션의 일치까지 확인된 것은 아니다.
  현재 코드의 동일 EXE를 동일 옵션으로 실행했다면 두 OS 모두 ASCII가 되어야 한다.
  따라서 정확한 EXE/실행 옵션과 해당 터미널의 실제 출력 비교는 남아 있다.
- 현재 우회: 소스는 `python -m textris --unicode`, 배포 EXE는 해당 EXE에 `--unicode`를 전달한다.
  이번 출력 성공이 사용자 터미널의 Braille/폰트 호환을 보증하지 않는다.
- 수정 방향: Windows 표시 모드의 자동/ASCII/Unicode 선택을 명확히 하고, 설정에서
  선택한 Unicode와 자동 정책의 우선순위를 문서에 확정한다. 타일 기본 요구에 맞게
  실제 출력 기능을 검증하며 ASCII 대체 경로를 유지한다.
- 재감사: 동일 버전으로 Windows 10/11·한글 locale·실제 폰트별 보드/HOLD/NEXT/메뉴,
  Unicode 선택/설정 저장/인코딩 실패 fallback/레이아웃을 검사한다.
- 증거: [native CLI 결과](../../.antigravity/audit-20261007-status/terminal-probe.json),
  [설정과 native 색상 결과](../../.antigravity/audit-20261007-status/native-palette-probe.json),
  [점검 스크립트](../../.antigravity/audit-20261007-status/terminal_probe.py).

### A1 — Major / Confirmed: Windows 독립 재생 경로가 없음

- 근거: `textris/audio.py:73-84`, `:91`, `:142-148`, `:166-193`.
- 현재: stdlib PCM/WAV 합성 후 PATH의 paplay/aplay/ffplay/afplay 중 하나를 실행한다.
  Windows native 재생/믹서 백엔드는 없으며 외부 플레이어가 없으면 의도적으로 무음이다.
  플레이어 파일은 게임 바이너리 안에 포함되는 구현이 없다.
- 실제 호스트: ffplay 8.1.1이 존재한다. `--audio-check` 종료0을 작업자와 주 점검자가
  서로 다른 프로젝트 내부 데이터 디렉터리에서 확인했다. SDL_AUDIO 환경 override는 없다.
- WAV 14종(효과음10/음악4) 모두 22050Hz·mono·16bit, 비영 PCM 신호와 예상 길이를 확인했다.
  독립 ffplay, Audio 효과음, Audio 음악, UI hard drop→Session→process_events→Audio에서
  기본 출력 endpoint의 신호를 확인했다(각 peak 약 0.2006 / 0.2006 / 0.1779 / 0.2006).
- 음악 11.5초 실행에서 8초 루프의 첫 프로세스가 종료0 후 두 번째 루프를 시작했다.
  pause·mute·volume0·close 후 음악 중단 및 worker/프로세스 회수도 확인했다.
- 기본 출력 장치 **스피커(Senary Audio)**는 master volume **0.0**, mute **true**였다.
  별도 읽기 조회로 재확인했다. 앱 저장 설정은 sound/music=true, volume=.5였다.
  현재 호스트의 무음은 OS 상태로 설명된다. OS 볼륨·음소거는 변경하지 않았다.
- 한계: endpoint 피크는 마스터 볼륨 감쇠 전 측정이므로 청취 성공을 뜻하지 않는다.
  사용자가 실행한 EXE와 현재 소스의 동일성도 확인되지 않았다.
- 수정 방향: 외부 플레이어 설치 없이 작동하는 Windows 재생 백엔드와 효과음/음악
  수명·믹싱·음소거·재시도 계약을 먼저 문서화한다. 기존 외부 백엔드는 선택적으로 유지한다.
  현재 무음 진단은 우선 Windows 출력 장치의 음소거/볼륨 확인이 필요하다.
- 재감사: 외부 플레이어가 없는 깨끗한 Windows에서 효과음·음악·동시재생·정지·종료,
  출력 장치 실패/변경과 실제 청취를 확인한다.
- 증거: [오디오 결과](audio-20261007-6ec14cb99f44/audio-result.json),
  [루프 결과](audio-20261007-6ec14cb99f44/loop-result.json),
  [장치 결과](audio-20261007-6ec14cb99f44/endpoint-name.json).

### V1 — Major / Confirmed: 배경 업그레이드와 성취 연출 동등성의 차이

- 근거: `textris/theme_art.py:15-30`, `:48-174`, `:175-204`,
  `textris/art.py:13-21`, `textris/effects.py:93-105`, `textris/cathedral.py:28-59`, `:181-206`.
- 공통 업그레이드: 6개 테마의 producer→Effects→ThemeScene→ArtCanvas→App.draw 경로가 연결됐다.
  서로 다른 geometry·팔레트, 서브셀·깊이, 보드/HUD 보호와 유한 주 연출을 사용한다.
- 실제 App.draw 60프레임을 새 디렉터리에 캡처했다. 6테마 모두 같은 게임 상태에서
  idle→all clear 시 보드/HUD 문자 불변. 4크기×3표시 모드×6테마의 72개 보호·클리핑·ASCII 계약 통과.

| 테마 | 배경 구현 | 같은 위상의 성취6종 배경 서명 수 | 상태 |
| --- | --- | ---: | --- |
| 대성당 | 아치·장미창·천체 조각·광막 | 5 | 비교 기준 |
| 사이버펑크 | 도시·원근 도로·회전 큐브 | 1 | 배경 완료 / 성취 보강 필요 |
| 우주 | 명암 행성·궤도·천체 고리 | 1 | 배경 완료 / 성취 보강 필요 |
| 불꽃 | 상승 불꽃·코로나·불씨 | 1 | 배경 완료 / 성취 보강 필요 |
| 레트로 CRT | 계측 프레임·곡선·회로·스캔 | 1 | 배경 완료 / 성취 보강 필요 |
| 모노크롬 | 판화 윤곽·간섭 문양·해칭 | 1 | 배경 완료 / 성취 보강 필요 |

- clear/bloom/ascension/victory/eclipse/awakening을 같은 시각·위상 .5·power·coords로 비교했다.
  대성당은 cue.name에 따라 형상을 분기한다. 나머지의 ceremony는 cue.name/power/coords를
  읽지 않아 테마별 한 형상으로 귀결된다. 공통 이벤트 문구·수명은 종류마다 달라진다.
- 섬광 OFF, 동일 이벤트에서 fx_intensity .25→1 및 Cue.power 1→1.6 변경은
  대성당만 배경 서명을 바꿨다. 다른 테마는 강도 임계값에 따른 섬광 색 변화만 있고
  성취 기하·power 반응이 없다. 국소 연출과 보드 흔들림 등 다른 경로의 반응까지 없다는 뜻은 아니다.
- 판단: 서로 다른 배경을 고급 합성기로 올린 작업은 확인되지만, 성취 연출의 구분과
  강도 반응까지 대성당과 같은 수준이라는 주장은 현재 근거로 충족하지 못한다.
- 수정 방향: 각 테마의 삭제·Tetris/T-spin·올 클리어·승리·게임오버·레벨업에 어울리는
  유한 연출과 의미별 변화, 강도/power/좌표 소비를 문서화 후 구현한다.
- 재감사: 동일 상태/시간 비교와 실제 이벤트 producer 경로 모두 검사하고,
  HUD 보호·입력·리플레이 불변·성능·작은 창/ASCII/모노 폴백을 재확인한다.
- 증거: [테마 비교](theme-status-20261007-9c30426f/theme-contact.png),
  [60프레임 HTML](theme-status-20261007-9c30426f/frames.html),
  [원시 계약/성능](theme-status-20261007-9c30426f/runtime-results.json),
  [강도/power 검사](theme-status-20261007-9c30426f/semantic-probes.json).
- 캡처 한계: 현재 HEAD의 대성당과 비교한 offscreen 렌더다. 색상 속성은 ncurses 방식으로
  모의했고 Braille은 셀 마스크를 직접 그렸다. 과거 버전 before/after 또는 실제 터미널 폰트 캡처가 아니다.

## Pass 2: 검증과 진단 품질

### Q1 — Minor / Confirmed: 전체 테스트는 현재 Windows에서 통과하지 않음

검증용 PYTHONPATH는 `.antigravity/audit-20261007-status/deps`이다.

| 명령/검사 | 현재 결과 | 범위 |
| --- | --- | --- |
| CI의 portability 6모듈 명령 | 25/25 통과 | compat/theme/gallery/audio portability/auxiliary/commands |
| terminal_compat + ui + commands | 17개 중16통과/1실패 | Unicode 로고를 기대한 Windows ASCII fixture |
| unittest discover -s . | 113개 중105통과/4실패/4오류, 종료1 | 전체 Windows 실행은 green 아님 |
| theme 관련 대상31개 | 30통과/1실패 | native A_COLOR와 Linux 모의 비트의 차이 |
| audio portability + services | 15개 중13통과/2오류 | symlink 생성 권한 실패 |
| 실제 curses CLI·모드·입력 | 기본/Unicode/ASCII 모두 종료0 | 유한 점검 루프 / 실제 wrapper·buffer·입력 큐 |

- 4오류: termios 없는 Unix 전용 test_terminal 모듈1, WinError1314 symlink 준비 실패3.
- 4실패: 기본 Windows ASCII인데 Unicode를 기대하는 로고/Braille/넓은 문자 테스트3,
  curses.color_pair를 Linux의 `n<<8`로 모의하면서 native Windows A_COLOR를 쓰는 테스트1.
- 실제 PDCurses A_COLOR=-16777216, color_pair(1)=16777216, color_pair(2)=33554432.
  별도 native Palette(8,8) 검사에서 I/O 색상 identity가 정상임을 확인했다.
  실패한 mock 테스트만으로 제품 색상 결함을 주장하지 않는다.
- 수정 방향/재감사: fixture에 표시 모드를 명시하고 native attribute 또는 일관된 mock을 쓴다.
  Unix 전용 PTY와 Windows 실제 콘솔 검증을 분리하고 symlink 권한 가용성을 명시한다.
  검사 제외를 통해 전체 플랫폼 검증이 완료된 것처럼 보고하지 않는다.
- 원시 로그: [전체 테스트](../../.antigravity/audit-20261007-status/unittest-discover.log).

### A2 — Minor / Open: 짧은 효과음 출력과 진단 성공의 한계

- 실제 Audio 효과음10종 모두 재생 프로세스 종료0. 9종의 장치 peak는 .0438~.2006.
  move(35ms)는 WAV가 정상인데 peak .0000305만 관측돼 정상 출력은 확정하지 못했다.
  짧은 WAV의 ffplay 종료/드레인 문제는 가설이며 원인 확정은 아니다.
- `textris/__main__.py:47-55`의 audio-check는 플레이어 종료0으로 성공한다.
  `textris/ui.py:216-219`는 앱 설정/백엔드 상태를 표시하므로 OS 음소거·볼륨0을 알려주지 않는다.
  현행 문서의 재생 검사 성공을 실제 청취 성공으로 읽으면 오해가 생긴다.
- 수정 방향/재감사: 짧은 효과음의 실제 출력 신호/청취를 재검사하고, 진단에서
  백엔드 성공·앱 음소거·OS 출력 상태·청취 여부를 명확히 구분한다.
- 증거: [효과음별 결과](audio-20261007-6ec14cb99f44/all-effects-result.json).

### 새 렌더 비용 측정

120×40, 명시 Unicode·색상 모의, 실제 App.draw 240프레임/테마. 터미널 전송 제외.

| 테마 | 평균 ms | p95 ms | 최대 ms |
| --- | ---: | ---: | ---: |
| 대성당 | 8.046 | 11.972 | 54.779 |
| 사이버펑크 | 6.560 | 9.823 | 73.197 |
| 우주 | 6.470 | 9.460 | 118.541 |
| 불꽃 | 5.416 | 9.269 | 10.655 |
| CRT | 6.784 | 9.737 | 169.467 |
| 모노크롬 | 3.760 | 8.563 | 9.678 |

이번 p95는 모두 16.7ms 미만이다. 일부 최대 프레임은 초과하며 전 환경 60FPS 보장이 아니다.
기존 Linux 문서의 모노 p95 18.91ms는 과거 환경의 측정이다. 이번 수치로 당시 기록을 덮지 않는다.

## Pass 3: 저장·프로세스 경계

선택된 범위에서 새 보안 결함은 확인하지 않았다. 프로젝트 기존 자료를 보존하고
새 증거 디렉터리와 격리 의존성만 생성했다. 오디오 실제 프로세스는 검사 종료 시 회수했다.
symlink 보안 테스트3개는 현재 권한에서 준비하지 못했으므로 보안 경계 전체 PASS는 주장하지 않는다.
제품 소스·기존 테스트·설정·사용자 데이터·OS 볼륨은 변경하지 않았다.

## 충돌·제외·미확정

- 기존 Windows ASCII 정책과 사용자의 타일 기대를 T1에 명시했다. 기존 정책을 임의 변경하지 않았다.
- 외부 플레이어 기반이라는 현행 spec은 충족하지만, 외부 재생기 없는 독립 동작은 A1에서 미충족으로 구분했다.
- 전체 테마 공통 합성은 충족하지만 성취별 표현 동등성은 V1에서 구분했다.
- 제외: Windows 10 실기, 사용자의 정확한 EXE/실행 옵션·터미널 프로필·폰트,
  실제 사람 청취, 배포 바이너리 재빌드·게시, 전체 보안 감사, 장시간 부하 및 터미널 전송 성능.
- 사용자 회신: Windows Terminal, 두 OS 모두 Cascadia Mono, EXE는 동일할 것으로 추정.
  확인된 사용자 정보와 달리 정확한 EXE 해시·버전·실행 옵션·Windows 10 실기 출력은 미확인이다.
- 이 감사는 상태 확인이며 수정 요청을 완료했다고 표현하지 않는다.

## 최종 판단과 재감사 조건

점검은 완료했다. 세 요구를 모두 충족하는 품질 판단은 **HOLD / 보완 필요**다.
T1의 표시 선택, A1의 독립 재생, V1의 성취 연출을 구현한 뒤 위 재감사 조건을 실행한다.
현재 OS 음소거를 해제한 실제 청취와 사용자의 실행 환경 비교도 남아 있다.
변경 파일은 이 보고서와 새 감사 증거뿐이며, 커밋·푸시·태그·릴리스는 수행하지 않았다.

## 참고한 공식 자료

- [windows-curses 공식 저장소](https://github.com/zephyrproject-rtos/windows-curses): wide-character/UTF-8 지원과 Windows 의존성.
- [Microsoft Console Code Pages](https://learn.microsoft.com/en-us/windows/console/console-code-pages): 콘솔 input/output 코드페이지 경계.
- [Microsoft IAudioMeterInformation](https://learn.microsoft.com/en-us/windows/win32/api/endpointvolume/nn-endpointvolume-iaudiometerinformation): 피크는 마스터 볼륨 감쇠 전 측정.
- [Microsoft GetMute](https://learn.microsoft.com/en-us/windows/win32/api/endpointvolume/nf-endpointvolume-iaudioendpointvolume-getmute): endpoint 음소거 상태의 의미.

## Coder Handoff

`C:\LocalDev\python\textris\docs\audit\audit_report_2.md`의 T1/A1/V1/Q1/A2를
현재 프로젝트 문서와 실제 코드에 대조하여 검토한다. 표시 정책·독립 재생·테마별 성취
연출의 설계와 검증 기준을 먼저 문서화하고 필요한 수정 및 Windows 실제 재검증을 수행한다.
기존 감사 증거·사용자 기록·OS 설정을 보존하고 확인하지 못한 범위를 완료로 보고하지 않는다.
