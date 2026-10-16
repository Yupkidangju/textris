# 감사 3 수정 재검증

작성: 2026-10-16. 기반 b02fe7e/v1.4.0, 수정 대상 v1.4.1.
범위: 사용자 제공 `audit_report_3.md`의 AUD-001~006 및 Required Fixes/Re-audit Checklist.
원본 SHA256: `50cc567e405110f5efc2dcf2d39daadb64ca16537882d151cf9dfa3b5ff27ff4`.
원본은 수정하지 않으며 기존 사용자 제공 파일의 추적 상태도 보존한다.

## 항목별 처리

| ID | 조치 | 현재 검증 |
| --- | --- | --- |
| AUD-006 | Store의 symlink/lstat mount-point 검사 후 exists, 부모 정규 위치 고정, mkdir/교체/정리 전 재검증 | 저장·Windows 경로 25개 OK, 권한 조건 symlink 5개 제외; 실제 junction 탈출/후기 교체/깨진 경로·확장 경로 포함 |
| AUD-003 | 공식 프로브를 miniaudio/Audio/PcmMixer/diagnostics로 교체, 실패 JSON/한정 대기/종료 보장 | 신규 7개 단위 검사와 실제 Windows 실장치 검사 통과, OS 상태 변경 없음 |
| AUD-001 | particles/구형 scenes 렌더러/reflection/intensity/미렌더링 버퍼 제거, 실제 cue·출력·만료 검사로 교체 | 관련 83개 OK(환경 skip 3), 전체 스위트 통과; synthesize native PCM 픽스처 보존 |
| AUD-002 | 30개 모듈 책임/영문 UI/무음 계약 통합, README 경로·8테마·명령, 실제 PYTHONPATH 기록 | 파일 목록과 표의 1:1 대조, AGENTS 메타데이터 값만 현행화·정책 본문 유지 |
| AUD-004 | decoder/장치 검사만 명시 skipIf; 순수 믹서/카탈로그/무음 검사는 유지 | 의존성 포함·미포함 전체 331개 OK, 미포함 3초 타임아웃 없음 |
| AUD-005 | 핵심 문서 포함, 증적 제외, 설계 allowlist와 현재 모듈 목록 검사 | 실제 sdist/wheel/EXE/pyz 모두 30개 활성 모듈 일치, 바이트코드/소스/음원 누락 없음 |

## 보고서와 실제 코드 대조 중 정정한 근거

- b02fe7e의 `scripts/build.py`에는 보고서가 언급한 particles 전용 제외 조건이 없다.
  실제 파일 삭제로 전체 빌드 포맷을 정리하고 예외 조건을 새로 추가하지 않았다.
- MANIFEST는 `recursive-include docs *` 형태는 아니지만 여러 증적 디렉터리를 명시적으로
  포함하고 있었다. 해당 include를 제거하고 prune/설계 allowlist로 실제 문제를 해결했다.
- 실제 Python 모듈 수는 수정 전 31개, particles 제거 후 30개다. 표는 실제 목록에 맞췄다.
- 기존 eight-themes 검증 문서에는 보고서가 인용한 잘못된 PYTHONPATH 행이 없었다.
  재현할 수 있도록 확인한 실제 두 의존성 경로를 명시적으로 추가했다.

## 재현 환경과 Re-audit Checklist

Windows, Python 3.14.3. 실제 로컬 의존성은 아래 경로다. miniaudio 1.71 및 windows-curses는
일반 설치의 의존성이고, 이번 경로는 기존 개발 체크아웃의 검증 환경에 한정한다.

```powershell
$env:PYTHONPATH="$PWD\.antigravity\audio-overhaul-20261008\deps;$PWD\.antigravity\audit-20261007-status\deps"
git status --short
python -m compileall -q textris tests scripts run.py
python -m textris --version
python -m textris --verify-audio-assets
python -m unittest discover -s . -v
python scripts/windows_audio_probe.py --output .antigravity/audit-3-remediation-20261016/windows-audio
```

- compileall/version/음원 검증: 종료 코드 0, 1.4.1, 26곡·30효과음·2,340초·47,790,454바이트.
- 의존성 포함 최종 전체 검사: **331개 / 52.627초 / 318통과·13제외 / 실패·오류 0**.
- 미포함 전체 검사: fresh Python subprocess의 meta_path에서 miniaudio만 차단했다.
  **331개 / 37.738초 / 289통과·42제외 / 실패·오류 0**, sys.modules 미로딩 확인.
  42제외는 기존 환경 조건 13개와 decoder/장치 의존 29개(출하 decoder 검사 포함)다.
  windows-curses는 두 환경에 동일하게 제공했다. 의존성을 제거하거나 OS 설정을 바꾸지 않았다.
