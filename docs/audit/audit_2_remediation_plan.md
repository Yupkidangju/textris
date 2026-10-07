# 감사 2 수정 설계와 검증 계획

작성: 2026-10-07 (Asia/Seoul). 근거: 사용자 수정 요청, `audit_report_2.md`,
`spec.md`, `designs.md`, 실제 terminal/ui/audio/theme_art/storage 코드,
AI_IMPLEMENTATION_DOC_STANDARD.md, AI_CODING_STANDARD.md, AI_AUDIT_DOC_STANDARD.md.
상태: 구현 및 가용 Windows 재검증 완료. 결과와 남은 범위는
`audit_2_revalidation.md`에 기록했다. 기존 감사 산출물을 보존했고 커밋/게시하지 않았다.

## 대조 판정

| ID | 코드와 기존 계약의 대조 | 처리 |
| --- | --- | --- |
| T1 | Windows 강제 ASCII와 설정 OR 결합은 기존 정책을 구현했지만 최신 기본 타일 요구를 충족하지 못함 | 표시 계약 변경 |
| A1 | 외부 프로세스 재생은 기존 spec과 일치하지만 독립 실행 요구 미충족 | Windows native 백엔드 추가 |
| V1 | 공통 합성/보호는 구현됨. 다섯 테마 ceremony가 name/power/coords를 소비하지 않음 | 의미별 유한 연출 구현 |
| Q1 | Unix 모듈 import, symlink 권한, Windows 색상 비트와 표시 fixture 가정 문제 | 플랫폼 경계와 테스트 개선 |
| A2 | 정상 PCM/프로세스 종료만으로 짧은 효과음의 장치 출력·청취를 입증하지 못함 | native drain 및 진단 분리 |

## 표시 선택 계약 (T1)

- 설정 `display_mode`: `auto` / `unicode` / `ascii`. 기존 version 1 저장을 유지하며
  필드가 없으면 기존 `ascii=true`는 ascii, false는 auto로 이행한다. 기존 ascii 필드는 호환용으로 보존한다.
- 우선순위: 실제 인코딩 실패의 안전 폴백 > 세션 CLI --ascii/--unicode > 저장 선택 > 자동 정책.
- Windows 자동은 windows-curses의 wide-character 경로로 Unicode 타일을 기본 출력한다.
  Unix 자동은 UTF-8에서 Unicode, 나머지는 ASCII. Unicode 명시 선택은 출력 시도 후
  UnicodeError가 발생하면 이후 프레임까지 ASCII로 고정한다. 폰트 지원은 추정하지 않는다.
- 설정 화면에서 세 모드를 순환하고 유효 모드/안전 폴백 여부를 안내한다.
  CLI 모드는 저장 선택을 바꾸지 않는다. 보드/HOLD/NEXT/메뉴는 동일한 최종 모드를 사용한다.

## Windows 독립 오디오 (A1/A2)

- 추가 재생기/패키지 없이 stdlib ctypes + Windows winmm waveOut을 기본 선택한다.
  현재 PCM 합성/데이터 루트 검증을 재사용한다. 비Windows 외부 백엔드는 유지한다.
- 음악 1개 + 효과음 최대 3개의 독립 voice를 Windows 믹서에서 합성한다.
  PCM 버퍼와 WAVEHDR는 WHDR_DONE 또는 reset 확인 전 해제하지 않는다.
  종료는 reset → unprepare → close. 35ms move도 완료 flag까지 drain한다.
- 재생/정리는 오디오 worker에서 실행한다. pause/help/resize/confirm은 음악 정지,
  master mute/volume0/볼륨 변경은 활성 음성을 중단한다. close는 worker/핸들을 회수한다.
- 실패는 무음 상태로 표시한다. native 실패는 지연 및 제한 횟수로 재개를 시도하며
  새 voice는 기본 장치를 다시 선택한다. 장치 교체 중 무결점 연속 재생은 보장하지 않는다.
  독립 리뷰 보강: 같은 장치 이상으로 여러 활성 voice가 함께 실패하면 한 실패 사건으로
  집계한다. 새 재생 시도 실패는 각각 집계하며 세션 누적 3회에서 중단한다.
  정상 정리된 동시 실패가 재시도 전에 예산을 전부 소진하지 않도록 한다.
