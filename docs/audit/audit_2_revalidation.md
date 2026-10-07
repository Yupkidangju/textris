# 감사 2 수정 및 Windows 재검증

작성: 2026-10-07 (Asia/Seoul). 대상: TEXTRIS 1.1.0 + Unreleased 수정, 시작 HEAD `8fd1671`.
근거: 사용자 수정 요청, [원 감사](audit_report_2.md), [선행 설계](audit_2_remediation_plan.md),
spec/designs/AI 문서·코딩·감사 표준, 현재 소스와 아래 새 실행 증거.

**판정: 요청한 수정과 가용 Windows 재검증 완료.** 사람 청취, Windows 10 실기,
사용자 터미널 폰트, 물리 장치 탈착까지 포함한 무제한 PASS는 아니다.
기존 미추적 감사 보고서·audio/theme-status 자료는 보존했고, 커밋·푸시·게시·OS 설정 변경은 하지 않았다.

## 원 finding 대조와 수정

| ID | 판정과 변경 | 재검증 | 남은 범위 |
| --- | --- | --- | --- |
| T1 | 기존 강제 ASCII는 이전 정책의 구현이었음. 최신 타일 요구에 맞춰 Auto/Unicode/ASCII 및 저장 이행·CLI 우선순위를 설계 후 구현 | 실제 Windows 기본 Unicode, CLI/저장 모드, 설정 UI 순환/저장, 안전 폴백 회귀 | Windows 10·Cascadia Mono 픽셀 비교 |
| A1 | 외부 플레이어 전용 계약을 Windows waveOut으로 확장. 음악 1+효과음 3, PCM 수명·정지·제한 복구 구현 | PATH 비움/외부 플레이어 실행 금지 조건의 native 25검사, EXE/pyz audio-check | 별도 깨끗한 VM, 물리 장치 교체/청취 |
| V1 | 다섯 테마의 name/power/coords 미소비 확인 후 6종 의미별 형상·강도·행 출발점 구현 | 432보호 조건, 36실제 producer, 108실제 curses 조건, 시각 캡처·성능 | 최소 창의 장식 축소, 사용자 미적 수용·장시간 부하 |
| Q1 | 제품 색상 결함이 아닌 fixture/import/권한 가정 문제 확인 | Windows 전체 156개: 147통과/9명시 제외, 실제 junction 2개 통과, CI 전체 discover로 확대 | Unix PTY 6 및 symlink 권한 3은 Windows 통과에 포함하지 않음 |
| A2 | 짧은 효과음 출력을 실제 장치 피크로 확인. 진단에서 백엔드/앱/OS/청취를 분리 | 35ms move 5회 피크 0.222565, 전체 10효과음 신호, OS mute/volume 표시 | 실제 사람 청취 미확인 |

## 변경 파일 책임

- `textris/terminal.py`, `storage.py`, `ui.py`, `__main__.py`, `i18n.py`:
  표시 정책·저장 이행·UI 선택·세션 CLI 우선순위, 인코딩 폴백, 오디오 진단 표시.
- `textris/windows_audio.py`, `audio.py`: Windows waveOut 및 read-only endpoint 조회,
  비동기 수명/상한/복구. 비Windows 외부 backend 유지.
- `textris/theme_art.py`: clear/bloom/ascension/victory/eclipse/awakening의 테마별 형상.
  강한 삭제는 삭제 행 평균에서 확산하고 올 클리어는 해당 높이에서 상승한다.
- 새 `tests/test_display_modes.py`, `test_audio_check.py`, `test_windows_audio.py`,
  `test_theme_ceremonies.py`, `test_windows_paths.py`, `filesystem_helpers.py`와 기존
  terminal/ui/cathedral/expansion/services/audio/auxiliary fixture: 회귀·플랫폼 경계 검증.
- `scripts/windows_terminal_probe.py`, `windows_theme_probe.py`, `windows_audio_probe.py`,
  `theme_ceremony_probe.py`: 새 디렉터리에 기록하는 재현 도구.
