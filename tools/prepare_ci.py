"""Recover only pinned third-party FFmpeg and Zig inputs on a clean CI runner."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import urllib.request
import zipfile

try:
    from .build_native import ZIG_ARCHIVE_URL, ZIG_ARCHIVE_SHA256, ZIG_VERSION
except ImportError:
    from build_native import ZIG_ARCHIVE_URL, ZIG_ARCHIVE_SHA256, ZIG_VERSION


FFMPEG_ARCHIVE_URL = (
    "https://github.com/JH-Prime/ToneMatchTMP/releases/download/v0.1.08/"
    "ToneMatchTMP-v0.1.08-Windows-x64-Portable-Dev.zip"
)
FFMPEG_ARCHIVE_SHA256 = "d0de3a7d09db5b51eb379d1387439fa57373da54da428bf5481c6371e94002da"
FFMPEG_MEMBER = "ToneMatchTMP-v0.1.08/source/resources/ffmpeg.exe"
FFMPEG_SHA256 = "72A489ECCD008C2EC2C0A5856C5C75BC3D8BBFA90166C4566865C246445E6AA3"
FFMPEG_SIZE = 102856192


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def download_verified(url: str, destination: Path, expected_sha256: str) -> Path:
    """Never replace an existing cache file or execute an unverified download."""
    if destination.exists():
        if not destination.is_file() or digest(destination).lower() != expected_sha256.lower():
            raise ValueError("Existing CI cache does not match its pinned SHA-256; remove it explicitly.")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="download-", dir=destination.parent) as temporary:
        downloaded = Path(temporary) / "download"
        request = urllib.request.Request(url, headers={"User-Agent": "ToneMatchTMP-CI"})
        with urllib.request.urlopen(request, timeout=120) as source, downloaded.open("xb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
        if digest(downloaded).lower() != expected_sha256.lower():
            raise ValueError("Downloaded CI input failed pinned SHA-256 verification.")
        with destination.open("xb") as output, downloaded.open("rb") as source:
            shutil.copyfileobj(source, output, length=1024 * 1024)
    return destination


def recover_ffmpeg(archive: Path, destination: Path) -> None:
    if destination.exists():
        if destination.is_file() and digest(destination).upper() == FFMPEG_SHA256:
            return
        raise ValueError("Existing FFmpeg does not match the pinned runtime; it was not replaced.")
    if digest(archive).lower() != FFMPEG_ARCHIVE_SHA256:
        raise ValueError("FFmpeg source archive failed pinned SHA-256 verification.")
    with zipfile.ZipFile(archive) as source:
        matches = [item for item in source.infolist() if item.filename == FFMPEG_MEMBER]
        if len(matches) != 1 or matches[0].file_size != FFMPEG_SIZE:
            raise ValueError("Expected exactly one pinned FFmpeg archive member with the documented size.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="ffmpeg-", dir=destination.parent) as temporary:
            extracted = Path(temporary) / "ffmpeg.exe"
            with source.open(matches[0]) as input_file, extracted.open("xb") as output:
                shutil.copyfileobj(input_file, output, length=1024 * 1024)
            if digest(extracted).upper() != FFMPEG_SHA256:
                raise ValueError("FFmpeg member failed pinned SHA-256 verification.")
            with destination.open("xb") as output, extracted.open("rb") as input_file:
                shutil.copyfileobj(input_file, output, length=1024 * 1024)


def extract_zig(archive: Path, destination: Path) -> Path:
    if destination.exists():
        raise FileExistsError("CI Zig output already exists; use a fresh build/ci-tools directory.")
    if digest(archive).lower() != ZIG_ARCHIVE_SHA256:
        raise ValueError("Zig archive failed pinned SHA-256 verification.")
    prefix = f"zig-x86_64-windows-{ZIG_VERSION}"
    with zipfile.ZipFile(archive) as source:
        seen = set()
        for item in source.infolist():
            name = PurePosixPath(item.filename)
            if (not name.parts or name.parts[0] != prefix or name.is_absolute()
                    or any(part in (".", "..") or ":" in part for part in name.parts)
                    or "\\" in item.filename or item.filename.casefold() in seen
                    or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError("Zig archive contains an unsafe or duplicate path.")
            seen.add(item.filename.casefold())
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="zig-", dir=destination.parent) as temporary:
            staging = Path(temporary)
            for item in source.infolist():
                target = staging.joinpath(*PurePosixPath(item.filename).parts)
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(item) as input_file, target.open("xb") as output:
                        shutil.copyfileobj(input_file, output, length=1024 * 1024)
            if not (staging / prefix / "zig.exe").is_file():
                raise ValueError("Pinned Zig archive has no expected compiler executable.")
            (staging / prefix).rename(destination)
    return destination / "zig.exe"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    cache = project / "build" / "ci-cache"
    ffmpeg = project / "resources" / "ffmpeg.exe"
    try:
        if ffmpeg.exists():
            if digest(ffmpeg).upper() != FFMPEG_SHA256:
                raise ValueError("Existing FFmpeg differs from the pinned runtime.")
        else:
            archive = download_verified(FFMPEG_ARCHIVE_URL, cache / "ffmpeg-source-v0.1.08.zip", FFMPEG_ARCHIVE_SHA256)
            recover_ffmpeg(archive, ffmpeg)
        zig_archive = download_verified(ZIG_ARCHIVE_URL, cache / f"zig-{ZIG_VERSION}.zip", ZIG_ARCHIVE_SHA256)
        zig = extract_zig(zig_archive, project / "build" / "ci-tools" / f"zig-{ZIG_VERSION}")
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, f"CI input preparation failed: {error}\n")
    print(json.dumps({"zig": zig.relative_to(project).as_posix(), "ffmpeg_sha256": FFMPEG_SHA256}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
