# TUI 연출 확장 계획
작성: 2026-10-07. 근거: 최신 사용자 요청, spec.md, designs.md, 현재 UI.

## 목표와 범위
충격·흔들림·파괴·배경 텍스트 애니메이션을 풍부하게 표현한다.
표준 라이브러리/curses, 기존 게임 규칙/저장 스키마/최소 64×28은 유지한다.
사용자가 구현과 지속 작업을 요청했으므로 AGENTS.md 3.5/13.1에 따라 별도 승인 없이 진행한다.

## 결정과 계약
- `textris/effects.py`는 게임에 의존하지 않는 문자 연출을 담당한다.
  `Effects.trigger(name,data,now)`, `update(now)`, `offset(now)`,
  `draw(app,bx,by,now)`, `background(app,now)`; bx/by는 보드 내부 왼쪽 위 좌표.
- 배경은 9초마다 문자 비, 플라스마, 별 터널, 와이어프레임으로 순환한다.
  낮은 밝기 배경, 색 순환, 사인파 문자 리본. 게임 통계/패널/오버레이는 뒤에 그려 가독성을 지킨다.
- drop/lock: 0.45초 감쇠 흔들림(최대 x±2/y±1), 1초 타원 충격파,
  0.55~1.15초 중력 파편, 세로 광선과 착지 스파크.
- clear: 모든 삭제 셀마다 파편 2개, 1초 폭발과 충격파, 점수 상승 문자,
  Tetris/T-spin/B2B/combo/all-clear는 강도 증가와 1.4초 대형 5행 문자 아트.
- rotate/hold/level/go/win/gameover도 색 입자/궤도/폭죽/파괴 연출을 생성한다.
  최대 파편 360개, 충격파 12개, 상승 문자 8개. 시간 만료와 재시작 시 정리한다.
  효과의 RNG는 엔진 RNG와 분리해 게임 결과를 바꾸지 않는다.
- 메뉴 V: `showcase` 화면. 1.6초 간격으로 drop/clear/Tetris/T-spin/combo/all-clear/
  level/gameover/win 연출을 반복한다. 엔진은 정지하고 기록을 저장하지 않는다.
  Esc/V는 메뉴 복귀, Q 종료, 일반 게임 조작은 적용하지 않는다.
- Unicode/ASCII와 컬러/모노 모두 지원. F는 해당 실행에서 연출 활성/정지 토글.
  줄 삭제와 기존 정보 배너는 F로 끄더라도 유지한다. 작은 창에서는 모든 입력/게임 정지 정책 유지.

## 순서와 검증
1. 효과 트리거/만료/상한/흔들림/엔진 독립성과 쇼케이스 입력 테스트 실패 확인.
2. 연출 모듈 및 UI 이벤트/배경/쇼케이스 연결, i18n/도움말.
3. 최소·큰 화면, ASCII/Unicode/모노 렌더링과 실제 PTY 쇼케이스/게임 입력 확인.
4. 전체 unittest와 compileall, 실제 PTY 프레임 캡처, 문서/변경 이력/구현 증거 동기화.

## 검토 보강
동일 프레임 drop→lock 이벤트에서 강한 drop 흔들림을 약한 lock이 덮지 않도록
활성 흔들림 강도의 최댓값을 유지한다. 승리 문자 아트 VICTORY의 Y 글리프를 제공한다.
두 조건을 회귀 테스트로 고정한 뒤 전체 검증한다.

## 완료 증거
- [x] 선행 실패 테스트와 구현, 단위/실제 PTY 회귀 검사.
- [x] 46개 전체 테스트 및 compileall 통과.
- [x] 모든 9단계 실제 PTY 캡처, 두 Minor 수정과 재검증.
- [x] spec/designs/README/CHANGELOG/IMPLEMENTATION_SUMMARY 동기화.
최종 상세 결과와 환경 한계는 IMPLEMENTATION_SUMMARY.md에 기록했다.
