# TEXTRIS 구현 및 검증 증거

## 사운드 전면 개편 1.2.0 (2026-10-08)

승인 설계는 [사운드 개편 계획](docs/audio-overhaul-plan.md), 최신 증거는
[검증 보고서](docs/audio-overhaul-verification.md)에 있다.

- 테마 창작18곡과 Classic8곡, 각90초의4파트 MIDI/FLAC/Ogg 및 생성형SFX30종을 제작했다.
- miniaudio 스트리밍·1:1 셔플·볼륨/duck/limiter·위치보존과 Extras Soundtrack을 구현했다.
- 독립 악보/코드/패키지 검토에서 찾은 종지·음역·전사·preset·정리·clipping·seek·배포 gate
  문제를 회귀 검증 후 수정했다. 217개 테스트:207통과/10제외(Unix6·symlink권한4).
- 실제 Soundtrack UI4/4, 실제 게임+장치SFX5/5, 26곡39분완주와600초혼합을 확인했다.
  39분검사의OS상태비교 실패는 사용자가 직접Windows볼륨을변경했다고 확인했다.
  원본실패기록과 기능조건통과를 구분해 보존했다. 별도혼합검사의OS상태는불변이었다.
- EXE/pyz/wheel63개runtime파일과소스/bytecode를대조했다. EXE약54.2MiB,
  pyz약44.2MiB,외부재생기없이실제EXE재생·입력·정상종료를확인했다.
- 사람청취에 의한 최종음질수용,물리장치탈착,Windows10실기는 수행했다고 주장하지 않는다.
  사용자는 완료 후패키징·커밋·v1.2.0태그푸시를 승인했다. 원격CI/릴리스상태는검증보고서에남긴다.

## 감사 2 수정 및 Windows 재검증 (2026-10-07)

최신 계약/파일 책임/실행 증거는 [수정 설계](docs/audit/audit_2_remediation_plan.md)와
[재검증 보고서](docs/audit/audit_2_revalidation.md)에 있다. 아래 과거 단계의 환경·결과와 구분한다.

- Windows 자동 Unicode 타일, Auto/Unicode/ASCII 저장 및 CLI 우선순위, version 1 이행.
- stdlib ctypes waveOut 재생: 음악 1+효과음 3, 버퍼 완료·정지·정리, 누적 실패 사건 3회 한도.
  audio-check는 백엔드 완료·앱 설정·OS mute/volume·청취 미확인을 분리한다.
- 다섯 테마의 6성취 형상과 intensity/power/삭제 행 반응. 코어·리플레이 규칙 불변.
- Windows 전체 156개: 147통과/9명시 제외. 실제 콘솔 5시나리오, native 테마108조건,
  실제 오디오25조건 통과. EXE/pyz 빌드 및 실행 검증 완료. Git 커밋/게시 없음.
- OS mute=true/volume0 상태를 보존했다. Windows 10·사용자 폰트·실제 청취·물리 장치
  교체·타 OS/CI·장시간 부하는 미검증이다. symlink 3개 권한 제외와 junction 2개 통과를 구분한다.

작성: 2026-10-07. 근거: spec.md, designs.md, 현재 소스와 테스트 실행 결과.
초기 사용자 요구: 터미널 TUI 테트리스, 텍스트 애니메이션, 사운드, 키보드 조작.

## 모듈과 실행 흐름

| 파일 | 책임 |
| --- | --- |
| textris/engine.py | 7-bag, 블록/충돌/SRS/홀드/드롭, 착지 시간, 점수, 모드 종료 |
| textris/ui.py | curses 렌더링, 메뉴/설정/기록/게임/오버레이, 입력, 텍스트 효과 |
| textris/audio.py | PCM 합성, 오디오 worker, 효과음/음악 프로세스와 벨 fallback |
| textris/storage.py | JSON 검증, 모드별 정렬/상위 10개, 원자 저장, 오류 보호 |
| textris/i18n.py | 한국어/영어 사용자 문자열 |
| textris/__main__.py, run.py | CLI, 저장/오디오 초기화, curses.wrapper와 종료 정리 |
| pyproject.toml | Python 3.10+ 메타데이터와 선택적 textris 설치 진입점 |
| tests/ | 코어, 서비스, UI, 명령, 장기 시뮬레이션 및 실제 PTY 검증 |

CLI → Store.load → Audio worker → curses.wrapper(App.run).
프레임마다 입력 → Game.update(dt) → Event 소비 → 화면/음원 반영.
음원 생성/재생은 worker에서 진행한다. 종료는 Audio.close와 설정 저장 이후
curses.wrapper를 통해 터미널 상태를 복원한다.

