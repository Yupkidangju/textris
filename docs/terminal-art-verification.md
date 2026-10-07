# 영문 호환·전체 아트 검증 및 릴리스 인계

작성: 2026-10-07. 근거: 현재 소스, tests, 실제 Linux PTY, App.draw 컬러 캡처.
대상 버전: **1.1.0**. 구현 기준: [계획](terminal-art-upgrade-plan.md).

## 완료된 구현
- 영문 단일 UI, ko 저장 설정 이행, Windows/비UTF-8 ASCII 기본, --unicode 선택.
- 모든 최종 출력의 ASCII 치환과 인코딩 오류 폴백. 재생기 없음/실패는 무음이며 beep/BEL 없음.
- ThemeScene 6개 독립 구도와 팔레트. ArtUI 공통 보호 영역/모달/프레임/타이틀.
- GalleryArt 19개 배경/25개 효과. 기존 게임 중 리본/파편 중첩 경로 제거.
- 보스 방패·코어·촉수, 분석 서브셀 곡선, 테마별 준비 숫자와 결과 프레임.
- 정수 서브셀 Bresenham, 캐시 결정성, 유한 주 연출 1개와 국소 연출 최대8개.
- 게임 엔진/리플레이 계약 불변. Windows 조건부 의존성과 CI 플랫폼 smoke 추가.

## 실제 검증
환경: Linux, Python 3.14.4, TERM=xterm-256color, UTF-8.

| 검증 | 결과 |
| --- | --- |
| `python3 -m unittest discover -s .` | **118개 통과**, 45.619초, 종료0 |
| `python3 -m compileall -q textris tests run.py` | 종료0 |
| `git diff --check` | 통과 |
| 독립 코드 재검토 | Critical/Important 추가 없음. 밀도 설정/갤러리 테마전환 지적 수정 및 회귀 통과 |
| 실제 PTY | 키 입력/도움말/정지/재시작/크기변경/설정이행/기록/보스/리플레이/종료 및 터미널 상태 복원 |
| 호환 경계 | ASCII, CP949, CP1252, CP437, UTF-8 인코딩/영문 문자열/동적 텍스트/UnicodeError 폴백/무벨 |
| 캡처 | 실제 App.draw **93개 프레임**, 6테마·12성취·44갤러리·4보조화면·21ASCII 표본 |
| zipapp | `python3 scripts/build.py --mode zipapp --skip-tests --no-clean` 빌드 및 help/version 통과 |
| zipapp 실제 PTY | 메뉴→쇼케이스→복귀→종료0, 전송 ASCII-only, BEL/Traceback 없음 |

[아틀라스](art-atlas.html) · [6테마](art-themes.png) · [44갤러리](art-gallery.png).
재생성: `python3 -m tests.capture_atlas` (검토 도구에만 Pillow/DejaVu 필요).
폰트 렌더링은 터미널마다 다르므로 캡처가 실제 Windows의 폰트 호환성을 보증하지 않는다.
영어 UI와 Unicode 글리프 문제를 분리한 근거:
[Microsoft 콘솔 코드페이지](https://learn.microsoft.com/en-us/windows/console/console-code-pages),
[Python curses](https://docs.python.org/3.14/library/curses.html).

## 성능
`python3 -m tests.benchmark_atlas` 종료0. 120×40, 게임 240프레임/테마,
갤러리 60프레임/항목. 실제 App.draw 비용이며 터미널 전송은 제외한다.
[원시 수치](art-performance.json).

| 테마 | 평균 ms | p95 ms |
| --- | ---: | ---: |
| Cathedral | 8.44 | 14.40 |
| Cyberpunk | 6.38 | 13.01 |
| Space | 7.06 | 15.50 |
| Fire | 6.23 | 14.96 |
| CRT | 5.82 | 11.66 |
| Mono | 8.46 | 18.91 |

첫 측정 모노 p95 39.66ms에서 18.91ms로 감소. 목표16.7ms는 5테마 충족,
모노는 초과한다. 갤러리 최대 p95는 smoke 19.96ms. 60 FPS를 전 환경에서
보장하지 않으며, 터미널 전송/폰트/CPU에 따라 추가 비용이 든다.

## 릴리스 상태 — 미완료
소스/메타데이터/CHANGELOG/조건부 의존성/태그 기반 CI는 1.1.0으로 준비했다.
현재 세션의 제한으로 커밋/태그/푸시는 수행하지 못했다.

- `git add pyproject.toml textris/__init__.py` → `.git/index.lock: Read-only file system`.
- 기본 Git SSH → `/etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf` 권한 오류.
- 시스템 SSH 설정을 제외한 읽기 연결 → `Could not resolve hostname github.com`.
- GitHub 연결 도구로 저장소 읽기/권한 확인은 가능했으나, 사용 가능한 도구에 태그 생성/푸시 기능이 없다.
- 권한/네트워크 경계를 우회하거나 원격 파일만 부분 게시하지 않았다.
- 따라서 **v1.1.0 태그, 원격 CI 성공, GitHub Release 및 5종 실행 파일/체크섬은 아직 미확인**이다.
- 이 환경에는 PyInstaller가 없어 네이티브 바이너리는 이번 작업에서 재빌드하지 않았다.
  dist의 기존 네이티브 파일은 이전 산출물이며 이번 검증 대상이 아니다.
- 새 로컬 산출물: `dist/textris.pyz`, SHA256
  `15fde27046e2a902584b42acf0f83e7f054329e62843fa9351971e8d3f3f33c9`.

쓰기 가능한 .git과 GitHub 연결이 있는 환경에서 현재 변경을 커밋한 뒤
`v1.1.0` 태그를 만들어 main과 함께 푸시한다. 기존 태그가 원격에 없는지 먼저
확인하고, Actions의 모든 빌드/플랫폼 smoke와 Release 자산 6개(5실행파일+SHA256SUMS)를
확인해야 릴리스가 완료된다. Windows 네이티브/실제 폰트·오디오 청취는 현재 로컬 검증 범위 밖이다.
