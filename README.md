# TEXTRIS

키보드로 플레이하는 터미널 테트리스. 컬러 블록과 텍스트 애니메이션,
테마별 4파트 MIDI 편곡 음악과 생성형 효과음을 제공합니다. 음악/효과음은 패키지에 포함되며
실행 중 네트워크나 외부 재생기는 필요하지 않습니다. 소스 실행은 `python -m pip install .`로
miniaudio 및 Windows의 windows-curses를 설치하세요. 배포 EXE에는 런타임 의존성이 포함됩니다.

기본 미술 테마는 **우주 대성당**입니다. Braille 곡선의 장미창, 원근 아치,
깊이가 있는 천체 고리, 빛 커튼과 성취에 반응하는 문자 아트가 보드를 감쌉니다.
권장 화면은 **120열 × 40행**, 최소 화면은 64×28입니다.

```bash
python3 -m textris --theme cathedral
```

이미 저장한 테마는 보존됩니다. 위 명령은 이번 실행에만 대성당을 적용합니다.
계속 사용하려면 **E → Effects & themes → Theme → Cosmic cathedral**을 선택하세요.
6개 테마와 19종 배경·25종 효과 전체에 보호 영역·서브셀·깊이 합성을 적용했습니다.
네온 도시, 천체 관측소, 태양 대장간, 인광 실험실, 모노 판화는 서로 다른 구도와 팔레트를 사용합니다.
[전체 테마/갤러리 프레임](docs/art-atlas.html) · [테마 비교](docs/art-themes.png) · [갤러리 비교](docs/art-gallery.png)

[컬러 연속 프레임 미리보기](docs/cathedral-preview.html) ·
[플레이 화면](docs/cathedral-idle.png) · [올 클리어](docs/cathedral-all-clear.png)

모든 테마에서 보드의 빈칸과 HUD를 안정적으로 유지하고, 하드 드롭에는 빛 기둥,
테트리스/T-spin과 올 클리어에는 테마별 격자 폭발·초신성·불꽃·파형·판화·대성당 연출을 표시합니다.
삭제·강한 삭제·올 클리어·승리·게임 오버·레벨업은 서로 다른 유한 형상으로 반응하며,
섬광을 꺼도 강도 설정과 콤보 power가 형상에 반영됩니다.
효과가 겹쳐도 주 연출은 하나이며 게임 입력과 시간을 멈추지 않습니다.
256색이 없으면 기본 색상으로, Braille을 끄면 점/선 문자로 대체합니다.
`--ascii`, 모노 설정, 흔들림·섬광 옵션과 **F** 효과 토글도 지원합니다.

```bash
cd /home/eunho1/Projects/textris
python3 -m textris
```

Python 3.10 이상과 대화형 터미널이 필요합니다. Windows는 배포 EXE를 실행하거나
`python -m pip install .`로 조건부 의존성까지 설치하세요. WSL도 지원합니다.
터미널 크기는 최소 **64열 × 28행**입니다. 창을 줄이면 게임과 시간이 멈춥니다.
`python3 run.py`도 같은 게임을 실행합니다. 제품 UI는 영문 단일입니다. 기존 한국어 설정은 기록을 보존하면서 영어로 이행합니다.
설정의 **Display mode**에서 **AUTO / UNICODE / ASCII**를 선택하고 저장할 수 있습니다.
Windows AUTO는 Unicode 타일(`██`)을 기본 사용하고, Unix AUTO는 UTF-8 여부를 따릅니다.
`--unicode` 또는 `--ascii`는 저장 선택보다 우선하며 이번 실행에만 적용됩니다.
기존 ASCII 설정은 유지됩니다. 실제 인코딩 오류가 발생하면 재시작 전까지 ASCII로 전환합니다.
영문 UI만으로 Unicode 글리프 호환성이 보장되지는 않으며, 깨지면 `--ascii`를 사용하세요.
ASCII 모드에서는 메뉴·아트·동적 파일명까지 최종 출력 경계에서 7비트 문자로 바꿉니다.