## 실제 검증 결과

환경: Linux, Python 3.14.4, TERM=xterm-256color, UTF-8.

- `python3 -m unittest discover -v`: **38개 테스트 통과**, 18.724초.
- `python3 -m compileall -q textris tests run.py`: 종료 코드 0.
- `python3 -m textris --help`, `--version`: 비대화형 환경에서도 정상 출력.
- 대화형 환경 없는 일반 실행: 안내 후 종료 코드 1, 데이터 디렉터리 미생성.
- 실제 PTY: 메뉴→준비→게임, 이동/회전/홀드/드롭, 도움말/정지/재개,
  재시작 승인/취소, 45×12→64×28 리사이즈, 설정/한국어/기록,
  게임오버→저장→재시작, 종료 승인과 ECHO/ICANON 복원.
- 120개 seeded 게임, 1500개 이상 블록 배치: 보드 크기/셀 값/충돌/고스트/레벨 불변조건 유지.
- 음원 11종: 22050Hz/16bit/mono, 양/음 파형과 진폭/길이 검증. 음악 8초 루프.
- 오디오 프로세스 계약 테스트: 음악 정지, 효과음 음소거, 실패 벨 전환,
  worker 종료와 모든 자식 프로세스 종료를 대체 프로세스로 검증.
- `python3 -m textris --audio-check --language en`: aplay 감지, 재생 장치 실패,
  bell fallback 안내와 종료 코드 1. 실제 청취는 이 환경에서 검증하지 못함.
- 실제 80×28 Unicode 화면: docs/terminal-preview.txt.

## 요구별 완료 근거

| 요구 | 구현과 증거 |
| --- | --- |
| 터미널 실행 TUI | curses App, 실제 PTY 화면/정상 종료 및 CLI 테스트 |
| 키보드 조작 | 실제 키 전송 PTY 및 UI dispatcher 테스트, README 키 표 |
| 테트리스 규칙 | engine 테스트: bag, 충돌, I/T floor/wall kicks, 4회 회전, 홀드, 드롭/ghost |
| 점수/레벨/모드 | 1~4줄/T-spin/B2B/combo/all-clear, level, Sprint/Ultra 종료 테스트 |
| 착지 지연 | 이동/회전 reset 최대 15회, O 회전 회귀 테스트 |
| 텍스트 애니메이션 | 타이틀 행 겹침 회귀, drop/clear/입자/배너/만료 UI 테스트, PTY 준비/결과 화면 |
| 사운드/음악 | 합성 WAV 검증, 비동기 lifecycle, 실제 백엔드 실패 전환 검증 |
| 완성된 화면 흐름 | 모든 화면 두 언어/최소 크기 렌더링, pause/help/confirm/resize 시간 정지 |
| 기록/설정 | 왕복/상위 10개/Sprint 시간 정렬, 손상 보존/권한 오류/거대 숫자 필터링, PTY 영구 설정 |
| 종료/안전 | wrapper 터미널 복구, 오디오 종료, 생성 음원 symlink 경계 테스트 |

## 검토와 수정
별도 코드 검토에서 저장 실패 예외, O 회전 lock reset 누락, audio symlink 경계
3개 Important 항목을 찾았다. 모두 재현 테스트를 먼저 실행하고 수정했다.
재검토에서 Critical/Important 잔여 항목이 없음을 확인했다.
추가로 키 입력 직후 gameover를 UI가 playing으로 덮어쓰던 문제와 타이틀 행 겹침을
회귀 테스트로 고정했다. 커밋/푸시/외부 배포는 요청되지 않아 수행하지 않았다.

## 한계 및 가정
- 실제 오디오 장치가 없어 물리적 소리 청취는 미검증. 재생 가능한 장치가 있으면
  --audio-check로 확인한다. 벨 자체도 터미널의 소리/시각 알림 설정에 의존한다.
- Python 3.10~3.13/macOS/WSL에서의 실행은 이 환경에서 직접 검증하지 않았다.
  사용 API는 Python 3.10+ 표준 라이브러리 범위다.
- 키 release 이벤트를 제공하지 않는 터미널 특성상 OS 키 반복을 사용한다.
- T-spin mini/180도 회전은 spec에서 정의하지 않은 규칙이며 제공하지 않는다.
- 설치 없이 프로젝트에서 실행하는 경로를 검증했다. 선택적 pip 패키징 경로는 미검증.

