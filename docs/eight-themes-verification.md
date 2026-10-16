# 8테마·텍스트 효과 검증

작성: 2026-10-15. 대상 v1.4.0, 기준 `eight-themes-plan.md`.
근거: 실제 코드/검사 결과와 `.antigravity/eight-themes-20261015` 실행 자료.

재현 환경 기록 정정(2026-10-16): 로컬 검증에 사용한 의존성은 아래 실제 경로다.
아카이브 의존성 경로는 이 개발 체크아웃에만 해당하며 일반 설치는 `python -m pip install .`을 사용한다.

```powershell
$env:PYTHONPATH="$PWD\.antigravity\audio-overhaul-20261008\deps;$PWD\.antigravity\audit-20261007-status\deps"
python -m unittest discover -s . -v
```

## 구현

- 기존 6테마의 광점·반사·유성·재·인광·잉크 시간층을 강화했다.
- `abyss`: 발광 해파리와 촉수, 해저 능선, 수면 광선·물결, 기포·플랑크톤.
- `aurora`: 겹친 오로라 커튼, 설산·빙면 반사, 눈송이·결정 가지.
- 8테마 조작은 주 문양 뒤에 최대 두 개의 수명 기반 잔상을 그린다. 누적 버퍼가 없고
  기존 조작 180회/상태 260회 brush 예산과 보드별 보호 경계를 유지한다.
- 메뉴/Profiles/CLI/저장/음악 감상에 새 테마를 연결했다. 시각 ID와 음악 모음을 분리해
  abyss는 space, aurora는 mono의 기존 3곡을 사용한다. 게임의 Classic 1:1 셔플은 유지한다.
  10개 감상 모음 중 새 두 모음에는 원래 음악 분류를 안내한다. 26곡/30효과음은 그대로다.

## 검증 결과

| 검사 | 결과와 범위 |
| --- | --- |
| 전체 단위 검사 | 306개 중 296 통과, 10 명시적 skip, 64.157초 |
| skip | Unix PTY 6개, Windows 심볼릭 링크 권한 4개; Windows junction 검사는 통과 |
| 조작 회귀 | 기존 17개 + 신규 10개 통과, 8테마의 형태/수명/강도/품질/영역/예산 |
| 장면 회귀 | 관련 34개 통과, 신규 9개 포함, 6성취·spin·삭제 행·미래 보드 격리 |
| 음악·저장 통합 | 신규 4개 및 감상/UI/오디오 회귀 통과; 매핑 제거 mutation도 탐지 |
| 게임 사건·화면 | 48개 생산 경로, 576개 테마/성취/크기/표시 조건 통과 |
| 상태·미래 배치 | 112프레임 생성, game/session checksum 유지; 실제 대전 게임은 없음 |
| Windows 테마 버퍼 | 144개 조건 통과, Unicode/ASCII/모노의 보드·HUD 보호 |
| Windows 넓은 문자 | Unicode/ASCII 12조건에서 증분 출력과 전체 재출력의 버퍼 동일; 인코딩 fallback 없음 |
| Windows 입력/오디오 | 7개 App.run 시나리오 통과, 새 두 테마의 CLI·조작·정지·재시작·종료와 음악 연결 |
| Windows 감상 | 64×28/120×40 × ASCII/모노 4개 조건 통과, 조건별 10모음·재생/탐색/음량/복귀 |
| 음원 무결성 | 26곡/30효과음, 2,340초, 47,790,454바이트 |
| 정적 검사 | compileall과 git diff --check 통과 |
| 독립 검토 | 통합 및 전체 변경 검토 완료; probe의 고정 모음 인덱스와 import 범위 수정 후 잔여 결함 없음 |

