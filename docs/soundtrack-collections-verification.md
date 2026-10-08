# 음악 감상 모음 선택 검증

검증일: 2026-10-08. 구현 기준: `soundtrack-collections-plan.md`.

## 결과와 변경

Extras → Soundtrack은 Traditional Tetris(8곡), 6테마별 모음(각3곡),
All tracks(26곡)을 곡 수와 함께 표시한다. 방향키/W/S와 Enter로 모음을 연다.
곡 목록에서 Esc/Q/Tab은 감상을 종료하고 모음 선택으로 돌아간다.
다른 테마를 감상해도 게임 테마와 설정·기록은 바뀌지 않는다.

## 검증 근거

- `python -m unittest tests.test_soundtrack_ui tests.test_ui tests.test_expansion`:
  39개 중38통과/1환경별skip. 전체 `python -m unittest discover -s .`:
  233개 중223통과/10skip(Windows의 Unix PTY6개와 symlink 권한4개).
- 기존 코드에 새 메뉴 회귀 검사를 먼저 적용해 잘못된 진입 화면으로8개 실패함을 확인했다.
  수정 후 감상 UI12개 통과. 모음 선택 조건의 `or`를 `and`로 변조하면
  전통곡8개 대신0개가 되어 회귀 검사가 실패하며, 원본 복원 후12개 통과했다.
- `scripts/windows_soundtrack_ui_probe.py`: 실제 App.run·WriteConsoleInputW·curses·Audio를
  사용하는64×28/120×40, ASCII/모노4조건 모두 통과. 각 조건에서8개 모음과 곡 수,
  전체 목록 마지막 행 스크롤, 재생/일시정지/탐색/이전·다음/셔플/반복/음량/음소거/
  작은 창 정지·재개/복귀·정상 종료를 검사했다. 게임·리플레이·기록 생성 없음.
  [실행 결과](soundtrack-collections-evidence/windows-ui.json).
- 첫 실행은 모든 모음과 감상 조작 검사 후 Extras 복귀에서 기존45초 제한에 걸렸다.
  추가한 모음 검사 단계에 맞춰 제한을70초로 조정했다. 최종4조건은 각각47~49초에 종료했다.
- 새 Windows EXE를 PATH/PYTHONPATH가 빈 환경에서120×40 콘솔로 실행했다.
  Traditional Tetris8곡·Korobeiniki 재생(Playing 표시)·Orbital observatory3곡·복귀·종료0을
  확인했다. 종료 후 게임 테마cathedral과 빈 기록, 저장version1이 유지됐다.
- EXE `--audio-check`는 WASAPI 완료PASS. OS 음소거false/볼륨39%를 읽었으며 변경하지 않았다.
  장치 완료와 화면의 재생 표시는 물리 청취 판정과 구분한다.

## 패키징과 검증 범위

`python scripts/build.py --mode all --no-clean --skip-tests`로EXE/zipapp을 빌드하고
version/help/음원26곡·효과음30종/47,790,454바이트 해시 검사를 통과했다.
wheel은 `pip wheel . --no-deps --no-build-isolation`, sdist는 setuptools build_sdist로 만든다.
아카이브의 현재 UI code object/소스와63개 오디오 파일·문서 해시 및wheel RECORD를 검사한다.
실행 경로에서 import하지 않는particles 모듈은 기존과 동일하게EXE에서 제외되며
zipapp/wheel에 포함한다. 상세 크기·해시는
[배포 내용 검사](soundtrack-collections-evidence/package.json)에 기록한다.

음원과 재생 엔진을 변경하지 않아39분 전곡·10분 믹싱 검사를 반복하지 않았다.
물리 키보드·스피커 청취를 이번 자동 검사로 합격 선언하지 않는다.

## 게시 완료

코드 커밋 `4b6da74`에 v1.2.1 태그를 푸시했다.
[태그 CI](https://github.com/Yupkidangju/textris/actions/runs/37746663428)의7개 job이
모두 성공해 Linux x64/ARM64, Windows x64, macOS ARM64, zipapp과 체크섬을 게시했다.
[v1.2.1 릴리스](https://github.com/Yupkidangju/textris/releases/tag/v1.2.1).

CI Windows EXE(56,115,009바이트)는 외부 PATH/PYTHONPATH 없이 실제 콘솔에서
전통곡 모음 선택·Korobeiniki 재생·다른 테마 선택·정상 종료와WASAPI 완료PASS를 확인했다.
게시된EXE의SHA-256 `83ef00056646bfa64ed61838c1ec3e4ada675cd552cc514d72fda904a52b3126`은
이 검증 파일과 일치한다. 6개 게시 파일의GitHub digest와SHA256SUMS도 일치한다.
[CI Windows 실행 근거](soundtrack-collections-evidence/ci-windows.json),
[게시 파일·체크섬 근거](soundtrack-collections-evidence/release.json).
