"""포터블 배포 폴더의 파일 크기와 SHA-256 목록을 JSON으로 기록한다."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    """큰 바이너리도 메모리를 많이 쓰지 않고 SHA-256을 계산한다."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_manifest(root: Path, output: Path, version: str) -> None:
    """배포 루트 아래 모든 일반 파일을 정렬해 재현 가능한 목록으로 저장한다."""
    resolved_output = output.resolve()
    files = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or path.resolve() == resolved_output:
            continue
        relative = path.relative_to(root).as_posix()
        if relative.lower().endswith((".safetensors", ".ckpt", ".pth", ".pt", ".th", ".onnx", ".pkl")):
            raise RuntimeError(f"AI 모델 가중치는 배포할 수 없습니다: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": _sha256(path)})
    payload = {
        "schema": "tonematch-portable-manifest/v1",
        "app_version": version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "build_platform": platform.platform(),
        "file_count": len(files),
        "files": files,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    """명령행 인수로 받은 배포 루트와 버전에 대해 manifest를 생성한다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    arguments = parser.parse_args()
    write_manifest(arguments.root.resolve(), arguments.output.resolve(), arguments.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
