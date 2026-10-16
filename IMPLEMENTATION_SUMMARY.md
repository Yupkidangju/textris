# TEXTRIS 현재 구현 요약

갱신: 2026-10-16. 현재 v1.4.1(기반 v1.4.0), spec.md, 실제 textris/ 모듈 30개.
현재 계약만 기술한다. 과거 버전의 실험/검증 수치는 [이전 요약 스냅샷](https://github.com/Yupkidangju/textris/blob/b02fe7e/IMPLEMENTATION_SUMMARY.md)에 보존돼 있으며 현행 기능의 근거로 사용하지 않는다.
최신 수정 범위·검증 상태: `docs/audit/audit_3_remediation_plan.md`, `docs/audit/audit_3_revalidation.md`.

## 모듈 책임

| 파일 | 현행 책임 |
| --- | --- |
| `textris/__init__.py` | 제품 버전. |
| `textris/__main__.py` | CLI 옵션, Store/Audio 초기화, curses 실행과 종료·세션 override 복원. |
| `textris/art.py` | 문자/서브셀·깊이 합성, 팔레트, 보호 마스크, 단일/향후 복수 보드 좌표. |
| `textris/art_director.py` | 성공 사건의 우선순위·유한 주 연출/국소 cue와 플레이어 소유권. |
| `textris/art_ui.py` | 보호된 UI 프레임·타이틀·보드 장식과 상태 표현. |
| `textris/asset_check.py` | 26곡·30효과음 카탈로그/경로/파일 해시·수량 검증. |
| `textris/audio.py` | miniaudio 장치/decoder 소유권, 비동기 스트리밍·감상 제어·상태/진단. 실패 시 무음. synthesize는 native PCM 회귀 픽스처 전용. |
| `textris/audio_events.py` | 실제 UI/게임 사건의 효과음 라우팅·중복 억제·위험 진입 감지. |
| `textris/autoplay.py` | 전시용 블록 위치 평가와 결정적 명령 선택. |
| `textris/cathedral.py` | 대성당의 캐시된 환경과 유한 성취 형상. |
| `textris/effects.py` | ThemeScene/GalleryArt/ArtDirector 통합, 표시 상태·수명·적응형 품질. |
| `textris/engine.py` | 7-bag, 충돌/SRS/홀드/드롭, 착지 시간, 점수와 네 모드 종료. |
| `textris/expansion_ui.py` | Extras/갤러리/프로필/보스/리플레이/전시/분석/10개 감상 모음 화면과 입력. |
| `textris/gallery_art.py` | 19종 배경·25종 효과의 실제 갤러리 렌더링과 투영. |
| `textris/i18n.py` | 영문 단일 제품 문자열과 이전 언어 설정의 영어 이행. |
| `textris/replay.py` | 리플레이 형식/경로 검증, 원자 저장·보존, 결정적 재생·탐색. |
| `textris/scenes.py` | BACKGROUNDS/EFFECTS/PROFILES 카탈로그와 THEMES 재노출. 렌더러는 포함하지 않음. |
| `textris/session.py` | 고정 틱 세션·입력 기록·통계·checksum·하이라이트. |
| `textris/soundtrack.py` | 에셋 라이브러리/추출 캐시, 독립 셔플백, 제한된 PCM 믹서·큐·리미터. |
| `textris/storage.py` | version 1 설정·기록 검증/정렬/원자 저장, 링크·정션 차단과 손상 원본 보존. |
| `textris/terminal.py` | 폭 계산·클리핑·ASCII 안전 변환·표시 정책. |
| `textris/theme_actions.py` | 8테마별 조작·상태 문양과 제한된 잔상, 플레이어 효과 영역 준수. |
| `textris/theme_art.py` | 공유 환경·주 성취·조작·상태의 테마 합성·캐시·viewport 격리. |
| `textris/theme_atmosphere.py` | 기존 6테마의 누적 버퍼 없는 시간·거리 세부 층. |
| `textris/theme_nature.py` | 심해/오로라의 면·실루엣·6성취·T-spin·기포/눈. |
| `textris/theme_surfaces.py` | 테마별 면 명암/반사·축약 문양·회전 변주·품질별 표본. |
| `textris/themes.py` | 8개 시각 테마와 원본 6개 음악 모음 연결(abyss→space, aurora→mono). |
| `textris/ui.py` | App 입력/화면/고정 틱 통합, 실제 사건 소비·불투명 모달·같은 속성 구간 전송 생략. |
| `textris/visual_state.py` | 게임을 변경하지 않는 frozen 플레이어 표시 상태. |
| `textris/windows_audio.py` | waveOut 저수준 PCM 수명 회귀 경로, OS 출력 상태/endpoint 읽기 전용 진단. |

보조 진입점 `run.py`는 CLI를 실행한다. `scripts/build.py`는 zipapp/네이티브 빌드와 현재 소스 모듈 목록·버전·음원 무결성을 검사한다. PATH/uv로 PyInstaller를 선택하면 목록 검사도 그 환경에서 실행한다. pyproject.toml은 Python 3.10+/miniaudio/Windows 조건부 curses와 설치 진입점을 정의한다.

## 실행과 데이터 흐름

CLI → Store.load → Audio worker → curses.wrapper(App.run).
프레임마다 입력 → Session 고정 틱/engine → 실제 사건 → AudioEventRouter와 Effects → 보호된 최종 캔버스 → curses 출력이다.
게임 난수와 음악 셔플 난수는 분리한다. 시각/음악 선택은 게임 checksum·점수·리플레이에 영향을 주지 않는다.
장곡은 스트리밍하고 짧은 효과음만 적재한다. 파일 I/O/디코딩/장치 대기는 UI 루프에서 수행하지 않는다.
종료 시 worker/장치/decoder를 닫고 CLI override를 복원한 뒤 설정을 저장한다.

## 현재 기능과 보존 계약

- 제품 UI는 영어 단일이며 Unicode 아트와 ASCII/모노를 지원한다. Windows Auto는 Unicode 타일을 기본 사용한다.
- Marathon/Sprint/Ultra/Boss, 7-bag/SRS/HOLD/NEXT/ghost, 고정 틱·결정적 리플레이·분석·전시를 제공한다.
- 8테마(cathedral/cyberpunk/space/fire/crt/mono/abyss/aurora), 19배경·25효과, 최소 64×28이다.
- BoardViewport는 향후 두 보드용 좌표/효과 격리 계약이다. 실제 대전/AI 상대/온라인은 후속 범위다.
- 26곡 Ogg(2,340초)·30종 WAV, 음악/Classic 1:1 셔플, 10개 감상 모음을 사용한다. 새 자연 테마는 기존 space/mono 음악을 연결한다.
- 마스터/음악/SFX 음량, pause/help/confirm/resize 위치 보존, 최대 6효과음·우선순위·쿨다운·리미터를 적용한다.
- 장치나 decoder 실패는 무음과 상태로 안내한다. 외부 플레이어/네트워크/벨 fallback은 사용하지 않는다.
- Store version 1, 모드별 상위 10개와 원자 저장을 유지한다. 손상/링크는 읽기 전용 경고로 보존하고, 쓰기 직전에도 파일/디렉터리 경계를 재검증한다.
- 미사용 particles 모듈/구형 scenes 렌더러/빈 reflection/Audio intensity/미렌더링 App 버퍼는 감사 3에서 제거했다. 실제 효과는 ArtDirector·ThemeScene·GalleryArt·render_local/render_state가 담당한다.

## 검사·빌드·한계

`python -m unittest discover -s . -v`, compileall, CLI 음원 검증과 Windows 콘솔/오디오 프로브를 실행한다.
miniaudio가 없으면 decoder/장치가 필요한 검사만 명시적으로 skip하고 순수 PCM/카탈로그/무음 경계 검사는 계속 실행한다.
Windows 링크 생성 권한이 없으면 일부 symlink 검사를 제외하며, 실제 junction 검사를 별도로 실행한다.
sdist에는 핵심 문서와 선택한 설계·소스·테스트·음원 제작 메타데이터를 포함하고 감사 원문/증적 이미지·로그는 포함하지 않는다. 저장소의 증적은 보존한다.
최신 검사 수치·명령·패키지 파일 목록·잔여 제약은 재검증 문서에 기록한다. CPU 렌더와 터미널 출력 성능, PCM 제출과 직접 청취를 각각 구분한다.
