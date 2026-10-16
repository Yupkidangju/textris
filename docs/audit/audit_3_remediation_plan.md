# 감사 3 수정·재검증 계획

작성: 2026-10-16. 기준: 사용자 요청, 원본 `audit_report_3.md`, spec.md, D3D 구현/코딩/감사 표준.
기반: v1.4.0 / b02fe7e. 원본 보고서와 사용자 기록·설정·리플레이·음원은 보존한다.

## 수정 계약과 우선순위

1. AUD-006: Store는 데이터 디렉터리와 records.json의 링크를 존재 여부보다 먼저 검증한다.
   처음 선택한 부모의 정규 경로를 신뢰 기준으로 고정하며, 데이터 디렉터리 자체의 링크/정션,
   파일 링크, 이후 부모/디렉터리 재지정을 차단한다. load 실패는 save_read/read_only,
   save 실패는 save_write/False다. 임시 파일 생성과 교체 전에도 경계를 재검증한다.
   시스템의 정상 부모 경로 별칭과 상대 경로는 지원한다. 완전한 OS 수준 동시 경합 방지를
   주장하지 않으며 기존 링크와 load/save 사이 교체를 회귀로 검증한다.
2. AUD-003: windows_audio_probe는 실제 Audio worker/miniaudio/PcmMixer 진단을 사용한다.
   없는 구형 API patch를 제거하고, 재생·정지/재개·음량·큐/보이스 제한·종료를 검사한다.
   JSON 보고서와 명확한 의존성/장치 실패를 제공한다. OS 볼륨은 변경하지 않는다.
3. AUD-001: 미사용 particles 모듈, scenes의 구형 렌더 함수, 빈 reflection, set_intensity,
   App의 미렌더링 버퍼/난수/틱 훅을 제거한다. 실제 ArtDirector/Effects 출력·수명·경계의
   검사로 구형 테스트를 교체한다. NativePlayback 회귀용 synthesize는 보존한다.
4. AUD-004: 디코더가 필요한 검사에 miniaudio skipIf를 적용한다. 무음/실패 경계 검사와
   순수 PCM/셔플/자산 검사는 의존성 없이 계속 실행한다. 모듈 미설치 전체 스위트도 실행한다.
5. AUD-002/005: 전체 런타임 모듈 책임 표와 현재 영문/무음 계약, 8테마/설치 경로/프로브
   명령을 동기화한다. sdist는 핵심 문서/필요한 설계만 포함하고 증적/감사/PNG/log는 제외한다.
   증적 원본을 저장소에서 삭제하지 않는다. 모든 포맷의 활성 모듈/음원 포함을 검사한다.

## 작업 분리와 사전 경계 점검

기존 체크아웃의 codex/audit-3-remediation 브랜치에서 로컬 Windows 의존성과 제작 자료를
재사용한다. subagent-driven-development/dispatching-parallel-agents로 독립 작업을 분리한다.

| 작업 | 소유 파일 / 소비 계약 | 충돌 처리 |
| --- | --- | --- |
| 주 작업자: 보안 | storage.py, test_services의 Store 검사, test_windows_paths.py | AudioLifecycleTests는 테스트 작업자 전용 |
| 레거시 작업자 | particles/scenes/effects/audio(set_intensity만)/ui, 관련 UI/확장 검사, scripts/build.py | audio 기타 본문과 streaming 검사는 수정하지 않음 |
| 오디오 프로브 작업자 | scripts/windows_audio_probe.py, 신규 프로브 검사 | 현행 Audio 진단만 소비, audio 본문 변경 없음 |
| 의존성 검사 작업자 | test_soundtrack_audio/windows_audio/audio_portability, services의 AudioLifecycleTests | 보안 테스트 클래스는 수정하지 않음 |
| 주 작업자: 문서/패키지 | README/spec/summary/manifest/결정/검증 문서 | 다른 작업자는 문서를 수정하지 않음 |
| 최종 검토 | 전체 diff 및 사용자 Re-audit Checklist | 구현 후 독립 검토와 필요한 수정 |

AGENTS 메타데이터는 AUD-002의 현재 수정 요청 범위에서 값만 현행화한다. 정책 본문은
변경하지 않으며 추론한 프로젝트 환경·언어·문서 범위는 가정이라고 표시한다.

## 완료 기준

- 원본 보고서 SHA256 유지, AUD-001~006별 원인·수정·검사·판정을 별도 검증 문서에 기록.
- compileall, version, verify-audio-assets, 의존성 포함/미포함 전체 unittest.
- dangling/live symlink, 디렉터리 symlink/실제 Windows junction, load 이후 교체 및 원본 보존.
- 새 Windows audio probe 실제 실행/JSON, 실제 콘솔 입력/화면/종료 회귀.
- python -m build에 해당하는 wheel/sdist와 EXE/pyz 생성·자산·모듈·문서 목록 확인.
- 과거 패키징/태그 푸시 요청을 이어 하위 호환 수정 v1.4.1로 검증·제공한다.

## 진행

- 원본 보고서 및 실제 사용 경로 대조 완료. 코드 변경 전에 작성했다.
- AUD-001~004/006 구현·문서 동기화 및 독립 검토 완료. 저장 경로 25개와 실장치 프로브 통과.
- 전체 스위트: 포함 325개 OK(13skip), miniaudio만 차단한 전체 325개 OK(42skip).
- 보고서의 build.py particles 제외 조건은 실제 기반 코드에 없어 별도 예외를 만들지 않았다.
  실제 모듈 수와 MANIFEST 표현/기존 PYTHONPATH도 코드에 대조해 정정 근거를 재검증 문서에 기록했다.
- 패키지·Windows 콘솔·배포 게이트 진행 중.
- 최종 331개: 포함 318통과/13skip, 미포함 289통과/42skip. 모든 실패·오류는 0이다.
- 실제 새 EXE의 정션 대상 원본 보존, WASAPI 완료 및 외부 Python 경로 없는 실행을 확인했다.
  네 포맷의 활성 모듈 30개·음원 리소스 63개, 핵심 문서/설계 allowlist 검증도 통과했다.
- Windows 콘솔 첫 실행에서 6조건 통과 후 aurora의 failure_count=1을 감지했다.
  판정 조건을 완화하지 않고 장치 재시도의 원인을 보존하는 probe 관측을 추가해 독립 재실행한다.
- sdist 검사에서 이전 SOURCES.txt의 오래된 Markdown 항목이 남는 것을 확인했다.
  `prune docs` 후 필요한 설계만 명시적으로 재포함해 캐시 유무와 무관한 목록을 만든다.
- 빌드 검증에도 현재 소스 목록과 EXE/pyz의 모듈 목록 비교를 추가한다. 삭제된 모듈을
  특별 취급하지 않고 누락/잔존 모듈을 실패로 처리해 AUD-005의 포맷 일관성을 고정한다.
- 추가 검토에서 현재 Python 밖의 PATH/uv PyInstaller 빌드 경로도 확인했다. native 목록 검사는
  선택한 PyInstaller 환경의 archive_viewer CLI로 실행해 같은 fallback 지원을 유지한다.