Windows 입력 검사는 콘솔 입력 큐와 실제 App.run/오디오 worker를 사용한다. 버퍼 검사는
실제 curses 출력이지만 물리 키보드·특정 터미널 폰트의 촬영을 뜻하지 않는다.
음악 연결은 실제 백엔드와 상태로 확인했으며 새 음원 제작·39분 전곡 재청취는 이번 범위가 아니다.
OS 음소거·볼륨은 변경하지 않았다.

## 시각 검토

120×40 새 테마의 실제 App.draw 이미지와 두 테마의 6성취 contact, 64×28 Unicode/ASCII,
향후 두 보드 64×28/120×40 이미지를 검토했다. 해파리의 둥근 종·촉수와 오로라의 가로 커튼·
뾰족한 산이 구분되며, 보드/HOLD/NEXT/숫자/안내에 침범하는 문제는 발견하지 못했다.
PNG는 문자 버퍼·정확한 Braille 마스크·로컬 폰트로 만든 검토물이며 네이티브 스크린샷은 아니다.

## 성능과 배포

초기 CPU 측정에서 cathedral p95 21.477ms, 후속 측정에서는 23.239ms로 목표를 넘었다.
프로파일 결과 120프레임 중 모의 색상 호출 46,320회가 기록 객체를 쌓으며 0.719초를 사용했다.
`scripts/theme_ceremony_probe.py`의 색상 변환을 같은 값을 반환하는 함수로 바꾸었다.
제품 렌더러·품질 기준은 그대로이며, 전후 PNG 80개 SHA256이 모두 같았다.
검사 도구의 호출 기록 비용을 제거한 CPU 측정(120×40, 테마별 240프레임)은 다음과 같다.

| 테마 | 평균 ms | p95 ms |
| --- | ---: | ---: |
| cathedral | 6.440 | 11.233 |
| cyberpunk | 5.481 | 12.084 |
| space | 4.887 | 9.831 |
| fire | 5.982 | 12.932 |
| crt | 4.283 | 8.580 |
| mono | 5.238 | 11.220 |
| abyss | 4.616 | 8.905 |
| aurora | 5.956 | 12.759 |

8테마 모두 CPU p95 목표 16.7ms 이내다. Windows 출력 포함 측정은 별도이며 모든 터미널에서
같은 프레임 속도를 보장하지 않는다. 보정 전 결과도 `eight-themes-evidence/uncalibrated-cpu.json`에 남겼다.

Windows 출력 포함 최종 부하: 128초 목표, 실제 128.092초 / 6748프레임이다.
2초마다 성취를 바꾸고 국소 동작/피버/콤보를 겹쳐 같은 적응형 품질 정책으로 검사했다.
모든 테마에서 보드/HUD·게임 checksum·국소 큐 상한을 유지했다.

| 테마 | 프레임 | 출력 포함 p95 ms | 마지막 품질 |
| --- | ---: | ---: | ---: |
| cathedral | 761 | 55.357 | 0.595 |
| cyberpunk | 837 | 26.871 | 0.520 |
| space | 877 | 25.896 | 0.545 |
| fire | 834 | 26.131 | 0.400 |
| crt | 888 | 21.464 | 0.460 |
| mono | 928 | 12.209 | 1.000 |
| abyss | 859 | 22.321 | 0.540 |
| aurora | 764 | 54.601 | 0.585 |

일부 테마는 출력 포함 60FPS 목표(16.7ms)를 충족하지 못한다. CPU 목표 통과를 네이티브
출력 목표 통과로 해석하지 않는다. 전송 최적화는 같은 속성 구간을 생략하며, 전후 PNG 80개와
Windows 넓은 문자 12조건이 전체 재출력과 같았다. 이전 부하도 native-load-before.json에 보존한다.
추가적인 네이티브 출력 최적화는 후속 성능 작업으로 남긴다.

## 로컬 패키지와 EXE

