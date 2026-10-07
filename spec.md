# TEXTRIS 실행 스펙

작성: 2026-10-07. 근거: 사용자 요청, AGENTS.md, AI_IMPLEMENTATION_DOC_STANDARD.md.
프로젝트명 TEXTRIS, 초기 버전 1.0.0, 로컬 Python TUI 게임. 사용자 언어는 한국어/영어로 가정.

## 목표와 완료 기준
터미널에서 키보드로 즐기는 완성형 싱글 플레이 테트리스. 독립 코어 테스트,
실제 PTY 키 입력/화면/종료/리사이즈 검증, WAV 신호 검증과 오디오 백엔드 확인을 완료한다.
온라인 대전, 계정, 외부 배포는 이번 범위가 아니다.

## 동결 결정
- Python 3.10 이상, 표준 라이브러리만 사용. Linux/macOS curses 터미널.
- `python3 -m textris` 또는 `python3 run.py`. 설치와 네트워크 불필요.
- 코어/화면/오디오/저장/번역 분리. 화면 60 FPS 목표, 실제 시간 delta로 진행.
- 보드 10×20 표시 + 상단 숨김 2행, I/O/T/S/Z/J/L 7-bag, NEXT 5개, HOLD 1개.
- 90도 좌/우 회전과 SRS 벽 차기, ghost, soft/hard drop, 0.5초 lock delay,
  바닥 이동/회전 시 최대 15회 지연 초기화. 숨김 행 잔존 또는 spawn 충돌이면 종료.
- Marathon: 10줄마다 레벨 상승. Sprint: 40줄 완료. Ultra: 120초 점수전.
- 중력 `max(0.05, 0.8 * 0.8 ** (level-1))` 초/행. soft drop 1점/행, hard drop 2점/행.
- 일반 삭제 100/300/500/800 × 현재 레벨, T-spin 0/1/2/3줄 400/800/1200/1600 × 레벨.
  회전이 마지막 성공 행동이고 T 중심 대각선 4곳 중 3곳이 막히면 T-spin 판정(미니 구분 없음).
  연속 Tetris/T-spin 삭제 B2B 1.5배, combo 두 번째 삭제부터 50×combo×레벨.
  All clear는 3500×레벨 추가. 레벨은 해당 삭제 이전 레벨로 점수 계산.
- READY → PLAYING ↔ PAUSED/HELP/CONFIRM → RESULT → MENU.
  줄 삭제 0.24초 깜빡임/입자, hard drop 잔상, 레벨 배너, 타이틀 낙하 문자,
  종료 보드 순차 채움. 모든 애니메이션은 입력 루프를 막지 않는다.
- 방향키/A/D 좌우, 아래/S soft drop, 위/X 우회전, Z 좌회전,
  Space hard drop, C 홀드, P/Esc 일시정지, H/? 도움말, M 음소거,
  B 배경음 토글, R 재시작 확인, Q 종료 확인. 메뉴 Enter 선택.
- 메뉴: 모드 3개, 시작 레벨 1~15, 설정, 기록, 종료. 설정: 언어, 색상/모노,
  블록 Unicode/ASCII, 전체 사운드, 음악, 볼륨 0~100%.
  전체 사운드 설정은 M과 같은 마스터 음소거이며 음악에도 적용된다. 시작 전 3초 카운트다운.
- i18n 문자열 외부화. 최소 64×28, 미달 시 안내와 자동 게임 정지, 확대 후 재개.
- stdlib wave로 직접 합성한 효과음/오리지널 루프 음악. 외부 유료 서비스나 음원 사용 없음.
  aplay/paplay/ffplay/afplay 자동 선택, 비동기 실행, 실패하면 터미널 bell fallback.
  음악은 pause/help/resize/confirm 시 중단, 프로세스 종료 시 모두 정리.
  생성 음원 디렉터리/파일의 정규 경로는 지정한 데이터 루트 내부인지 검증한다.
- 기본 저장은 프로젝트 내부 `.textris-data/records.json` (외부 쓰기 방지).
  스키마 `{"version":1,"settings":{"language":"ko","sound":true,"music":true,
  "volume":0.5,"ascii":false,"color":true},"records":{"marathon":[],"sprint":[],"ultra":[]}}`.
  기록 필드 score:int, lines:int, level:int, seconds:float (0~10^12), completed:bool, date:str.
  모드당 10개, sprint 완료 시간 우선/나머지 점수 우선. 임시 파일 후 원자 교체.
  손상/권한 오류는 실행을 중단하지 않고 상태 안내, 원본 손상 파일 유지.

