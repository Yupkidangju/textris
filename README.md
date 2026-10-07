# TEXTRIS

키보드로 플레이하는 터미널 테트리스. 컬러 블록과 텍스트 애니메이션,
직접 합성한 효과음·배경음악을 제공합니다. Python 표준 라이브러리만 사용합니다.

기본 미술 테마는 **우주 대성당**입니다. Braille 곡선의 장미창, 원근 아치,
깊이가 있는 천체 고리, 빛 커튼과 성취에 반응하는 문자 아트가 보드를 감쌉니다.
권장 화면은 **120열 × 40행**, 최소 화면은 64×28입니다.

```bash
python3 -m textris --theme cathedral
```

이미 저장한 테마는 보존됩니다. 위 명령은 이번 실행에만 대성당을 적용합니다.
계속 사용하려면 **E → 연출과 테마 → 테마 → 우주 대성당**을 선택하세요.
기존 테마와 18종 배경·25종 효과도 갤러리에서 사용할 수 있습니다.

[컬러 연속 프레임 미리보기](docs/cathedral-preview.html) ·
[플레이 화면](docs/cathedral-idle.png) · [올 클리어](docs/cathedral-all-clear.png)

대성당에서는 보드의 빈칸과 HUD를 안정적으로 유지하고, 하드 드롭에는 빛 기둥,
테트리스/T-spin에는 장미창 개화, 올 클리어에는 공간이 펼쳐지는 고리를 표시합니다.
효과가 겹쳐도 주 연출은 하나이며 게임 입력과 시간을 멈추지 않습니다.
256색이 없으면 기본 색상으로, Braille을 끄면 점/선 문자로 대체합니다.
`--ascii`, 모노 설정, 흔들림·섬광 옵션과 **F** 효과 토글도 지원합니다.

```bash
cd /home/eunho1/Projects/textris
python3 -m textris
```

Python 3.10 이상, Linux/macOS의 대화형 터미널이 필요합니다. Windows에서는 WSL로 실행하세요.
터미널 크기는 최소 **64열 × 28행**입니다. 창을 줄이면 게임과 시간이 멈춥니다.
`python3 run.py`도 같은 게임을 실행합니다. 기본 화면은 한국어입니다.

- 마라톤: 10줄마다 레벨 상승, 시작 레벨 1~15.
- 스프린트: 40줄 완료 시간 도전.
- 울트라: 120초 점수 도전.
- 7-bag 블록, SRS 벽 차기, NEXT 5개, HOLD, 고스트, 0.5초 착지 지연.
- T-spin, Tetris 연속 보너스, 콤보, 올 클리어와 최고 기록.
- 감쇠 보드 흔들림, 착지 섬광·충격파, 블록 파편·폭죽, 상승 점수와 대형 문자 아트.
- 문자 비·플라스마·별 터널·와이어프레임 배경, 사인파 문자 리본과 색 순환.
- 움직이는 타이틀, 준비 카운트다운, 드롭 잔상, 줄 삭제 점멸, 콤보·레벨·승리·게임 오버 연출.
- 메뉴 **V**: 연출 쇼케이스. **E**: 확장 허브(갤러리·테마·보스·리플레이·자동 전시).
- **19종 배경 + 25종 효과**: Braille 점 입자, 회전 큐브·토러스·입체 블록, 프랙털 줌,
  오로라·유체·메타볼·문자 도시·입체 로고·수면 반사.
- 균열·셀 분해·벽/바닥 파편 충돌·연쇄 폭발·번개·블랙홀·글리치·연기·불꽃.
- 블록별 전용 궤적, 콤보 고조·8초 피버·상단 위험 경고·음악 박자 이퀄라이저.
- 피버와 테마는 기존 세 모드의 점수·중력·착지 규칙을 바꾸지 않습니다.
- 별도 보스: 팔 2개와 코어를 줄 삭제로 파괴. 각 60 HP, 제한 시간 180초.
- 자동 리플레이, 배속·구간 이동·주요장면 카메라, 점수 그래프·콤보 타임라인.
- 합법적인 입력으로 움직이는 자동 플레이 전시. 전시·감상은 순위 기록을 만들지 않습니다.
- 일시정지, 조작 도움말, 재시작/종료 확인, 모드별 상위 10개 기록.
- 한국어/영어, Unicode/ASCII 블록, 컬러/모노, 전체 사운드/음악/음량 설정.

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
설정은 확장 허브 또는 설정의 **연출과 테마**에서 바꿉니다.

