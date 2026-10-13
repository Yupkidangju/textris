# 테마 표현 고도화 구현 계획

> Agentic workers: superpowers:subagent-driven-development로 작업과 검토를 수행한다.

Goal: 승인된 여섯 테마의 표현을 강화하고 작은 창의 식별성과 향후 복수 보드 렌더 확장 지점을 확보한다.
Architecture: 레이아웃/보호 영역, 읽기 전용 시각 상태, 공용 환경, 테마별 국소·성취 효과를 분리한다.
Tech stack: 기존 Python 3.10+/curses/ArtCanvas. 제품 의존성·음원 추가 없음.
Spec: `spec.md`, `theme-enhancement-layout-design.md`, `audit/theme_enhancement_review_20261014.md`.

## 공통 제약

- 현재 싱글플레이 기능·게임 규칙·테마ID·저장version1·게임난수·리플레이·26곡/30효과음을 유지한다.
- 실제 배틀/AI/온라인 메뉴·게임·저장 필드를 추가하지 않는다. 예정 복수 보드 좌표 계약만 제공한다.
- 최소64×28, Unicode/ASCII/모노, flash/shake/F OFF와 축소 정지를 보존한다.
- 한 플레이어 주 연출1개/국소8개, 성취 최대1.8초, 정해진 수명·캐시·입자 상한을 지킨다.
- 조작 효과는 성공 사건만 사용한다. 위험/피버 진입·유지·종료를 표현 전용 상태로 전달한다.
- 표시만의 시간/난수를 사용한다. 생략된 효과로 미완료 항목을 완료 처리하지 않는다.
- 기존 패키징·태그 푸시 요청을 이어서 검증 후 하위호환 v1.3.0으로 제공한다.

## 동결 인터페이스

- `art.BoardViewport(player_id, board_rect, hud_rects=(), effect_regions=())`: frozen dataclass.
  board_rect=(x,y,22,22). `board` 속성은(x,y). effect_regions는 플레이어 전용 허용 영역이다.
- `Layout`의 기존board/origin/protected는 보존하고viewports tuple을 추가한다.
  `game_layout(w,h)`는현재원점을유지하되 HUD의 실제 정보만 보호한다.
  `battle_viewports(w,h)`는예정2보드배치만 반환하며 제품 화면에 노출하지 않는다.
- `RenderContext`의기존위치인자는보존한다. trailing `viewports=()`와 `clip_rect=None`를 추가한다.
- `visual_state.VisualState(player_id='p1', danger=False, fever=False, combo=0, b2b=False, level=1)`:
  immutable 표시 상태. `theme_actions.render_local(canvas,board,t,cue,theme,intensity,flash)`와
  `render_state(canvas,t,theme,state,viewport=None,*,intensity=.75,flash=True)`는테마별 표시만 수행한다.
- `ThemeScene.render`의기존인자를유지하고 keyword-only `state=None`을 추가한다.
  배경은한번 생성하고 state/국소효과는해당viewport의영역에한정한다.
- `Cue`는 trailing `player_id='p1'`, `variant=''`를 추가한다.
  같은급 주 연출은수명연장없이최신label/coords/variant와강도를반영한다.
  기존 상위 연출은낮은급 사건으로교체하지 않는다.
- 배경의 조명·잔상·반사·열기는문자 명암·밀도·좌표·깊이로구현한다.
  quality는곡선표본/거리층/국소상세에도 적용하고 낮은값에서일부테마를제거하지않는다.

## 작업과 검토

### 1. 레이아웃·합성·사건 경계 (주 작업자, 완료)
- Files: art.py, art_ui.py, ui.py, effects.py, art_director.py, new visual_state.py.
- [ ] 실패 검사: 최소 창에 배경 공간/6테마의 가시성, 정확한HUD/보드보호, 복수viewport비중첩.
- [ ] ASCII 선방향·서브셀명암과저품질 예산; 같은급 사건의최신의미; 상태전달과게임불변.
- [ ] 구현 후 기존 회귀+새 검사, 독립 검토, 필요한 수정.

