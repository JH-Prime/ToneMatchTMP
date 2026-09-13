"""명시적으로 지정한 검증된 Zig C++ 도구로 Windows x64 DSP DLL을 만든다."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


ZIG_VERSION = "0.15.2"
ZIG_ARCHIVE_URL = "https://ziglang.org/download/0.15.2/zig-x86_64-windows-0.15.2.zip"
ZIG_ARCHIVE_SHA256 = "3a0ed1e8799a2f8ce2a6e6290a9ff22e6906f8227865911fb7ddedc3cc14cb0c"


def build(project: Path, zig_path: str) -> dict:
    """고정 버전·대상·최적화 옵션으로 빌드하고 재현용 비식별 메타데이터를 저장한다."""

    if platform.system() != "Windows" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise RuntimeError("This release builder requires Windows x64.")
    compiler = Path(zig_path).resolve()
    if not compiler.is_file():
        raise RuntimeError("Specify an existing Zig 0.15.2 executable with --zig or TONEMATCH_ZIG.")
    version = subprocess.check_output([str(compiler), "version"], text=True).strip()
    if version != ZIG_VERSION:
        raise RuntimeError(f"Expected Zig {ZIG_VERSION}; received {version}.")
    build_dir = project / "build" / "native"
    build_dir.mkdir(parents=True, exist_ok=True)
    output = build_dir / "tonematch_dsp.dll"
    flags = ["-std=c++17", "-O3", "-g0", "-shared", "-target", "x86_64-windows-gnu",
             "-Wall", "-Wextra", "-Werror"]
    command = [str(compiler), "c++", *flags, "native/tonematch_dsp.cpp", "-o", str(output)]
    environment = os.environ.copy()
    environment["ZIG_GLOBAL_CACHE_DIR"] = str(build_dir / "global-cache")
    environment["ZIG_LOCAL_CACHE_DIR"] = str(build_dir / "local-cache")
    subprocess.run(command, cwd=project, env=environment, check=True)
    # 성공 종료만으로 정적 archive를 DLL로 잘못 배포하지 않도록 실제 로더도 검사한다.
    with output.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise RuntimeError("Compiler output is not a Windows PE library.")
    library = ctypes.CDLL(str(output))
    for symbol in ("tm_dsp_abi_version", "tm_dsp_create", "tm_dsp_destroy", "tm_dsp_reset",
                   "tm_dsp_bin_count", "tm_dsp_frequencies", "tm_dsp_push"):
        getattr(library, symbol)
    library.tm_dsp_abi_version.restype = ctypes.c_uint32
    if library.tm_dsp_abi_version() != 1:
        raise RuntimeError("Built library does not implement DSP ABI 1.")
    destination = project / "resources" / "tonematch_dsp.dll"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output, destination)
    record = {
        "compiler": f"Zig {version} c++", "target": "x86_64-windows-gnu", "flags": flags,
        "compiler_archive_url": ZIG_ARCHIVE_URL, "compiler_archive_sha256": ZIG_ARCHIVE_SHA256,
        "sources": {str(path.relative_to(project)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (project / "native" / "tonematch_dsp.cpp", project / "native" / "tonematch_dsp.h")},
        "library": "resources/tonematch_dsp.dll", "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "size_bytes": destination.stat().st_size,
    }
    (build_dir / "native-build.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> int:
    """다운로드나 전역 PATH 변경 없이 사용자가 지정한 컴파일러만 실행한다."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig", default=os.environ.get("TONEMATCH_ZIG"), help="Path to Zig 0.15.2 zig.exe")
    args = parser.parse_args()
    if not args.zig:
        parser.error("--zig or TONEMATCH_ZIG is required; see DEVELOPMENT_KO.md for the verified archive.")
    print(json.dumps(build(Path(__file__).resolve().parents[1], args.zig), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
