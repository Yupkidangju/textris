#!/usr/bin/env python3
"""textris 빌드 스크립트.

멀티플랫폼 단일 실행 파일(zipapp) 및 네이티브 단일 실행 바이너리(PyInstaller)를 빌드합니다.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipapp

# Windows 및 다양한 환경에서 UTF-8 입출력 강제
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
ENTRY_POINT = "textris.__main__:main"


def log(msg: str) -> None:
    print(f"\033[1;34m[BUILD]\033[0m {msg}")


def log_success(msg: str) -> None:
    print(f"\033[1;32m[SUCCESS]\033[0m {msg}")


def log_error(msg: str) -> None:
    print(f"\033[1;31m[ERROR]\033[0m {msg}", file=sys.stderr)


def run_tests() -> bool:
    log("단위 테스트 실행 중 (python3 -m unittest discover -s .)...")
    res = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "."],
        cwd=ROOT_DIR,
    )
    if res.returncode != 0:
        log_error("테스트 실패! 빌드를 중단합니다.")
        return False
    log_success("모든 단위 테스트 통과!")
    return True


def clean_artifacts() -> None:
    log("이전 빌드 산출물 정리 중...")
    for d in (BUILD_DIR, DIST_DIR):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    for spec_file in ROOT_DIR.glob("*.spec"):
        try:
            spec_file.unlink()
        except OSError:
            pass
    DIST_DIR.mkdir(parents=True, exist_ok=True)


def build_zipapp() -> Path:
    """모든 플랫폼(Linux, macOS, Windows)에서 Python만 있으면 실행 가능한 단일 zipapp 아카이브 빌드."""
    log("멀티플랫폼 단일 zipapp 패키지 빌드 중...")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    output_pyz = DIST_DIR / "textris.pyz"
    output_bin = DIST_DIR / "textris-app"

    with tempfile.TemporaryDirectory() as td:
        bundle_dir = Path(td) / "bundle"
        shutil.copytree(ROOT_DIR / "textris", bundle_dir / "textris", dirs_exist_ok=True)
        # __pycache__ 제거
        for pycache in bundle_dir.glob("**/__pycache__"):
            shutil.rmtree(pycache, ignore_errors=True)

        zipapp.create_archive(
            source=bundle_dir,
            target=output_pyz,
            interpreter="/usr/bin/env python3",
            main=ENTRY_POINT,
            compressed=True,
        )

    # 실행 권한 부여
    try:
        current_mode = output_pyz.stat().st_mode
        output_pyz.chmod(current_mode | 0o755)
    except OSError:
        pass

    # 유닉스 편의를 위한 단일 실행 스크립트 복사본
    shutil.copyfile(output_pyz, output_bin)
    try:
        output_bin.chmod(output_bin.stat().st_mode | 0o755)
    except OSError:
        pass

    size_kb = output_pyz.stat().st_size / 1024
    log_success(f"Zipapp 빌드 완료: {output_pyz} ({size_kb:.1f} KB)")
    return output_pyz


def get_pyinstaller_cmd() -> list[str] | None:
    """사용 가능한 pyinstaller 실행 명령어 감지 (python -m PyInstaller, 시스템 pyinstaller 또는 uv 기반)."""
    # 1. python -m PyInstaller (현재 파이썬 환경과 정확히 일치하여 가장 안전)
    res = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode == 0:
        return [sys.executable, "-m", "PyInstaller"]

    # 2. 시스템 또는 현재 가상환경의 pyinstaller executable
    pyi_path = shutil.which("pyinstaller")
    if pyi_path:
        return [pyi_path]

    # 3. uv 확인
    uv_path = shutil.which("uv") or str(Path.home() / ".local" / "bin" / "uv")
    if Path(uv_path).is_file():
        return [str(uv_path), "run", "--with", "pyinstaller", "pyinstaller"]

    return None


def build_standalone_binary() -> Path | None:
    """OS 네이티브 Standalone 단일 바이너리(PyInstaller --onefile) 빌드."""
    log(f"네이티브 Standalone 단일 바이너리 빌드 중 (OS: {platform.system()} {platform.machine()})...")
    cmd_prefix = get_pyinstaller_cmd()
    if not cmd_prefix:
        log_error("PyInstaller 또는 uv를 찾을 수 없습니다. 독립 바이너리 빌드를 건너뜁니다.")
        return None

    os_name = platform.system().lower()
    arch = platform.machine().lower()
    base_name = f"textris-{os_name}-{arch}"
    if os_name == "windows":
        base_name += ".exe"

    pyi_args = [
        *cmd_prefix,
        "--name", "textris",
        "--onefile",
        "--collect-data", "textris",
        "--hidden-import", "_cffi_backend",
        "--hidden-import", "_miniaudio",
        "--exclude-module", "numpy",
        "--clean",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / "pyinstaller"),
        "--specpath", str(BUILD_DIR),
        str(ROOT_DIR / "run.py"),
    ]

    log(f"실행 명령: {' '.join(pyi_args)}")
    res = subprocess.run(pyi_args, cwd=ROOT_DIR)
    if res.returncode != 0:
        log_error("PyInstaller 빌드 실패!")
        return None

    built_target = DIST_DIR / ("textris.exe" if os_name == "windows" else "textris")
    if not built_target.exists():
        log_error(f"빌드된 바이너리를 찾을 수 없습니다: {built_target}")
        return None

    # 플랫폼 명시 이름의 복사본도 생성
    platform_specific_target = DIST_DIR / base_name
    shutil.copyfile(built_target, platform_specific_target)
    try:
        platform_specific_target.chmod(built_target.stat().st_mode | 0o755)
    except OSError:
        pass

    size_mb = built_target.stat().st_size / (1024 * 1024)
    log_success(f"네이티브 단일 바이너리 빌드 완료: {built_target} ({size_mb:.1f} MB)")
    log_success(f"플랫폼 전용 아티팩트 생성: {platform_specific_target}")
    return built_target


def verify_executable(executable_path: Path, is_python_script: bool = False) -> bool:
    """빌드된 실행 파일의 기본 인자(--version, --help) 및 동작 검증."""
    log(f"빌드 산출물 동작 검증: {executable_path.name}...")
    run_cmd = [sys.executable, str(executable_path)] if is_python_script else [str(executable_path)]

    # 1. --version 검증
    res_ver = subprocess.run([*run_cmd, "--version"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
    if res_ver.returncode != 0 or not res_ver.stdout.strip():
        log_error(f"{executable_path.name} --version 검증 실패 (코드 {res_ver.returncode})")
        return False

    # 2. --help 검증
    res_help = subprocess.run([*run_cmd, "--help"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    if res_help.returncode != 0 or "TEXTRIS" not in res_help.stdout:
        log_error(f"{executable_path.name} --help 검증 실패 (코드 {res_help.returncode})")
        return False

    log_success(f"{executable_path.name} 정상 검증 완료! (버전: {res_ver.stdout.strip()})")
    assets = subprocess.run([*run_cmd, "--verify-audio-assets"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    if assets.returncode != 0:
        log_error(f"{executable_path.name} 음원 무결성 검사 실패: {assets.stderr.strip()}")
        return False
    log_success(f"음원 목록/해시 검증: {assets.stdout.strip()}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="TEXTRIS 멀티플랫폼 단일 실행 파일 빌더")
    parser.add_argument("--mode", choices=["all", "zipapp", "binary"], default="all",
                        help="빌드 대상 선택 (기본값: all)")
    parser.add_argument("--skip-tests", action="store_true",
                        help="빌드 전 단위 테스트 건너뛰기")
    parser.add_argument("--clean", action="store_true", default=True,
                        help="이전 빌드 산출물 정리")
    parser.add_argument("--no-clean", dest="clean", action="store_false",
                        help="이전 빌드 산출물 유지")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT_DIR))
    from textris.asset_check import verify_audio_assets
    try:
        verify_audio_assets()
    except ValueError as exc:
        log_error(str(exc))
        return 1

    print("=" * 60)
    print("           TEXTRIS MULTI-PLATFORM BUILDER")
    print("=" * 60)

    if not args.skip_tests:
        if not run_tests():
            return 1

    if args.clean:
        clean_artifacts()

    built_files: list[tuple[Path, bool]] = []

    if args.mode in ("all", "zipapp"):
        zipapp_path = build_zipapp()
        built_files.append((zipapp_path, True))

    if args.mode in ("all", "binary"):
        binary_path = build_standalone_binary()
        if binary_path:
            built_files.append((binary_path, False))
        elif args.mode == "binary":
            return 1

    # 산출물 검증
    print("-" * 60)
    log("빌드 산출물 자체 검증 시작...")
    all_ok = True
    for path, is_py in built_files:
        if not verify_executable(path, is_python_script=is_py):
            all_ok = False

    print("=" * 60)
    if all_ok:
        log_success("모든 빌드 및 검증이 성공적으로 완료되었습니다!")
        print("\n[생성된 산출물 목록 in dist/]:")
        for p in DIST_DIR.iterdir():
            size = p.stat().st_size
            unit = "MB" if size > 1024 * 1024 else "KB"
            val = size / (1024 * 1024) if unit == "MB" else size / 1024
            print(f"  - {p.name:<30} ({val:.1f} {unit})")
        return 0
    else:
        log_error("일부 빌드 산출물 검증에 실패했습니다.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