### 2. 테마별 배경·성취 (배경 작업자, 완료)
- Files: theme_art.py, cathedral.py, new theme_surfaces.py; tests/test_theme_enhancement.py.
- [ ] 실패 검사: 대성당6종의미/강도/행 좌표, 모든테마의면·거리층/시간변화/저품질/작은창.
- [ ] 스테인드글라스·네온면광/반사·행성고리가림/성운·화염면/용암·인광/주사·판화해칭.
- [ ] render_state/render_local을연결하고T-spin/Tetris/일반삭제변주를구별한다.
- [ ] 기존테스트와전용회귀, 주 작업자 시각/성능검토, 피드백수정.

### 3. 테마별 조작·상태 (조작 작업자, 완료)
- Files: new theme_actions.py; tests/test_theme_actions.py.
- [ ] 실패 검사: move/drop/lock/rotate/hold/focus의테마별형태, 수명/강도/ASCII/보호.
- [ ] 위험·회복, combo/B2B, fever, level의상태형태/시간/설정 반응과viewport격리.
- [ ] 테마별국소효과/상태효과, bounded입자/잔상; 기존좌표계와인터페이스 유지.
- [ ] 전용회귀, 독립 검토, 필요한 수정.

### 4. 통합·Windows·배포 (주 작업자와 최종 검토자)
- [ ] 검사용Windows버퍼의UTF-8/CP949오판을수정하고보드/HUD/입력/정지/설정경로 확인.
- [ ] 6테마×상태/성취×64/80/120/160×Unicode/ASCII/모노/flash OFF/저품질 캡처와시각검토.
- [ ] 120×40 p95 16.7ms의CPU목표, 실제출력별도측정. 미달은원인조정후재측정한다.
- [ ] 전체회귀/컴파일/장기동시효과/리플레이·난수불변/실행종료와프레임예산 검사.
- [ ] README/CHANGELOG/spec/design/검증문서, 패키지·EXE 내용과실제실행, 커밋/태그/CI/릴리스.

## 구현 전 검토와 작업 분리

| 공유 경계 | 생산/소비 | 판정 |
| --- | --- | --- |
| 작업1→2/3 | BoardViewport/RenderContext/VisualState | 위의형식에동결. 작업자는이형식으로회귀를먼저작성한다. |
| 작업3→2 | theme_actions.render_local/render_state | 작업2는호출부만수정하고작업3파일을수정하지않는다. |
| 작업1→2 | state keyword와legacy board원점 | 호환기존인자유지. 작업1은ThemeScene의본문을수정하지않는다. |
| 작업2→4 | theme_art/cathedral의출력 | 성취·작은창·모노검토는캡처와실제Windows에서추가한다. |
| 작업1/2/3→4 | 파일별소유권과검증 | 별도파일/별도테스트. root가통합하고커밋·푸시만담당한다. |

Ruling: 원점을유지한정교한HUD보호와테마문양으로작은창문제를해결한다.
현재HUD/게임조작을전면교체하지않아회귀위험을줄인다.
Ruling: 복수보드의공간함수와viewport격리를현재구현하되, 실제2게임진행은사용자설명대로후속범위다.
Ruling: 성공한이동의국소효과도추가해승인된점검보고서의이동/회전/홀드/드롭/착지계약을완성한다.
이동은짧은0.12초의연출이며기존국소8개예산안에포함한다.
Ruling: 실제Windows출력비용에대응해완성캔버스의변경행만전송한다.
정밀변경셀추적은단편화·추적비용이커서행단위비교/속성구간전송으로대체한다.
넓은문자의소유/연속셀을행과함께갱신하며초기/크기/팔레트/출력실패시전체화면을다시보낸다.
정적프레임무전송·삭제문자제거·Unicode폭·리사이즈·오류후복구를회귀로고정한다.
