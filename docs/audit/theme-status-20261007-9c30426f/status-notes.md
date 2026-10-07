# 테마 현황 감사 증거

작성: 2026-10-07. 대상: `8fd1671` / TEXTRIS 1.1.0. 실행 환경: Windows 11,
Python 3.14.3, 감사 전용 프로젝트 로컬 windows-curses 2.4.2.
제품 소스/설정/사용자 저장 데이터 수정 없음. 모든 새 산출물은 이 폴더에만 작성했다.

## 판단

6개 테마 모두 새 공통 ArtCanvas/보호/서브셀/깊이/팔레트 경로로 확장되어 있다.
단순 색 교체가 아니라 서로 다른 배경 구도가 구현되어 있다. 그러나 다른 5테마의
성취 종류별 구조 변화와 강도 반응은 대성당보다 단순하다. `같은 품질`의 미적
동등성에는 정량 합격 기준이 없으므로 자동 테스트 통과로 동등성을 보증하지 않는다.

| 테마 | 현재 구도 / 코드 근거 | 공통 합성 | 성취 6종의 동일위상 셀 서명 수 |
| --- | --- | --- | ---: |
| Cosmic cathedral | 원근 아치, 장미창, 투영 천체 고리, 팔면체, 빛 커튼 / `textris/cathedral.py:28,62,88,115,153,181` | 확인 | 5 |
| Neon metropolis | 계단 도시, 원근 도로, 회전 와이어 큐브 / `textris/theme_art.py:48` | 확인 | 1 |
| Orbital observatory | 명암 행성, 중력 궤도, 천체 고리 / `textris/theme_art.py:75,98` | 확인 | 1 |
| Solar forge | 상승 불꽃, 태양 코로나, 불씨 / `textris/theme_art.py:111` | 확인 | 1 |
| Phosphor laboratory | 인광 계측 프레임, Lissajous 곡선, 회로, 스캔 / `textris/theme_art.py:135` | 확인 | 1 |
| Monochrome etching | 판화 윤곽/간섭 꽃무늬, 해칭, 겹친 다이아몬드 / `textris/theme_art.py:156` | 확인 | 1 |

## 생산자부터 최종 소비자

`App.process_events` (`textris/ui.py:514,523,528`) → `Effects.trigger`
(`textris/effects.py:55,56`) → `ArtDirector.trigger` (`textris/art_director.py:28,38,42,51`)
→ `App._background` (`textris/ui.py:195`) → `Effects.background`
(`textris/effects.py:88,103`) → `ThemeScene.render` (`textris/theme_art.py:15`)
→ `ArtCanvas.paint` (`textris/art.py:162`) → 보드/블록/HUD/모달
(`textris/ui.py:242,308`). 테마별 팔레트는 `textris/art.py:11,29`에서 생성하고
`textris/art_ui.py:9`에서 실제 속성으로 소비한다.

배경 구도 분기와 다르게, 대성당 외의 `ThemeScene.ceremony`
(`textris/theme_art.py:175-203`)는 `cue.name`, `cue.power`, `cue.coords`를 사용하지
않는다. `cue.phase(t)`에만 연결된 테마별 도형이다. 대성당은
`textris/cathedral.py:34-36,181-206`에서 종류·강도·행 좌표에 반응한다.
서로 다른 이벤트의 문구와 수명은 공통 ArtDirector/ArtUI에서 여전히 다르므로
전체 화면이 이벤트마다 동일하다는 뜻은 아니다 (`textris/art_ui.py:75-85`).

갤러리는 `ExpansionUI.gallery_trigger` (`textris/expansion_ui.py:40`) →
`Effects.background/draw` (`textris/effects.py:99,109`) → `GalleryArt.render`
(`textris/gallery_art.py:40`)로 19개 배경/25개 효과를 직접 소비한다.
예전 저해상도 `scenes.render`를 게임 배경에 연결하는 경로는 없다.

## 새 실행 증거

- `python -m unittest -v tests.test_theme_art tests.test_cathedral tests.test_gallery_art tests.test_auxiliary_art`
  : 31개 실행, 30개 통과, 1개 실패, 0.998초. 처음 의존성 없는 Python 실행은
  `_curses` import 실패 4건으로 실제 동작 테스트를 실행하지 못했다.