- audio-check는 백엔드 완료, 앱 설정, OS 출력 상태(조회 불가 시 unknown),
  실제 청취 미확인을 구분한다. OS 볼륨과 mute를 변경하지 않는다.
- waveOut은 유지보수용 Win32 API지만 무의존·소규모 PCM 플레이어에 필요한 기능을
  제공하므로 선택한다. 완전한 WASAPI 장치 관리와 초저지연 엔진은 이번 범위 밖이다.

## 테마별 성취 (V1)

공통 producer와 Cue 계약은 유지한다. clear/bloom/ascension/victory/eclipse/awakening을
다섯 테마에서 구분하며 기존 유한 수명/우선순위/주 연출 하나의 규칙을 지킨다.

| 테마 | 삭제 / Tetris·T-spin / 올 클리어 / 승리 / 종료 / 레벨업 |
| --- | --- |
| cyberpunk | 행 데이터 전송 / 격자 폭발 / 도시 상승 / 왕관 / 도시 붕괴 / 전원 상승 |
| space | 궤도 파동 / 초신성 / 상승 성운 / 별자리 왕관 / 수축 식 / 새 궤도 |
| fire | 행 불씨 / 화염 폭발 / 상승 기둥 / 불꽃 왕관 / 소멸 / 점화 |
| crt | 행 스캔 / 파형 폭발 / 상향 동기화 / 정상 신호 / 신호 붕괴 / 부팅 파동 |
| mono | 행 해칭 / 판화 확산 / 상승 선묘 / 기하 왕관 / 수축 음영 / 외곽 확장 |

- flash=false에서도 fx_intensity와 Cue.power가 기하 크기/밀도에 반영된다.
  clear 계열 coords는 보드 행 위치에서 출발하는 연출에 반영한다.
- 보호 영역, ASCII/모노, 작은 창, clipping, 게임/리플레이 결정성을 보존한다.
- 성취의 시각적 동등성은 단순 서명 수만으로 선언하지 않고 프레임과 실제 producer 경로도 확인한다.

## 구현 순서와 책임

1. 표시 선택/저장 이행 테스트 → terminal/storage/ui 및 CLI 표시 인자 연결.
2. 오디오 수명/실패 테스트 → native 백엔드/audio/check 진단. 표시 작업과 파일 경계를 분리한다.
3. 의미/강도/좌표 회귀 테스트 → theme_art. 기존 게임 규칙은 변경하지 않는다.
4. Windows fixture/Unix PTY 분리, symlink 권한 skip 사유와 별도 junction 경계 증거,
   전체 Windows discover를 CI에도 적용한다.
5. Windows 실제 curses 화면 버퍼·입력·저장/재시작·크기 변경 검사,
   native 장치 신호/루프/동시재생/정지, 새 exe·zipapp 빌드 및 실행 검사.
6. README/CHANGELOG/설계/구현 요약과 재검증 보고서에 근거 및 잔여 제한 기록.

## 완료 게이트와 리뷰 초점

- 새 회귀 테스트는 수정 전 실패와 수정 후 통과를 확인한다.
- Windows 전체 unittest discover, compileall, 실제 curses 및 native audio 검사를 실행한다.
- 외부 재생기 PATH 없는 상태에서 native 선택과 재생을 검증한다.
- 6테마 × 크기/표시 모드 보호 및 성취 구분, 입력·게임 상태 불변, 비용 측정.
- CLI 덮어쓰기 저장, 실패 시 buffer 수명, 음소거 큐 잔존, 기하 보호 침범,
  플랫폼 테스트 제외가 숨기는 범위를 중점 검토한다.
- Windows 10 실기, 사용자의 Windows Terminal/Cascadia Mono 픽셀, 실제 사람 청취,
  물리적 장치 탈착과 장시간 부하는 미실행 시 남은 검증으로 명시한다.

## 공식 근거

- https://github.com/zephyrproject-rtos/windows-curses — wide-character/UTF-8 빌드.
- https://learn.microsoft.com/en-us/windows/win32/multimedia/devices-and-data-types —
  waveOut 장치 선택·reset·unprepare/close 수명 및 새 엔진의 WASAPI 권고.