- 마라톤: 10줄마다 레벨 상승, 시작 레벨 1~15.
- 스프린트: 40줄 완료 시간 도전.
- 울트라: 120초 점수 도전.
- 7-bag 블록, SRS 벽 차기, NEXT 5개, HOLD, 고스트, 0.5초 착지 지연.
- T-spin, Tetris 연속 보너스, 콤보, 올 클리어와 최고 기록.
- 감쇠 보드 흔들림, 착지 빛 기둥, 성취 궤도·방사선·대형 문자 아트.
- 장미창·도시 원근·천체 구체·코로나·리사주·기요셰 판화의 테마별 무대.
- 조립되는 타이틀, 색 단계 카운트다운과 장식 프레임, 콤보·레벨·승리·게임 오버 연출.
- 메뉴 **V**: 연출 쇼케이스. **E**: 확장 허브(갤러리·테마·보스·리플레이·자동 전시).
- **19종 배경 + 25종 효과**: Braille 점 입자, 회전 큐브·토러스·입체 블록, 프랙털 줌,
  오로라·유체·메타볼·문자 도시·입체 로고·수면 반사.
- 균열·셀 분해·벽/바닥 파편 충돌·연쇄 폭발·번개·블랙홀·글리치·연기·불꽃.
- 콤보 고조·8초 피버·상단 위험 경고, 보스 궤도 방패/코어와 서브셀 분석 그래프.
- 피버와 테마는 기존 세 모드의 점수·중력·착지 규칙을 바꾸지 않습니다.
- 별도 보스: 팔 2개와 코어를 줄 삭제로 파괴. 각 60 HP, 제한 시간 180초.
- 자동 리플레이, 배속·구간 이동·주요장면 카메라, 점수 그래프·콤보 타임라인.
- 합법적인 입력으로 움직이는 자동 플레이 전시. 전시·감상은 순위 기록을 만들지 않습니다.
- 일시정지, 조작 도움말, 재시작/종료 확인, 모드별 상위 10개 기록.
- 영문 UI, Unicode/ASCII 아트, 컬러/모노, 전체 사운드/음악/음량 설정.

| 키 | 동작 |
| --- | --- |
| ← / → 또는 A / D | 좌우 이동 |
| ↓ 또는 S | 소프트 드롭 |
| ↑ 또는 X | 오른쪽 회전 |
| Z | 왼쪽 회전 |
| Space | 하드 드롭 |
| C | 홀드 (블록당 한 번) |
| P / Esc | 일시정지/재개 |
| H / ? | 조작 방법 |
| M | 전체 음소거 |
| B | 배경음악 켜기/끄기 |
| F | 추가 연출 켜기/끄기 (현재 실행에 적용) |
| V (메뉴) | 연출 쇼케이스; Esc / V로 메뉴 복귀 |
| E (메뉴) | 확장 기능 허브 |
| A (결과/리플레이) | 분석 화면 |
| R | 재시작 확인 |
| Q | 종료 확인 |

메뉴에서 ↑↓/W/S로 선택하고 Enter로 실행합니다. ←→로 시작 레벨을 바꿉니다.
설정에서는 ←→ 또는 Enter로 값을 바꿉니다. 확인 창은 Y/Enter로 승인,
N/Esc로 취소합니다. 결과 화면은 Enter/R로 재시작, Esc로 메뉴로 돌아갑니다.
키를 누르고 있을 때의 반복 속도는 터미널/운영체제 설정을 따릅니다.

갤러리에서는 방향키로 장면을 고르고 Space로 실행, A로 자동 순환합니다.
T는 테마, +/-는 강도, [ / ]는 속도, { / }는 입자량입니다. 값은 자동 저장됩니다.
우주 대성당·사이버펑크·우주·불꽃·레트로 CRT·모노크롬 프리셋과 흔들림·섬광·Braille 개별
설정은 확장 허브 또는 설정의 **Effects & themes**에서 바꿉니다.

리플레이에서는 Space/P로 정지, ↑↓로 0.5/1/2/4배속, ←→로 ±5초 이동,
C로 주요장면 카메라, A로 분석합니다. 분석의 방향키/Enter로 주요장면을 재생합니다.
자동 전시는 P로 정지, Esc로 허브에 복귀하며 게임 오버 뒤 자동으로 재시작합니다.
기존 설정·기록 파일은 그대로 호환됩니다.

```bash
python3 -m textris --unicode
python3 -m textris --ascii --no-sound
python3 -m textris --seed 42
python3 -m textris --audio-check
python3 -m textris --verify-audio-assets
python3 -m unittest discover -v
```

