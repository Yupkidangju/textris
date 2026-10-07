# CI 리플레이 이름 충돌 수정

작성: 2026-10-08. 근거: Windows Python 3.12 CI 37657156573의
`test_replay_recent_twenty` 실패, `textris/replay.py`, `spec.md`,
`AI_IMPLEMENTATION_DOC_STANDARD.md`, `AI_CODING_STANDARD.md`.

## 목표와 구현 기준

- 같은 시각에 22회 저장해도 각 저장에 서로 다른 이름을 발급하고 마지막 20개를 보존한다.
  시계가 뒤로 이동하거나 새 ReplayStore 인스턴스를 만들어도 기존 파일을 교체하지 않는다.
- 기존 JSON/version/rules/checksum, OWN_NAME 형식, 목록 역순, 게임 RNG는 유지한다.
- 현재 시각과 디렉터리의 가장 최신 이름보다 1마이크로초 뒤인 시각 중 큰 값을 쓴다.
  filename은 충돌 방지를 위한 논리적 시각이며 정확한 벽시계 기록을 보장하지 않는다.
- 같은 디렉터리의 고유 임시 파일에 JSON 전체를 쓰고 닫은 후 Windows에서는
  `os.rename`, POSIX에서는 `os.link`로 게시한다. Windows rename은 목적지가 있으면
  실패하므로 hardlink 미지원 파일시스템도 지원한다. POSIX rename은 교체하므로 쓰지 않는다.
  목적지가 이미 있으면 최신 이름을 다시 확인하고 최대 128회 시도한다.
  원자적으로 완성된 내용만 공개하며 기존 목적지는 교체하지 않는다.
- POSIX hardlink가 지원되지 않거나 권한/이름 범위 오류가 발생하면 `None`과 기존
  `replay_error`를 반환한다. 임시 파일을 정리하고 게시 전에는 기존 파일을 삭제하지 않는다.
  위험한 overwrite 또는 부분 파일이 보이는 직접 쓰기로 fallback하지 않는다.
- 성공 후 기존 소유 파일 20개 유지 정책을 적용한다. 동시 pruning이 이미 삭제한
  파일은 오류로 취급하지 않는다. 외부 파일/심볼릭 링크 정책은 유지한다.
- Windows 동시 초기화에서 Path.resolve가 표준 확장 경로 접두사를 일시 반환하는
  경우를 처리한다. root 포함 여부 비교에만 `\\?\C:\...`와 `\\?\UNC\server\share\...`를
  각각 동등한 일반 DOS/UNC 형식으로 정규화한다. 실제 I/O 경로는 보존하며,
  GLOBALROOT/장치 namespace는 허용하지 않는다. 경계는 문자열 startswith가 아닌
  pathlib의 구성요소 단위 is_relative_to로 확인한다.
- 전원 장애 내구성/fsync, 적대적인 디렉터리 교체 방어, 여러 프로세스의 저장 순서를
  전역적으로 직렬화하는 기능은 이번 수정 범위가 아니다.

## 순서와 검증

1. 시각 고정 22회 저장 및 기존 바이트 보존 테스트의 RED를 확인한다.
2. 저장 경로만 수정한다. 테스트 기대 개수20은 변경하지 않는다.
3. 고정/역행 시각, 새 인스턴스, 게시 직전 경쟁, 게시 실패와 임시 파일 정리,
   최신 20개 내용, 기존 expansion/session 회귀를 검증한다.

공식 근거: [Python os.rename](https://docs.python.org/3/library/os.html#os.rename),
[Python os.link](https://docs.python.org/3/library/os.html#os.link).
Unix의 hardlink 미지원 파일시스템은 저장 실패를 명시하고 기존 리플레이를 보존한다.

## 검증 기록

- RED: 수정 전 고정 시각 22회 저장에서 고유 이름 `1 != 22`, 같은 시각 두 번째
  저장에서 첫 번째 파일의 seed1 바이트가 seed2로 바뀌는 실패를 재현했다.
- GREEN: Windows Python 3.14에서 아래 명령으로 40개 실행, 39개 통과,
  심볼릭 링크 권한 부족(WinError1314) 1개 skip. 기존 junction 탈출 방어 2개는 통과했다.

  ```powershell
  $env:PYTHONPATH='.antigravity/audio-overhaul-20261008/deps;.antigravity/audit-20261007-status/deps'
  python -m unittest tests.test_replay_storage tests.test_expansion tests.test_session tests.test_windows_paths -v
  ```

- 고정 시각에서 초 경계(999999µs)를 넘는 22개 이름 및 마지막 20개 seed 순서,
  시계 역행/새 인스턴스, 실제 Windows rename의 WinError183 충돌과 재시도,
  게시 실패/128회 충돌 제한/임시 파일 정리, hardlink 분기 실제 파일 I/O를 검증했다.
- cold-start 8-worker 동시 생성 탐색에서는 기존 Windows Python3.14 Path.resolve가 순간적으로 `\\?\C:` 형식을
  반환하여 `_path`의 root 비교에서 안전 실패하는 현상이 발견됐다. 기존 바이트를
  교체하지는 않았다. cold-start 8-worker 및 inside DOS/UNC 경계 RED를 재현한 후
  비교 정규화를 적용했다. cold-start 회귀를 그대로 유지하며 10회 반복 통과,
  DOS/UNC 루트 내부 허용 및 유사 접두사 외부/다른 share/장치 namespace 거부를 검증했다.
  CPython 3.14 `ntpath.realpath`의 확장 경로 접두사 제거 조건과 실제 실패 경로도 대조했다.
- 실제 POSIX OS 실행, Windows Python3.12 CI 재실행, FAT/exFAT 장치 검증은
  이 로컬 결과에 포함하지 않는다. hardlink 분기는 Windows NTFS에서 실제 실행했다.