## 모듈 계약
`Game(seed=None, mode="marathon", start_level=1)`: board:list[list[str|None]],
active:Piece(kind,rotation,x,y), score/lines/level:int, elapsed:float, state:str,
events:list[Event(name, data)]. `move(dx,dy)`, `rotate(direction)`, `hold()`,
`hard_drop()`, `update(dt)`, `ghost_y()`; 이벤트는 spawn/move/rotate/hold/drop/lock/
clear/level/gameover/win. UI가 큐를 소비해 효과를 표시한다.
`Audio.play(name)`, `Audio.set_music(bool)`, `Audio.close()`는 blocking 재생하지 않는다.
`Store.load()/save()/record()`는 저장 상태와 warning 문자열을 제공한다.

## 구현/검증 순서
1. tests/test_engine.py 실패 증거 → 엔진 구현 → bag/회전/충돌/홀드/삭제/점수/모드/시간 테스트.
2. tests/test_services.py 실패 증거 → WAV 합성/저장/번역 구현 → 신호/손상/정렬/경계 검증.
3. curses UI/진입점 구현 → 실제 PTY smoke 테스트: 메뉴, 시작, 입력, pause/help,
   재시작, 리사이즈, 설정/기록, 종료와 터미널 복구. 별도 엔진 장기 자동 플레이.
4. README/designs/구현 증거 동기화, 전체 테스트 및 compileall, 완료 요구별 감사.

## 잔여 환경 제한
터미널 키 반복은 OS/터미널 설정을 따른다(키 release 이벤트 없음).
오디오 장치/서버가 없으면 실제 청취는 불가능하고 bell도 터미널 설정에 의존한다.
Windows 기본 Python에는 curses가 없어 WSL 실행을 안내한다.

## 화려한 TUI 연출 확장 (2026-10-07)
최신 요구에 따라 충격·감쇠 흔들림·충격파·블록 파괴 파편·폭죽·상승 점수·
대형 문자 아트와 네 종류의 순환 배경을 구현한다. 상세 계약/수치/검증 기준은
`docs/effects-plan.md`. 메뉴 V로 기록에 영향 없는 쇼케이스, F로 실행 중 연출 토글.

## 최대 연출·기능 확장
2026-10-07 최신 승인 계획: docs/maximal-effects-plan.md.
기존 세 모드 규칙은 보존하며 별도 보스, 결정적 리플레이, 분석, 자동전시,
전체 효과 갤러리/테마와 추가 텍스트 효과를 제공한다. 기존 연출 상한·구성은
새 계획의600파편/2초수명/합성 우선순위로 확장한다.

## 우주 대성당 미술 재설계 (2026-10-07)
최신 구현 기준은 `docs/cathedral-plan.md`. 120×40을 기준으로 새 기본 테마
cathedral, Braille 연속 곡선·깊이 기반 입체 아트·장미창·빛 커튼과 단일 주 연출을
도입한다. 기존 저장 테마는 보존한다. 새 테마에서 이전 순환 배경/상시 리본/
복수 폭발은 대성당 장면과 단계별 연출로 대체하고 기존 효과는 갤러리에 유지한다.

## 멀티플랫폼 단일 실행 파일 빌드 및 오픈소스 라이선스 (2026-10-07)
- 빌드 스크립트: `build.sh` 및 `scripts/build.py`.
- 범용 멀티플랫폼 단일 파일 번들: Python `zipapp` 기반 `dist/textris.pyz` (Linux/macOS/Windows 호환).
- Standalone 독립 단일 바이너리: PyInstaller `--onefile` 기반 `dist/textris` (호스트 OS 네이티브).
- CI/CD 파이프라인: `.github/workflows/build.yml`을 통한 Linux (x86_64, arm64), Windows (x64), macOS (arm64) 자동 매트릭스 빌드.
- 릴리즈 자동화: `v*` Git 태그 푸시 시 GitHub Release 생성 및 바이너리/체크섬 자동 첨부.
- 라이선스: Apache License 2.0 (`LICENSE`, Copyright 2026 yupkidangju@gmail.com).