음악은 **6테마×3곡 + Classic 8곡 = 26곡**, 각85~95초입니다. lead/harmony/bass/drums
네 MIDI 파트로 편곡하고 풍부한 악기 음색으로 미리 렌더한 Ogg를 사용합니다.
현재 테마의3곡과 Classic8곡을 약1:1로 섞으며 곡을 모두 소진하기 전 같은 범주의 곡을
반복하지 않습니다. 다른 테마의 전용곡이 현재 게임에 섞이지 않습니다.

메뉴 **Extras → Soundtrack**에서 전체 곡을 감상할 수 있습니다. 위/아래로 선택,
Enter 재생, Space 일시정지, N/P 다음/이전, 좌/우5초 탐색, Tab 필터,
S 셔플, R 한 곡 반복, +/- 음악 음량, M 전체 음소거, B 음악 토글, Esc/Q 복귀입니다.
곡명·분류·시간·진행·BPM·4파트 악기를 표시하며 감상은 점수·기록을 만들지 않습니다.

Agent Audio 효과음30종을 실제 조작·삭제·연속 성취·위험 진입·보스·UI 결과에 연결합니다.
음악1곡과 효과음최대6개를 믹싱하며 주요 성취가 중복 착지음보다 우선합니다.
설정의 마스터/음악/효과음 음량을 별도로 조절할 수 있습니다.
Windows는 miniaudio의 WASAPI를 우선 사용하며 WINMM으로 대체할 수 있습니다.
음악은 pause/help/confirm/작은 창에서 위치를 보존해 정지하고 재개 시 이어집니다.
장치/음원 실패는 무음과 상태로 안내하며 경고음(beep/BEL)으로 대체하지 않습니다.

`--audio-check`는 백엔드 완료와 앱 설정, Windows OS 음소거·볼륨을 구분해 표시합니다.
종료 코드 0은 백엔드 완료를 뜻하며 **스피커 청취 성공을 뜻하지 않습니다**.
앱 음소거/볼륨 0 또는 재생 실패는 종료 코드 1입니다. OS 설정은 자동 변경하지 않습니다.
OS가 음소거되었거나 볼륨이 0이면 사용자가 Windows 출력 장치 설정에서 확인하세요.

`--verify-audio-assets`는 장치를 열지 않고 포함된26곡/30효과음의 목록·경로·해시를
검사합니다. 제작 원본/출처와 상세 계약은 [사운드 개편 설계](docs/audio-overhaul-plan.md)에 있습니다.

리플레이는 `.textris-data/replays/`에 최근 20개를 보관합니다. 한 게임당 최대
2MiB·10만 명령·2시간이며, 한도나 저장 실패는 플레이를 중단하지 않습니다.
리플레이는 고정 60Hz 명령 기록과 최종 상태 체크섬으로 재생 결과를 확인합니다.
연속 저장이나 시계 역행에서도 기존 파일을 덮어쓰지 않도록 파일명은 단조 증가하는
논리적 시각을 사용합니다. Windows는 원자적 no-clobber rename, POSIX는 hardlink 게시를
사용하며 POSIX 저장 위치가 hardlink를 지원하지 않으면 기존 파일을 보존하고 저장 오류를 표시합니다.

설정/기록은 프로젝트 내부 `.textris-data/records.json`에 저장됩니다. 배포 음악과 효과음은
패키지의 `textris/assets/audio`에 있으며 필요한 zipapp 추출 캐시는 데이터 디렉터리 안에 둡니다.
`--data-dir 경로`로 저장 위치를 지정할 수 있습니다.
`--no-sound`, `--ascii`, `--unicode`는 해당 실행에만 적용됩니다. 저장 파일이 손상됐으면
원본을 보존하고 화면에 안내합니다. 게임 종료 후 해당 파일을 직접 다른 이름으로
옮기면 다음 실행에서 새 기록 파일을 만들 수 있습니다.

점수는 일반 1/2/3/4줄 100/300/500/800 × 레벨, T-spin 0/1/2/3줄
400/800/1200/1600 × 레벨입니다. 마지막 성공 행동이 회전이고 T 중심의
대각선 4곳 중 3곳이 막혔을 때 T-spin으로 판정하며 미니는 별도로 구분하지 않습니다.
연속 Tetris/T-spin 삭제는 1.5배, 콤보는 두 번째 연속 삭제부터 50×콤보×레벨,
올 클리어는 3500×레벨을 더합니다. 소프트/하드 드롭은 이동한 줄당 1/2점입니다.

구조와 검증 근거는 [spec.md](spec.md), [designs.md](designs.md),
[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)를 참고하세요.