## TUI 연출 확장 검증 (2026-10-07)
근거: 최신 사용자 요구, docs/effects-plan.md, 실제 소스/PTY 출력.

변경 파일: `textris/effects.py`(신규), `textris/ui.py`, `textris/i18n.py`,
`tests/test_effects.py`(신규), `tests/test_terminal.py`, spec/designs/README/CHANGELOG와 계획 문서.

- drop/lock 감쇠 흔들림과 착지 섬광, 타원 충격파, 중력 파편.
- 줄 삭제 셀마다 파편, Tetris/T-spin/B2B/combo/all-clear 강도 증가,
  상승 점수와 5행 대형 문자 아트. 시작/홀드/회전/레벨/패배/승리에도 추가 연출.
- 9초 순환 문자 비/플라스마/별 터널/와이어프레임, 사인파 문자 리본과 색 순환.
- 메뉴 V 쇼케이스는 9종 연출을 1.6초마다 순환. 기록/점수/시간과 독립적.
  F는 추가 효과 토글. Unicode/ASCII, 컬러/모노, 두 언어와 최소 크기를 유지한다.
- 파편 360/충격파 12/상승 문자 8 상한과 수명 만료, 재시작 정리 테스트.
- `python3 -m unittest discover -v`: 44개 통과, 22.548초.
  이후 B2B 충격파 강도를 보강하고 배경 네 종류를 모두 검사하는 테스트를 확장했다.
  최종 재검증 결과는 아래 완료 감사에 기록한다.
- `python3 -m compileall -q textris tests run.py`: 종료 코드 0.
- 실제 PTY에서 메뉴 V → 움직이는 쇼케이스 → F 토글 → 40×12/64×28
  리사이즈 → V 복귀 → Q 정상 종료, 기록이 비어 있는 것과 traceback 부재를 검증.
- 실제 110×36 PTY의 9단계 출력은 `docs/fx-showcase-frames.txt`.
  초기 충격/테트리스 별도 프레임은 `docs/fx-showcase-impact.txt`, `docs/fx-showcase-tetris.txt`.
- 120×40, 파편 최대 부하, 가상 curses window의 120회 렌더링:
  평균 10.55ms/최대 13.64ms. 터미널 전송과 실제 장치 렌더링 비용은 포함하지 않으므로
  모든 터미널에서 60 FPS가 보장된다는 의미는 아니다.

물리적 오디오 청취, 다른 OS의 실행과 선택적 패키징은 기존 환경 제한 그대로다.
추가 외부 의존성, 비용 발생 서비스, 배포, 버전 상승, 커밋은 없다.

### 완료 감사
| 사용자 요구/계약 | 현재 증거 |
| --- | --- |
| 충격과 흔들림 | Effects.trigger/offset의 감쇠 이동, 실제 drop→lock 강도 보존 회귀 테스트 |
| 파괴 효과 | 셀별 중력 파편/확대 충격파, clear storm 상한과 만료 검사, 실제 PTY 삭제 장면 |
| 화려한 텍스트 배경 | 네 배경의 서로 다른 출력 테스트, PTY 화면의 문자 리본/별/색 순환 |
| 다양한 문자 아트 | 5행 글리프, 9단계 쇼케이스 PTY 캡처, VICTORY 마지막 글자 회귀 검사 |
| 플레이 영향 없는 연출 | 엔진 보드/점수 독립성, 게임 정지/리사이즈/재시작 기존 회귀 검사 |
| 감상 가능한 경로 | 메뉴 V 안내, 실제 PTY 입력/움직임/F/복귀/정상 종료/빈 기록 검증 |
| 접근성/호환 표시 | F 토글, ASCII/Unicode/모노/두 언어/최소·큰 화면 경계 검사 |

별도 읽기 전용 코드 검토: Critical/Important 없음. 발견된 Minor 두 건(Y 글리프 누락,
동일 프레임 lock의 drop 흔들림 덮어쓰기)을 실패 회귀 테스트로 재현하고 수정했다.

최종 상태 재검증: `python3 -m unittest discover -q` **46개 통과**, 22.497초.
`python3 -m compileall -q textris tests run.py` 종료 코드 0.
수정 후 실제 PTY 9단계 프레임을 다시 캡처했고 정상 종료 코드 0을 확인했다.
연출 확장 범위의 미완료 항목은 없다.

## 최대 연출·기능 확장 (2026-10-07)

