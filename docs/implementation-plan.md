# TEXTRIS 구현 계획

목표: spec.md의 완성형 TUI 게임. Python stdlib, 새 프로젝트 현재 경로에서 직접 구현.
AGENTS.md 3.5/13.1에 따라 추가 승인/커밋 없이 진행. Git 저장소가 없어 worktree 불필요.
writing-plans/executing-plans/TDD/verification-before-completion 적용, 직접 실행.

## 작업 1: 엔진
- [x] 테스트 선작성 및 실패 확인: 7-bag, 4회 회전, 벽 차기, hold 1회 제한,
  drop 점수, 1~4줄 삭제, T-spin/B2B/combo/all-clear, top-out, lock delay/reset,
  Sprint/Ultra, seed 재현성과 pause 시간.
- [x] `textris/engine.py`: spec의 Game/Piece/Event 인터페이스. UI 의존성 없음.
- [x] `python3 -m unittest tests.test_engine -v` 통과.

## 작업 2: 서비스
- [x] 저장 손상/범위/원자 교체/10위 정렬, WAV 비무음 신호/길이, 번역 키 일치 테스트 실패.
- [x] `storage.py`, `audio.py`, `i18n.py`. 이벤트 이름을 엔진과 공유.
- [x] `python3 -m unittest tests.test_services -v` 통과.

## 작업 3: UI
- [x] `ui.py`, `__main__.py`, `run.py`, `pyproject.toml`, `.gitignore` 생성.
- [x] curses 60Hz loop, 입력 dispatcher, 상태 화면, UI 애니메이션, 오디오 lifecycle.
- [x] `tests/test_terminal.py` PTY로 실제 키/ANSI 출력/resize/quit 검증.
- [x] 오디오 실제 백엔드 probe, headless 자동 게임, 문서/사용법 갱신.

## 검토 초점
리사이즈와 pause 후 time jump, lock reset 무한 지연, 음원 프로세스 누수,
손상 저장 무단 덮어쓰기, 한국어 폭/작은 터미널 clipping.

## 진행 증거
구현/전체 검증 완료. 결과와 환경 제한은 IMPLEMENTATION_SUMMARY.md 및 docs/audit/audit_report_1.md에 기록했다.
