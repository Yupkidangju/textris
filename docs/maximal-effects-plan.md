# TEXTRIS 최대 연출·기능 구현 계획
작성: 2026-10-07. 근거: 사용자가 승인한 대화 계획, 현재 spec/designs/소스,
AI_IMPLEMENTATION_DOC_STANDARD.md 및 AI_CODING_STANDARD.md.
실행: executing-plans/TDD, 직접 구현, 끝에 독립 코드 검토. Git 저장소가 없어 현 경로에서 작업한다.

## 목표/제약
제시한 충격/파괴/입체·절차적 배경/문자 연출, 반응형 피버/음악/위험,
갤러리/다섯 테마/리플레이/분석/자동 플레이/별도 보스를 모두 제공한다.
기존 세 모드의 점수·중력·착지 규칙 유지. Python stdlib/curses, 최소64×28,
한국어/영어/ASCII/Unicode/컬러/모노, 기존 저장 version1 호환. 커밋/배포 없음.

## 연출 계약
배경→반사/장식→효과→실제 블록/ghost→HUD→모달.
물결 왜곡/탄성/충격 잔상은 플레이 중 배경·빈 셀·테두리에 적용.
큰 이벤트 우선순위 승패>올클리어>Tetris/T-spin>콤보>삭제>착지.
주 배경 하나+별/리본, 0.8초 디졸브. 배경20Hz 이하/캐시/적응형 해상도.
파편600/충격파12/상승문자8, 파편 벽·바닥 반발/마찰과 최대2초 수명.
추가: 균열/분해/연쇄폭발/번개/블랙홀/글리치/연기/불꽃/Braille,
회전 cube/tetromino/torus, Mandelbrot/Julia 줌, 오로라/유체/메타볼,
다층 우주/워프/도시/문자 로고/수면 반사, 타이핑·조립 배너/콤보 계기/승패 시퀀스.
작은 창 대형문자→배너. F 추가연출 off; shake/flash/Braille 개별 설정.

## 반응/설정
콤보 0~1/2~3/4~6/7+ 네 강도. 피버 게이지 줄당15, T-spin/Tetris+20,
올클리어+40;100시8초 피버후 초기화, 게임 규칙에는 영향 없음.
표시 상단6행 위험 상태. I laser/O gold/T vortex/SZ electric/J ice/L fire.
음악 박자/진폭 모델, 음소거시 가상 박자, 음악 강도 다음 루프 경계 변경.
테마 cyberpunk/space/fire/crt/mono, 강도·밀도 .75/속도1 기본.
설정 영구저장, F는 세션 전용. 모든 항목 갤러리 선택/Space실행/자동순환.

## 세션/리플레이/보스 계약
Session: 고정1/60초 tick, command(left/right/soft/cw/ccw/hold/drop) 순서 실행후 update.
정지/help/작은창 tick 멈춤. seed가 없으면 생성해 기록. 별도 FX RNG.
Replay version1/rules1/seed/mode/level/(tick,command)/end_tick/최종checksum.
최근20개, 파일2MiB/명령100000/시간2시간 한계, 실패시 게임은 유지+안내.
Player .5/1/2/4배속/pause/±5초 seek, 주요삭제1초 slow motion, 원본불변.
분석 점수그래프/콤보타임라인/특수삭제횟수/주요장면 seek.
자동: 합법명령만, 줄삭제/구멍/높이/굴곡 평가,4ms이하 분할 탐색, gameover 재시작,
순위/리플레이 기록 없음. 갤러리/showcase/replay도 순위 기록 없음.
보스: Game(marathon) 래핑, 팔2/코어 각60HP, 순차손상/초과피해 이월,
삭제10/25/45/70,spin+20,perfect+40,180초,topout 우선패배, 별도boss기록.

## 구성 및 순서
1. 공통 렌더러/카탈로그/프로필 (`scenes.py`, `effects.py`, `particles.py`).
2. 효과/배경/반응/음악과 payload 부가. 기존 엔진 규칙 변경 없음.
3. 갤러리/허브/설정/테마, 메뉴 원래6개 유지+확장7번째로 키 호환.
4. `session.py`, `replay.py`: 결정적 틱/보스/분석/검증된 원자 저장/Player.
5. `autoplay.py`와 UI 연결, 실제 PTY/성능/전체테스트/문서.
모든 작업은 선행 실패 테스트→구현→검증, 진행은 docs/maximal-effects-progress.md.

## 완료 기준
전체 unittest/compileall, 각 효과 실행/합성/수명/경계 검증과 PTY 캡처 대응표.
FX 설정불변 게임결과, replay 배속/seek 최종일치, 기존 파일·손상보존,
새 UI 실제 PTY/resize/pause/quit.120×40 평균16.7ms 목표,부하시는 배경→입자 축소.
