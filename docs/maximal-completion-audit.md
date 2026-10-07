# 최대 연출 확장 완료 검증

작성: 2026-10-07. 근거: `maximal-effects-plan.md`, 현재 소스, unittest,
실제 curses PTY, `maximal-fx-performance.json`, `maximal-replay-verification.json`.
기존의 작은 연출 확장 검증은 이번 18배경/25효과 범위로 확장했다.

| 승인 범위 | 구현과 검증 근거 |
| --- | --- |
| 절차적·입체 배경 18종 | scenes.py 카탈로그/투영, 전체 장면 경계 테스트, maximal-fx-gallery.txt 1~18 |
| 문자·충격·파괴 효과 25종 | effects.py 이벤트 연출, particles.py 충돌/마찰, 전체 장면 테스트와 캡처 19~43 |
| Braille·블록별 궤적·문자 아트 | 2×4 서브셀 합성/ASCII fallback, 배너/글리프/우선순위 회귀 테스트 |
| 콤보·피버·위험·음악 반응 | 시각 상태와 독립 RNG, 효과 설정별 코어 체크섬 동일, 8초 음원 길이/박자 검사 |
| 갤러리·테마·프로필 | E 확장 허브, 43항목/5테마/영구 설정, 모든 새 화면 표시 모드와 실제 키 입력 검사 |
| 리플레이·배속·탐색·분석 | Session 60Hz 명령, 검증/원자 저장/최근20개, Player checkpoint, 원본 불변/seek/체크섬 검사 |
| 보스 | 팔/코어 각60HP와 별도 기록, 피해/180초/topout 우선순위 회귀, 실제 합법 봇 승리 후 replay 재검증 |
| 자동 플레이 | 합법 회전/이동/홀드 명령 탐색, 40개 배치와 줄 삭제 검사, 전시 기록 제외/재시작 |
| 화면 합성·접근성 | 블록/ghost/HUD 상위 레이어, 넓은 글자 겹침 회귀, KO/EN·ASCII/Unicode·컬러/모노·64×28 검사 |
| 자원·성능 | 파편600/수명2초/배경20Hz, 자동 품질 조절, 120×40 최대 부하540프레임 평균15.708ms |
| 데이터 보존·오류 안내 | 기존 version1 기록, 손상/경로/심볼릭 링크/사용자 파일 보존 검사, 기록 한도 표시 회귀 |
| 실제 실행 | 새 허브/갤러리/설정/보스/분석/리플레이/자동 전시/resize/quit PTY 테스트, 43장 캡처 종료0 |

재현 명령:

최종 전체 검사: **75개 통과,39.548초**. compileall 종료 코드 **0**.
실제 PTY43장면 캡처 종료 코드 **0**, traceback 없음.

```sh
python3 -m unittest discover -q
python3 -m compileall -q textris tests run.py
python3 -m tests.benchmark_effects
python3 run.py
```

성능 측정은 Python 3.14.4, 가상 curses window, 터미널 전송 제외다.
최대 프레임35.079ms이며 프랙털 등 일부 장면은 평균16.7ms를 초과한다.
전체 평균 목표는 충족했지만 모든 프레임이나 모든 터미널의60 FPS를 보장하지 않는다.
실행 루프는 부하에 따라 배경 해상도/입자 표시량을 줄인다.
실제 오디오 장치 청취와 다른 OS 실행은 이 환경에서 확인하지 못했다.
별도 읽기 전용 코드 검토의 Critical/Important 잔여는 없다.
외부 서비스·배포·커밋·버전 변경은 수행하지 않았다.