- 실패: `tests/test_cathedral.py:225`의 `n << 8` 색상쌍 모의 값과 Windows
  `curses.A_COLOR=-0x1000000`이 맞지 않는다. Linux 색상 비트 가정을 가진 테스트
  이식성 문제이며, 이 실패로 실제 블록 팔레트가 소실된다고 단정할 수 없다.
- `audit_runtime.py`: 종료 0. 현재 HEAD 대성당과 나머지 5테마를 같은 seed 42,
  같은 보드, 시각 100.6에서 실제 `App.draw` 호출로 60개 프레임 보존.
- 6테마 모두 idle→all-clear에서 보드 내부와 좌/우 HUD **문자** 동일.
  보드 프레임/성취/FEVER 상태의 변화는 비교 대상에서 제외했다.
- 64×28/80×30/120×40/160×50 × ASCII/Braille/비Braille × 6테마:
  **72개** 클리핑/보호 계약 모두 통과. ASCII 모드는 7비트 문자만 생성했다.
  실제 ASCII App.draw 최소/최대 캡처 12개도 7비트 조건 통과.
- 주 연출은 `clear/bloom/ascension/victory/eclipse/awakening`을 같은 시각,
  같은 위상 .5, 같은 power/coords로 직접 주입해 배경 셀·스타일·깊이 서명을 비교.
  대성당 5개, 나머지는 각각 1개. `runtime-results.json`에 원시 서명 기록.
- 섬광 OFF에서 intensity .25→1, ascension의 Cue.power 1→1.6:
  대성당만 셀 결과가 바뀌고 나머지 5테마는 동일했다 (`semantic-probes.json`).
- `git diff --check` 종료 0. 감사 중 제품 파일 변경 없음.

## 새 렌더 비용 측정

실제 App.draw, 120×40, 240프레임/테마, Unicode 명시, 동일 보드, 테트리스와
올 클리어 직접 주입. 색상쌍은 ncurses 비트로 모의, 출력은 RenderWindow.
터미널 전송/키 입력/폰트는 제외. 다른 감사 작업과 공유된 호스트이며 독점 실행이 아니다.

| 테마 | 평균 ms | p95 ms | 최대 ms |
| --- | ---: | ---: | ---: |
| cathedral | 8.046 | 11.972 | 54.779 |
| cyberpunk | 6.560 | 9.823 | 73.197 |
| space | 6.470 | 9.460 | 118.541 |
| fire | 5.416 | 9.269 | 10.655 |
| crt | 6.784 | 9.737 | 169.467 |
| mono | 3.760 | 8.563 | 9.678 |

현재 측정은 전부 p95 16.7ms 이내다. 최대 프레임 초과가 있으므로 고정 60FPS
보장은 아니다. 기존 `docs/terminal-art-verification.md:44-53`의 Linux mono p95
18.91ms 및 smoke 19.96ms는 이전 환경의 기록이고 이번 Windows 수치와 구분한다.
갤러리 44종의 새 성능 측정은 수행하지 않았다.

## 시각 검토 및 한계

`theme-contact.png`를 직접 검토했다. 6테마 모두 별도 실루엣/색 체계,
중앙 보드와 측면 HUD의 여백이 보인다. 대성당이 아치·천체·광막·장미창의
복합 구도를 유지하고, 다른 테마는 도시/행성/불꽃/계측/판화로 분화되어 있다.
이는 오프스크린 셀 시각 검토이며 미적 동등성의 보증은 아니다.

`frames.html`과 PNG는 현재 HEAD 대성당을 기준으로 나머지를 비교한 자료다.
업그레이드 전 Git 버전과 현재 버전의 before/after 비교는 수행하지 않았다.
PNG의 Braille은 실제 App.draw 셀 마스크를 2×4 점으로 그렸고, 나머지 글리프는
Windows Consolas/Segoe UI Symbol을 사용했다. curses 속성 비트는 기존 Linux
캡처 형식에 맞춰 모의했으므로 실제 Windows 터미널의 A_DIM/색/폰트 출력과 다를
수 있다. 실제 Windows terminal glyph, 오디오 청취, 출시/CI 상태는 이 부분감사 범위 밖이다.