이번 확장은 `docs/maximal-effects-plan.md`의 승인 범위를 구현했다.
위의 4배경/360파편 검증은 이전 단계이며, 현재는 18배경/25효과와600파편 상한이다.
갤러리, 다섯 테마와 영구 프로필, 콤보/피버/위험/음악 반응,
독립 보스 모드, 자동 플레이 전시, 결정적 리플레이와 결과 분석을 제공한다.
메뉴 **E**에서 확장 허브로 들어가며 **V** 쇼케이스와 **F** 효과 토글도 유지한다.

구조:

- `scenes.py`/`particles.py`/`effects.py`: 절차적 배경, 투영 도형, 충돌 파편,
  2×4 Braille 합성, 이벤트 연출과 품질 조절.
- `session.py`: 60Hz 명령/업데이트/보스 승패/분석의 공유 코어.
  관찰 시점과 무관하게 step 경계에서 보스 피해와 승패를 확정한다.
- `replay.py`: 검증, 원자 저장,20개 보존, 체크섬과 checkpoint 기반 탐색.
- `autoplay.py`: 제한 시간으로 나누는 합법 입력 탐색, 게임 규칙이나 순위 변경 없음.
- `expansion_ui.py`/`ui.py`: 새 화면과 공통 문자 캔버스, 최종 span 출력,
  넓은 문자 소유 셀 정리, 기록 한도와 저장 오류 안내.
- `audio.py`/`storage.py`/`i18n.py`:8초 음악/강도 반응, 설정·보스 기록,
  한국어/영어 문자열과 기존version1 저장 호환.

최대 부하120×40,18장면×30프레임(540프레임), 단독 실행 평균 **15.708ms**,
최대 **35.079ms**. 터미널 전송 제외; 순간 초과 시 자동 품질 조절을 적용한다.
재현 결과는 `docs/maximal-fx-performance.json`에 보관한다.
실제 합법 자동 입력의 보스 승리는1646tick(27.43초),18줄이며 리플레이 재검증에 성공했다.
세 기본 모드의 게임 종료도 재생 체크섬 일치를 확인했다.
`docs/maximal-replay-verification.json`에 결과를 보관한다.

실제 PTY에서 최신43장면을 다시 캡처했고 정상 종료0/traceback 부재를 확인했다.
범위별 대응표와 제한은 [완료 검증](docs/maximal-completion-audit.md),
실행 결정과 회귀 내역은 [실행 원장](docs/maximal-effects-progress.md)에 기록했다.

최종 검증: `python3 -m unittest discover -q` **75개 통과**,39.548초.
`python3 -m compileall -q textris tests run.py` 종료0.
승인된 최대 확장 범위의 미완료 항목은 없다.


## 우주 대성당 구현 (2026-10-07)
구현 기준: `docs/cathedral-plan.md`.
- `art.py`: RenderContext, 보호 영역, Braille ArtCanvas, 깊이 합성, Palette.
- `cathedral.py`: 장미창/건축선/천체 조각/광막과 독립 레이어 캐시.
- `art_director.py`: 주 연출 우선순위와 유한한 국소 연출, 게임 시간과 독립.
- `art_ui.py`: 메뉴 문자 조립, 보드 테두리/성취 문구, 화면별 보호 영역.
- 기존 UI/Effects에 cathedral 경로 추가. 저장 테마 검증·번역·CLI·갤러리 연결.
- `tests/test_cathedral.py` 합성/우선순위/수명/보호/폴백/캐시 결정성 검증,
  `tests/capture_cathedral.py` 컬러 프레임 HTML/선택 PNG,
  `tests/benchmark_cathedral.py` 이벤트를 포함한 렌더 비용 측정.
- 성능/시각/PTY 최종 근거는 `docs/cathedral-verification.md`에 기록한다.

## 1.1.0 영문/전체 테마 통합 (2026-10-07 최신 상태)
이 절이 위의 초기 구현 기록 중 언어/벨/렌더링 설명을 대체한다.
제품 UI는 영문 단일, 오디오 실패는 무음, 모든 테마는 공통 ArtUI/ArtCanvas/ArtDirector를 사용한다.
`terminal.py`는 ASCII 출력 정책, `theme_art.py`는 6테마 무대,
`gallery_art.py`는 19배경/25효과를 담당한다. Effects는 시간축/캐시/합성 연결에 집중한다.
Bresenham 서브셀 선분, 보스/분석/모달과 기존 파일 이행을 구현했다.
전체118테스트/93컬러프레임/zipapp 검증 완료. 원격 릴리스는 .git 읽기 전용과 DNS 제한으로 미완료.
자세한 수치·변경·제약·릴리스 인계는 [최신 검증](docs/terminal-art-verification.md).