- `.github/workflows/build.yml`: 네이티브 빌드의 6모듈 부분 검사를 전체 discover로 확대.
  `tests/capture_atlas.py`: 새 표시 우선순위에서도 ASCII 캡처 선택 보존.
- spec/designs/README/CHANGELOG/DESIGN_DECISIONS/IMPLEMENTATION_SUMMARY와 감사 문서:
  계약·실행·검증 한계 동기화.

## 환경과 최종 검사

Windows 11 build 26200 / Python 3.14.3 / locale CP949 / windows-curses 2.4.2 /
PyInstaller 6.19.0. 검증 의존성은 기존 `.antigravity/audit-20261007-status/deps`를 사용했다.
시스템 Python/OS 볼륨/사용자 데이터는 변경하지 않았다.

| 검사 | 실제 결과 | 증거 |
| --- | --- | --- |
| 수정 전 전체 discover | 113개, 4실패/4오류 | [baseline](../../.antigravity/audit-2-fix/baseline-tests.log) |
| 최종 전체 discover -s . -v | 156개, 147통과/9제외, 종료0 | [최종 로그](../../.antigravity/audit-2-fix/final-tests.log) |
| compileall textris tests scripts run.py | 종료0 | [검사 코드](../../.antigravity/audit-2-fix/final-checks.json) |
| git diff --check | 종료0, 공백 오류 없음 | 기존 CRLF 정책 안내만 출력 |
| 실제 App.run 콘솔 5시나리오 | 모두 종료0 | [최종 콘솔 결과](../../.antigravity/audit-2-fix/native-console-final/results.json) |
| 실제 curses 테마 108조건 | 108/108 보호·표시 통과 | [native 테마 결과](../../.antigravity/audit-2-fix/native-themes/results.json) |
| native 오디오 25조건 | 25/25 | [최종 오디오 결과](../../.antigravity/audit-2-fix-audio/native-runtime-final/result.json) |
| EXE+zipapp 빌드, help/version | 모두 종료0 (빌더의 전체 테스트도 통과) | [빌드 로그](../../.antigravity/audit-2-fix/build.log) |
| 생성 EXE+pyz audio-check, PATH 비움 | 둘 다 native backend 완료/종료0 | [산출물 검사](../../.antigravity/audit-2-fix/artifact-audio.json) |
| 생성 EXE 실제 콘솔 | Unicode 타일, 플레이/홀드/회전/드롭/일시정지/도움말/Q→Y, 종료0 | [입력 출력 일부](../../.antigravity/audit-2-fix/exe-input-output.json), [종료 결과](../../.antigravity/audit-2-fix/exe-console-exit.json) |

9제외는 Unix PTY 6개와 WinError 1314로 생성할 수 없는 symlink 3개다.
두 디렉터리 경계는 **실제 Windows junction**으로 별도 실행했고 audio/replay 모두
루트 탈출과 외부 쓰기를 차단했다. leaf symlink 실기 검증을 대신한 것은 아니다.
CI 설정은 수정했지만 이번 세션에서 GitHub Actions/macOS/Linux를 실행한 것은 아니다.

## T1 실제 출력과 입력

`App.run`, `handle`, `tick`을 교체하지 않았다. draw 직후 화면 버퍼를 읽고 다음 키를
실제 curses 입력 큐에 넣었다. wrapper 진입/종료, 메뉴→설정→READY→플레이,
좌 이동·홀드·회전·드롭·pause/help·축소/복원·재시작·종료를 거쳤다.

| 실행 | 저장 선택 | 실제 표시 | 보드/NEXT 타일 쌍 | Unicode ghost 쌍 |
| --- | --- | --- | ---: | ---: |
| 기본 | AUTO | Unicode | `██` 20 | 4 |
| --unicode | ASCII | Unicode | `██` 20 | 4 |
| --ascii | UNICODE | ASCII | `[]` 20 | 0 |
| 저장 Unicode | UNICODE | Unicode | `██` 20 | 4 |
| 저장 ASCII | ASCII | ASCII | `[]` 20 | 0 |