전체 장면 캡처는 [컬러 아트 아틀라스](docs/art-atlas.html), 확장 구현 계약은
[최대 연출 계획](docs/maximal-effects-plan.md)을 참고하세요. 렌더링 비용은
`python3 -m tests.benchmark_atlas`로 측정할 수 있습니다(터미널 전송 비용 제외).


대성당 검증은 `python3 -m unittest discover -v`, 성능 측정은
`python3 -m tests.benchmark_cathedral`로 실행합니다. 컬러 프레임은
`python3 -m tests.capture_cathedral`로 HTML에 재생성할 수 있습니다.
선택 옵션 `--png`는 로컬 검토 도구 Pillow와 DejaVu 폰트가 있을 때만 사용하며,
게임 실행에는 필요하지 않습니다. 캡처는 실제 렌더러의 문자·색상 출력이며
사용자의 터미널 폰트에 따라 점 간격과 글리프 모양은 달라질 수 있습니다.

## 빌드 및 단일 실행 파일 (Single Executable)

`./build.sh` (또는 `python3 scripts/build.py`)를 통해 멀티플랫폼 단일 파일 패키지 및 OS 네이티브 바이너리를 원클릭으로 빌드할 수 있습니다.

```bash
# 단위 테스트 후 zipapp 및 Standalone 바이너리 모두 빌드
./build.sh

# 멀티플랫폼 범용 zipapp만 빌드 (dist/textris.pyz)
python3 scripts/build.py --mode zipapp

# Standalone 단일 실행 바이너리만 빌드 (dist/textris)
python3 scripts/build.py --mode binary
```

Windows 전체 회귀 검사는 `python -m unittest discover -s . -v`입니다.
Unix PTY 6개는 Windows에서 제외 사유를 표시하며, 실제 콘솔 검사는 별도로
`python scripts/windows_terminal_probe.py --output .antigravity/native-console-new`를 실행합니다.
출력 경로는 기존 증거를 덮어쓰지 않도록 새 디렉터리를 지정해야 합니다.
symlink 권한이 없으면 해당 3개 테스트를 명시적으로 제외하며 Windows junction 경계는 별도로 검사합니다.
감사 2의 설계와 실행 증거는 [수정 계획](docs/audit/audit_2_remediation_plan.md) 및
[재검증 보고서](docs/audit/audit_2_revalidation.md)를 참고하세요.

- **범용 zipapp (`dist/textris.pyz`)**: Python 3.10 이상과 miniaudio가 필요합니다. Windows에서는 windows-curses도 필요하며 소스의 `python -m pip install .`로 설치할 수 있습니다.
  - Linux/macOS: `./dist/textris.pyz` 또는 `python3 dist/textris.pyz`
  - Windows: `python dist\textris.pyz`
- **독립 단일 바이너리 (`dist/textris` / `dist/textris-linux-x86_64`)**: Python 인터프리터 설치 없이 직접 실행 가능한 완전한 네이티브 단일 실행 파일입니다.
- **CI/CD 및 GitHub Release 자동 배포**:
  - 지원 플랫폼:
    - **Linux x86_64** (`textris-linux-amd64`)
    - **Linux ARM64** (`textris-linux-arm64`, QEMU 컨테이너 빌드)
    - **Windows x64** (`textris-windows-amd64.exe`)
    - **macOS Apple Silicon** (`textris-macos-arm64`)
    - **범용 zipapp** (`textris.pyz`)
  - Git 태그(예: `git tag v1.1.0 && git push origin v1.1.0`)를 푸시하면 GitHub Actions 파이프라인이 위 5종 실행 파일과 `SHA256SUMS.txt`를 자동으로 빌드하여 **GitHub Release**에 등록합니다.

## 라이선스 (License)

Apache License, Version 2.0 (Apache-2.0)  
Copyright 2026 yupkidangju@gmail.com

소프트웨어의 라이선스와 개별 음원의 출처/이용 조건은 구분합니다. Bach Minuet 편곡
자산은 원전 디지털 판본을 따라 CC BY-SA 4.0이며, 상세 저작자·변경사항·악기 뱅크 고지는
[음악 attribution](textris/assets/audio/MUSIC_ATTRIBUTION.txt)에 있습니다.
효과음의 생성 요청·영수증·원본 해시는 `assets/audio-production/sfx`에 보존합니다.