`scripts/build.py --mode all --no-clean --skip-tests`, pip wheel, setuptools sdist를 완료했다.
EXE/pyz/wheel/sdist의 63개 오디오 리소스와 원본 해시가 같고 새 themes/theme_nature/
theme_atmosphere 모듈과 디코더가 포함된다. 31개 Python 소스를 대조했으며 EXE에서 제외되는
미사용 legacy `textris.particles` 외에 누락·바이트코드 불일치가 없다.

| 로컬 산출물 | 바이트 | SHA256 |
| --- | ---: | --- |
| Windows EXE | 56,874,927 | `da84e2094d9aab06d082c4daad81d33c6a7c64789df697829b26a95bb9c40c0d` |
| pyz / textris-app | 46,375,777 | `11d040fa862b247260821cc4fef36fd529bfca38a379a52223e6e03fba395f52` |
| wheel | 46,385,020 | `c14b8ecce070d5d320d02f7e0ba7466f22ecd91a5bbc126366f4f395589af26e` |

외부 PATH/PYTHONPATH를 비우고 EXE의 version/음원 무결성/실제 WASAPI 완료를 확인했다.
버전 실행은 2.355초, 오디오 검사 2.786초였고 프로세스군 Working Set은 100ms 표본에서
최대 51,212,288바이트였다(게임 장시간 메모리 상한을 뜻하지 않는다).
OS 출력은 기존 음소거/39% 상태였으며 변경하지 않았다. 직접 청취는 미확인이다.

실제 EXE PTY에서 심해 ASCII와 오로라 Unicode를 각각 실행해 새 장면·이동·회전·홀드·드롭·
일시정지·종료를 확인했다. 두 번 모두 종료 코드 0이고 CLI 테마/무음 override는 기존 저장 선택으로
복원됐다. 심해에서는 도움말 복귀도 확인했다. 기록/리플레이 사용자 디렉터리는 사용하지 않았다.

## 원격 태그와 배포본 검증

기능 커밋 `b484e0f96824ce10bf38a58ebe823b39152e0abd`를 main에 fast-forward하고
annotated tag `v1.4.0`과 함께 원격으로 atomic push했다. 태그 객체는
`d66aaaac533049d892b8cd38b4830c5d9c857971`이다.

[태그 CI](https://github.com/Yupkidangju/textris/actions/runs/38690811297)의 Windows 산출물을
직접 받아 외부 PATH/PYTHONPATH 없이 version/63리소스·새 모듈·디코더/실제 WASAPI 완료를 확인했다.
이 EXE는 56,167,306바이트이고 SHA256은
`407bef86bb2abd04ec0de8fdcb7e610ac06dc6af57a01704a97a634b4abaffa7`이다.
로컬 Python 3.14 빌드와 CI Python 3.12 빌드의 크기·해시는 다르므로 별도로 기록한다.

CI EXE의 Unicode 오로라 배경과 Extras 감상 10모음, Traditional Tetris 8곡,
오로라 3곡과 원래 Monochrome etching 안내, 마스터 음소거 상태의 감상·복귀·정상 종료를 확인했다.
실제 청취는 미확인이다.

태그 CI `38690811297`과 main CI `38690811066`이 모두 성공했다. 단위 검사와 Windows,
Linux x86-64/ARM64, macOS ARM64, zipapp 및 릴리스 게시가 완료됐다.
[v1.4.0 릴리스](https://github.com/Yupkidangju/textris/releases/tag/v1.4.0)는
2026-10-15 06:21:16 UTC에 공개됐다. 바이너리/pyz 5개와 SHA256SUMS.txt를 포함한
6개 자산의 GitHub digest를 검증했으며, Windows 게시 파일은 실제 실행한 CI 산출물과 같다.
배포 목록과 해시 대조는 `eight-themes-evidence/release.json`에 기록했다.

기능과 패키징·태그 푸시·배포를 완료했다. 남은 제한은 위에 명시한 일부 콘솔의 고부하 출력
프레임 목표 미달과 물리 폰트/직접 청취 미확인이다. 실제 배틀 게임은 후속 범위로 유지한다.