실제 설정 UI에서 AUTO→UNICODE→ASCII→AUTO 순환 후 각 저장을 다시 읽었다.
CLI 적용 시 기존 선택과 sound=true 저장이 보존됐다. input CP949/output CP65001/
window encoding CP65001이었다. native Palette(8,8)로 I/O 색상 attribute도 확인했다.
인코딩 fallback은 실패 주입 window 회귀 테스트이며, 실제 환경의 자연 발생 오류는 아니다.
콘솔 버퍼/입력 큐 증거를 물리 키보드·Windows Terminal 폰트 픽셀 증거로 확대하지 않는다.

## A1/A2 신호·수명·실패 검증

- PATH 비움과 외부 lookup/Popen 금지 조건에서 native를 선택했다. 효과음 10종 모두
  endpoint 신호가 관측됐다. move 35.011ms는 5회 모두 peak **0.222565**, 다른 효과음은
  **0.283569~0.283722**, 대기 기준은 약 **2.33e-10**이었다.
- 음악 9.1초 검사에서 두 루프 시작. 음악+효과음 최대 **4 voice**, 동시 peak **0.967865**.
  실제 UI hard drop 경로에서 고정된 보드 셀 4개와 출력 신호를 확인했다.
- pause/master mute/volume0/UI pause/close 뒤 신호는 대기 수준으로 돌아왔다.
  close 뒤 worker=false, 열린 handle=0, retained buffer=0.
- OS 전후 상태는 **mute=true, volume=0.0**. 피크는 감쇠 전 계측값이며 청취 증거가 아니다.
  OS 값을 변경하지 않았다. CLI도 backend completion과 listening unconfirmed를 분리한다.
- API/정리 실패·timeout·재시도는 fake driver로 주입했다. 실제 장치 고장·탈착은 미실행.
  드라이버가 버퍼 소유권을 반환하지 않으면 제한된 메모리를 보존하고 새 재생을 차단한다.

독립 리뷰에서 동시 voice timeout이 재오픈 전에 실패 예산을 소진하는 P2를 발견했다.
설계를 먼저 보강하고 RED 테스트 후 같은 사건을 한 번만 집계하도록 수정했다.
이전 voice 정리 후 재오픈하며, 새 사건/재개 실패의 누적 한도는 유지한다.
수정 후 오디오 집중 25/25, 리뷰 재검사 22/22 및 위 실제 장치 25조건을 다시 통과했다.
[RED](../../.antigravity/audit-2-fix-audio/failure-episode-red.log) ·
[최종 회귀](../../.antigravity/audit-2-fix-audio/tests-final-episode.log).

## V1 의미·보호·시각·비용

실제 `App.handle(' ') → Session → Game → process_events → Effects → ThemeScene → draw`
경로를 사용했다. 성취 직전 보드 fixture만 준비하고 이벤트는 엔진이 발생시켰다.

- 새 다섯 테마는 같은 시각·위상에서 **각각 6종**의 geometry 서명. 대성당은 수정하지 않아
  기존 5종 서명을 유지한다. flash=false에서도 각 의미의 intensity/power가 기하를 바꾼다.
- clear/bloom/ascension은 삭제 행과 보드 원점을 소비한다. 6테마×4크기×3표시×6의미
  **432조건**, producer 36건에서 보호·게임 checksum·리플레이 불변을 확인했다.
  실제 Windows curses에서도 **108조건**을 검증했다.
- 변경 테마 30프레임과 최소 창 ASCII/모노를 시각 확인했다.
  [프레임](../../.antigravity/audit-2-fix-themes/runtime-final/frames.html) ·
  [사이버펑크 6성취](../../.antigravity/audit-2-fix-themes/runtime-final/cyberpunk-contact.png) ·
  [원시 결과](../../.antigravity/audit-2-fix-themes/runtime-final/results.json).
  PNG는 실제 App.draw의 offscreen 셀로 생성했으며 사용자 터미널 스크린샷은 아니다.