리플레이에서는 Space/P로 정지, ↑↓로 0.5/1/2/4배속, ←→로 ±5초 이동,
C로 주요장면 카메라, A로 분석합니다. 분석의 방향키/Enter로 주요장면을 재생합니다.
자동 전시는 P로 정지, Esc로 허브에 복귀하며 게임 오버 뒤 자동으로 재시작합니다.
기존 설정·기록 파일은 그대로 호환됩니다.

```bash
python3 -m textris --language en
python3 -m textris --ascii --no-sound
python3 -m textris --seed 42
python3 -m textris --audio-check
python3 -m unittest discover -v
```

효과음과 창작 배경음악은 실행 중 WAV로 합성합니다. 설치된 `paplay`, `aplay`,
`ffplay`, `afplay` 중 하나를 자동 사용합니다. 재생기가 없거나 장치가 재생에 실패하면
터미널 벨로 전환하며, 벨 사용 여부는 터미널 설정을 따릅니다. 음악은 일시정지와
작은 창에서 멈추고 종료 시 재생 프로세스를 정리합니다. `--audio-check`는 실제
장치 재생을 시험하며 재생 실패 시 종료 코드 1을 반환합니다.

리플레이는 `.textris-data/replays/`에 최근 20개를 보관합니다. 한 게임당 최대
2MiB·10만 명령·2시간이며, 한도나 저장 실패는 플레이를 중단하지 않습니다.
리플레이는 고정 60Hz 명령 기록과 최종 상태 체크섬으로 재생 결과를 확인합니다.

설정/기록은 프로젝트 내부 `.textris-data/records.json`, 생성 음원은
`.textris-data/audio/`에 저장됩니다. `--data-dir 경로`로 저장 위치를 지정할 수 있습니다.
`--no-sound`와 `--ascii`는 해당 실행에만 적용됩니다. 저장 파일이 손상됐으면
원본을 보존하고 화면에 안내합니다. 게임 종료 후 해당 파일을 직접 다른 이름으로
옮기면 다음 실행에서 새 기록 파일을 만들 수 있습니다.

점수는 일반 1/2/3/4줄 100/300/500/800 × 레벨, T-spin 0/1/2/3줄
400/800/1200/1600 × 레벨입니다. 마지막 성공 행동이 회전이고 T 중심의
대각선 4곳 중 3곳이 막혔을 때 T-spin으로 판정하며 미니는 별도로 구분하지 않습니다.
연속 Tetris/T-spin 삭제는 1.5배, 콤보는 두 번째 연속 삭제부터 50×콤보×레벨,
올 클리어는 3500×레벨을 더합니다. 소프트/하드 드롭은 이동한 줄당 1/2점입니다.

구조와 검증 근거는 [spec.md](spec.md), [designs.md](designs.md),
[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)를 참고하세요.

전체 장면 캡처는 [갤러리 검증](docs/maximal-fx-gallery.txt), 확장 구현 계약은
[최대 연출 계획](docs/maximal-effects-plan.md)을 참고하세요. 렌더링 비용은
`python3 -m tests.benchmark_effects`로 측정할 수 있습니다(터미널 전송 비용 제외).


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

- **범용 zipapp (`dist/textris.pyz`)**: Python 3.10 이상이 설치된 모든 OS(Linux, macOS, Windows)에서 추가 설치 없이 단일 파일로 실행할 수 있습니다.
  - Linux/macOS: `./dist/textris.pyz` 또는 `python3 dist/textris.pyz`
  - Windows: `python dist\textris.pyz`
- **독립 단일 바이너리 (`dist/textris` / `dist/textris-linux-x86_64`)**: Python 인터프리터 설치 없이 직접 실행 가능한 완전한 네이티브 단일 실행 파일입니다.
- **GitHub Actions**: Windows / macOS / Linux 3대 OS 전용 바이너리가 Push / Release 시 자동 매트릭스 빌드됩니다.

## 라이선스 (License)

Apache License, Version 2.0 (Apache-2.0)  
Copyright 2026 yupkidangju@gmail.com

