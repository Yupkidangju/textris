# 실행 원장 — docs/maximal-effects-plan.md
- 사전 확인: UI→Effects, Session→Game, Replay→Session, Auto→Session 명령 연결.
- Ruling: Git 메타데이터가 없으므로 현 프로젝트에서 직접 구현, 커밋 없음.
- Ruling: 기존 메뉴 키 순서를 보존하기 위해 확장 허브는 일곱 번째와 E 단축키로 제공.
- 작업1~5: 진행 중. 검증 증거는 각 작업 완료 시 추가한다.
- Ruling: 세션/리플레이의 독립 코어를 먼저 구현해 UI·효과·자동플레이가 공유할 시간/명령 계약을 고정한다.
- Ruling: 명령은 현재 tick의 update 전에 즉시 적용한다. 기존 UI의 입력 직후 반응과 동일하다.
- 작업1~4 코어/화면 연결 완료: 18배경/25효과, 갤러리/프로필/세션/보스/리플레이/자동전시.
- 실제 PTY에서 A가 게임용 좌측별칭과 충돌함을 재현. 갤러리/리플레이 전용단축키를 우선 처리.
- Ruling: 최대FX 120×40 가상window 평균27.43ms로 목표 초과. 공통 문자캔버스에서 레이어를 합성하고 최종 span만 curses에 써서 중복쓰기 제거. 게임 규칙에는 영향 없음.
- 독립 검토 Important4개 재현: 보스 early-observe 승리 tick, 정지 중 sample중복,
  새세션 분석 selection 범위, 합성화면 wideglyph owner/continuation 손상.
- Ruling: observe는 tick전 분석/피해를 수집할 수 있지만 승패확정과 정기sample은 step후에만 수행한다.
  리플레이와 실제UI의 코어 update순서를 일치시키는 보강이며 규칙변경이 아니다.
- Music .25초 note의 반샘플 truncation으로8초루프16샘플부족 재현. 누적샘플 경계로 합성한다.
- Ruling(보강): observe의 보스 피해도 step까지 보류한다. 같은 tick 내 이후 topout이 발생해도 UI관찰 시점과무관한 동일 결과를 보장한다.
- 리플레이 정리 대상은 앱 timestamp 형식의 파일로 한정해 같은디렉터리 사용자 파일을 보존한다.
- 독립 재검토: Important/Critical 잔여 없음. 실제 seed42 보스승리 replay 검증 통과.
- wideglyph/분석선택/정지샘플/music8초/동일ticktopout/사용자파일보존/Braille 회귀 검사 추가.
- 모든43개 갤러리 실제 PTY 캡처 확보, 최신 전체 테스트와 최종 벤치마크 진행 중.
- 최종 회귀: 기록 한도 알림이 일반 게임에서 보이지 않는 실패를 재현하고,
  공통 화면 하단 안내와 세션 경고 전달로 수정했다. 새 게임에서 이전 안내를 초기화한다.
- 작업1~5 완료. `python3 -m unittest discover -q`:75개 통과,39.548초.
- `python3 -m compileall -q textris tests run.py`:종료0.
- 최신43개 갤러리 실제 PTY 캡처 재생성:43장/종료0/traceback 없음.
- 다른 검사와 분리한 최종 벤치마크:540프레임 평균15.708ms/최대35.079ms,
  목표 전체 평균16.7ms 충족. 프랙털 등 장면별 초과와 터미널 전송 제외를 완료 검증에 명시.
- 세 기본 모드와 실제 합법 자동 입력 보스승리의 최종 replay 체크섬 검증 성공.
- 문서/코드/검증 동기화 완료. 승인된 확장 범위 미완료 없음.
  환경 제한:실제 오디오 장치 청취/다른OS 실행 미확인.