- 64×28은 보드/HUD 보호를 우선해 장식을 축소하고 이벤트 문구로 의미를 전달한다.

120×40, 240프레임/테마, 자체 테스트 종료 후 순차 측정(터미널 전송 제외):

| 테마 | 평균 ms | p95 ms | 최대 ms |
| --- | ---: | ---: | ---: |
| 대성당 | 8.399 | 12.042 | 46.406 |
| 사이버펑크 | 6.988 | 9.623 | 77.169 |
| 우주 | 7.691 | 9.680 | 133.474 |
| 불꽃 | 6.755 | 10.517 | 13.462 |
| CRT | 7.022 | 9.183 | 211.265 |
| 모노 | 4.627 | 8.983 | 10.875 |

[순차 원시 값](../../.antigravity/audit-2-fix-themes/performance-sequential.json).
공유 호스트이며 격리 벤치마크는 아니다. 전체 테스트와 겹친 캡처에서는 일부 p95가
16.7ms를 넘었다. 최대 지연도 존재하며 모든 환경의 60FPS를 보장하지 않는다.

## 재현과 산출물

```powershell
$env:PYTHONPATH='.antigravity/audit-20261007-status/deps'
python -m unittest discover -s . -v
python -m compileall -q textris tests scripts run.py
python scripts/windows_terminal_probe.py --output .antigravity/verify-console-new
python scripts/windows_theme_probe.py --output .antigravity/verify-themes-native-new
python scripts/windows_audio_probe.py --output .antigravity/verify-audio-new
python -m scripts.theme_ceremony_probe --out .antigravity/verify-theme-frames-new
python scripts/build.py --mode all --no-clean
```

콘솔 probe는 TTY, 출력 경로는 새 이름이어야 한다. 테마 PNG 캡처만 Pillow가 필요하다.
이번 빌드의 TEMP/TMP/PYINSTALLER_CONFIG_DIR는 프로젝트 내부로 지정했다.
EXE 콘솔은 PATH/PYTHONPATH를 비우고 120×40에서 실행했다. pyz UI는 Python/
windows-curses가 필요하다. 별도 깨끗한 VM 검사는 아니다.

| 산출물 | bytes | SHA-256 |
| --- | ---: | --- |
| `dist/textris.exe` 및 `textris-windows-amd64.exe` | 9942443 | `10a3daab3fd082cd35696b018d7a2daaccfecdd53becee7874f968e30fba205e` |
| `dist/textris.pyz` 및 `textris-app` | 62614 | `300dc009712e3007644611815a70a43080f9e8afe1d04c94cf43fdad622d152d` |

버전은 1.1.0을 유지하며 Unreleased에 기록했다.
[환경·소스·산출물 manifest](../../.antigravity/audit-2-fix/manifest.json)로 이 수정본을 식별한다.
기존 사용자가 실행한 EXE와 동일하다고 주장하지 않는다.

## 남은 검증

Windows 10 실기, 사용자 Windows Terminal/Cascadia Mono 픽셀, 물리 키보드 체감,
OS 음소거 해제 후 사람 청취, 물리 장치 교체·드라이버 고장, 장시간 부하,
권한 있는 Windows leaf symlink, 타 OS/CI 클라우드 실행은 미확인이다.
현재 수정 범위와 Windows 기술 검증에 남은 차단 결함은 발견하지 못했다.
이 기록은 전체 제품/모든 장치에 대한 감사 PASS를 대체하지 않는다.

## 공식 자료

- [windows-curses Unicode 지원](https://github.com/zephyrproject-rtos/windows-curses)
- [waveOut 장치와 수명](https://learn.microsoft.com/en-us/windows/win32/multimedia/devices-and-data-types)
- [waveOutWrite 버퍼 완료](https://learn.microsoft.com/en-us/windows/win32/api/mmeapi/nf-mmeapi-waveoutwrite)
- [IAudioMeterInformation 계측 범위](https://learn.microsoft.com/en-us/windows/win32/api/endpointvolume/nn-endpointvolume-iaudiometerinformation)