- 실제 Windows 오디오 프로브: schema_version 2, passed/backend_completed=True, errors=[],
  모든 checks=True. 30 SFX 완료·쿨다운·6보이스 우선순위·위치 보존·무음 PCM·볼륨·감상 복귀·
  worker/device/decoder 정리를 확인했다. endpoint 전후 상태는 같고 직접 청취는 미확인이다.
- 신규 프로브 단위 검사 7개는 기본 Python/PYTHONPATH 없는 환경에서도 통과했다.

권한 없는 Windows에서는 실제 symlink 생성 일부를 제외한다. Windows junction 검사는 권한 없이
실행했고 외부 sentinel 내용/링크 원본/대상 디렉터리를 보존했다. 초기 부모의 정상 별칭은 신뢰
기준에 포함하고 이후 재지정은 차단한다. 완전한 OS 핸들 기반 동시 경합 방지를 주장하지 않는다.
Python 3.10 호환 근거: [pathlib](https://docs.python.org/3.10/library/pathlib.html#pathlib.Path.is_symlink),
[lstat/reparse 정보](https://docs.python.org/3.10/library/os.html#os.stat_result.st_reparse_tag).

미포함 검사는 저장소 루트의 새 프로세스에서 다음과 같이 재현할 수 있다(위 PYTHONPATH 유지).

```powershell
@'
import importlib.abc, sys, unittest
class NoMiniaudio(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "miniaudio" or fullname.startswith("miniaudio."):
            raise ModuleNotFoundError("dependency isolation: " + fullname, name=fullname)
sys.meta_path.insert(0, NoMiniaudio())
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover("."))
assert "miniaudio" not in sys.modules
sys.exit(not result.wasSuccessful())
'@ | python -
```

## 독립 검토

원본/계획/diff를 대조한 별도 검토에서 수정이 필요한 결함을 발견하지 못했다.
저장·Windows junction·프로브 실패 경계 29개(3 권한 skip)가 통과했고, 초기 부모 별칭 왕복과
상대 경로 Store가 chdir 이후에도 최초 위치를 지키는 동작도 확인했다.
검토는 실제 청취·다른 OS 실행·완성 패키지 검증을 대체하지 않는다.

추가 빌드 목록 검토에서 현재 Python 밖의 PATH/uv PyInstaller를 지원하는 경우를 발견했다.
native 검사도 선택된 환경의 archive_viewer CLI를 사용하도록 수정했으며, PATH/uv 정상 경로와
검사 실패 회귀를 포함한 빌드 검사 6개가 통과했다. scoped 재검토에 남은 지적사항은 없다.

## Windows 콘솔·실행 파일

첫 콘솔 실행에서는 6조건 통과 후 aurora에서 failure_count=1을 관찰했다. 첫 도구에는 재시도
이유 기록이 없어 당시 원인을 확정하지 못했다. 무실패 기준은 유지하고 원인 관측을 추가했다.
독립 새 실행은 **7조건 모두 통과, failure_count=0, audio_failures 없음**이다.
첫 실패 결과도 보존하며 모든 실행이 무실패였다고 해석하지 않는다. 오디오 재시도 정책과
오류/시간 제한을 완화하지 않았다.

새 EXE는 외부 PATH/PYTHONPATH 없이 1.4.1/음원 무결성/실제 WASAPI 완료를 확인했다.
실제 정션 데이터 디렉터리로 EXE를 시작하고 키 입력·종료한 뒤 외부 records.json의 SHA256
`f54693cb32014cf77e46069f0868ecf08cd631e6e48d9e003e82805c4b491aae`가 동일하고
외부 디렉터리에는 원본 records.json만 남음을 확인했다. 종료 코드는 0이다. 검사용 정션은 제거했다.

## 패키지 검사

프로젝트 로컬 build 1.6.1로 `python -m build --no-isolation --outdir dist/python-package`를 실행했다.
wheel은 새 sdist에서 만들어 이전 build/lib의 잔존 파일에 의존하지 않는다. builder의 EXE/pyz도
현재 모듈 목록과 비교한다. sdist/wheel/pyz의 소스 30개·오디오 리소스 63개 바이트가 현재 원본과
일치하며, EXE의 프로젝트 바이트코드도 누락·불일치가 없다. particles 특별 예외는 없다.
README/LICENSE/CHANGELOG/IMPLEMENTATION_SUMMARY/LESSONS_LEARNED/spec/designs/DESIGN_DECISIONS를 포함하고,
선택 설계 7개 외의 docs 증적 PNG/log/JSON 및 감사 원문은 포함하지 않는다.
MANIFEST 시작의 prune docs는 이전 SOURCES 캐시도 제거한다. 저장소의 기존 증적은 삭제하지 않았다.

## 남은 완료 게이트

AUD-001~006 수정과 로컬 Re-audit Checklist는 통과했다. 커밋·태그·CI·배포 결과를 이어 기록한다.
선별 원본 JSON은 `audit_3_evidence/`에 보존하며 sdist에 포함하지 않는다.
