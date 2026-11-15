"""Prepare an unsigned x64 Store candidate, or a visibly nonpublishable test package.

This tool never installs, signs, submits, or runs the packaged application.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
import zlib

try:
    from .write_manifest import assert_distributable_file
except ImportError:
    from write_manifest import assert_distributable_file

NS = {
    "m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
    "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
    "uap10": "http://schemas.microsoft.com/appx/manifest/uap/windows10/10",
    "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities",
}
VALIDATION_IDENTITY = {
    "name": "ToneMatchTMP.ValidationOnly",
    "publisher": "CN=ToneMatchTMP Validation Only",
    "display_name": "ToneMatch TMP NONPUBLISHABLE",
    "publisher_display_name": "Local validation only",
    "description": "Unsigned structural validation; not for installation or Store submission.",
}
RESERVED_NAMES = {"con", "prn", "aux", "nul"} | {
    f"{prefix}{number}" for prefix in ("com", "lpt") for number in range(1, 10)
}


class PackagingError(ValueError):
    """An input or packaging prerequisite failed validation."""


def application_version(version: str) -> tuple[int, int, int, int]:
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}", version):
        raise PackagingError("Application version must have three numeric components, such as 0.1.09")
    parts = tuple(int(part) for part in version.split("."))
    if parts[0] > 65534 or any(part > 65535 for part in parts[1:]):
        raise PackagingError("Application version exceeds the Store major+1 version mapping range")
    return (*parts, 0)


def store_version(version: str) -> str:
    major, minor, patch, _ = application_version(version)
    # Store requires a positive major and reserves revision for its own use.
    return f"{major + 1}.{minor}.{patch}.0"


def validate_identity(identity: dict) -> dict:
    fields = {"name", "publisher", "display_name", "publisher_display_name", "description", "partner_center_confirmed"}
    if not isinstance(identity, dict) or set(identity) != fields:
        raise PackagingError("Store identity JSON must contain exactly: " + ", ".join(sorted(fields)))
    if identity["partner_center_confirmed"] is not True:
        raise PackagingError("Store identity requires partner_center_confirmed=true after copying Partner Center values")
    for key in fields - {"partner_center_confirmed"}:
        value = identity[key]
        if not isinstance(value, str) or not value or value != value.strip() or any(ord(c) < 32 for c in value):
            raise PackagingError(f"Store identity {key} must be a nonempty, trimmed single-line string")
        if any(marker in value.casefold() for marker in ("placeholder", "replace_", "your-", "your ", "validation", "nonpublishable", "<", ">")):
            raise PackagingError(f"Store identity {key} contains a placeholder or validation value")
    name = identity["name"]
    if (not re.fullmatch(r"[A-Za-z0-9.-]{3,50}", name) or name.endswith(".")
            or name.split(".")[0].casefold() in RESERVED_NAMES
            or any(part.casefold().startswith("xn--") for part in name.split("."))):
        raise PackagingError("Store identity name is not a valid Windows package name")
    # Partner Center's Package/Identity/Publisher uses a canonical CN GUID.
    publisher = identity["publisher"]
    if not re.fullmatch(r"CN=[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", publisher):
        raise PackagingError("Copy the exact CN=<GUID> publisher from Partner Center product identity")
    if uuid.UUID(publisher[3:]).int == 0:
        raise PackagingError("Store identity publisher cannot be a zero GUID")
    for key in ("display_name", "publisher_display_name", "description"):
        if len(identity[key]) > 256 or identity[key].lower().startswith("ms-resource:"):
            raise PackagingError(f"Store identity {key} must be plain text of at most 256 characters")
    return dict(identity)


def assert_plain_path(path: Path) -> Path:
    path = Path(path)
    if ".." in path.parts:
        raise PackagingError("Path traversal components are forbidden")
    absolute = path.absolute()
    for entry in (absolute, *absolute.parents):
        try:
            info = entry.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise PackagingError("Symlinks, junctions, and reparse points are forbidden in package paths")
    return absolute


def source_files(root: Path) -> list[Path]:
    files = []
    seen = set()
    def walk_error(error):
        raise PackagingError("Unable to read an application input directory") from error
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        for name in sorted(dirs + names):
            path = assert_plain_path(Path(directory) / name)
            relative = path.relative_to(root)
            key = relative.as_posix().casefold()
            if key in seen:
                raise PackagingError("Case-insensitive package path collision")
            seen.add(key)
            if (name.endswith((".", " ")) or re.search(r'[<>:"|?*\x00-\x1f]', name)
                    or name.split(".")[0].casefold() in RESERVED_NAMES):
                raise PackagingError("Unsafe Windows package filename")
            if path.is_file():
                try:
                    assert_distributable_file(relative.as_posix())
                except RuntimeError as exc:
                    raise PackagingError(str(exc)) from exc
                files.append(path)
            elif not path.is_dir():
                raise PackagingError("Package inputs must be regular files or directories")
    return files


def assert_x64(executable: Path) -> None:
    with executable.open("rb") as handle:
        header = handle.read(64)
        if len(header) != 64 or header[:2] != b"MZ":
            raise PackagingError("Application must be a Windows x64 PE executable")
        handle.seek(struct.unpack_from("<I", header, 0x3C)[0])
        signature = handle.read(6)
    if len(signature) != 6 or signature[:4] != b"PE\0\0" or struct.unpack_from("<H", signature, 4)[0] != 0x8664:
        raise PackagingError("Application must have x64 PE architecture")


def read_executable_versions(executable: Path) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if os.name != "nt":
        raise PackagingError("Embedded executable version verification requires Windows")
    api = ctypes.WinDLL("version", use_last_error=True)
    api.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    api.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    api.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    api.GetFileVersionInfoW.restype = wintypes.BOOL
    api.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
    api.VerQueryValueW.restype = wintypes.BOOL
    size = api.GetFileVersionInfoSizeW(str(executable), None)
    if not size:
        raise PackagingError("Application executable has no readable embedded version")
    data = ctypes.create_string_buffer(size)
    pointer, length = ctypes.c_void_p(), wintypes.UINT()
    if not api.GetFileVersionInfoW(str(executable), 0, size, data) or not api.VerQueryValueW(data, "\\", ctypes.byref(pointer), ctypes.byref(length)):
        raise PackagingError("Unable to read embedded executable version")
    if length.value < 52:
        raise PackagingError("Invalid executable fixed version resource")
    values = struct.unpack("<13I", ctypes.string_at(pointer, 52))
    if values[0] != 0xFEEF04BD:
        raise PackagingError("Invalid executable version resource signature")
    def unpack_pair(high, low):
        return (high >> 16, high & 65535, low >> 16, low & 65535)
    return unpack_pair(values[2], values[3]), unpack_pair(values[4], values[5])


def write_manifest(layout: Path, identity: dict, version: str, executable: str) -> None:
    for prefix, uri in NS.items():
        ET.register_namespace("" if prefix == "m" else prefix, uri)
    def add(parent, name, attributes=None, text=None):
        prefix, local = name.split(":") if ":" in name else ("m", name)
        element = ET.SubElement(parent, f"{{{NS[prefix]}}}{local}", attributes or {})
        element.text = text
        return element
    root = ET.Element(f"{{{NS['m']}}}Package", {"IgnorableNamespaces": "uap uap10 rescap"})
    add(root, "Identity", {"Name": identity["name"], "Publisher": identity["publisher"], "Version": store_version(version), "ProcessorArchitecture": "x64"})
    properties = add(root, "Properties")
    for tag, field in (("DisplayName", "display_name"), ("PublisherDisplayName", "publisher_display_name"), ("Description", "description")):
        add(properties, tag, text=identity[field])
    add(properties, "Logo", text=r"Assets\StoreLogo.png")
    resources = add(root, "Resources")
    for language in ("ko-KR", "en-US"):
        add(resources, "Resource", {"Language": language})
    dependencies = add(root, "Dependencies")
    add(dependencies, "TargetDeviceFamily", {"Name": "Windows.Desktop", "MinVersion": "10.0.19041.0", "MaxVersionTested": "10.0.26100.0"})
    applications = add(root, "Applications")
    application = add(applications, "Application", {
        "Id": "ToneMatchTMP", "Executable": "app\\" + executable,
        f"{{{NS['uap10']}}}RuntimeBehavior": "packagedClassicApp",
        f"{{{NS['uap10']}}}TrustLevel": "mediumIL",
    })
    add(application, "uap:VisualElements", {
        "DisplayName": identity["display_name"], "Description": identity["description"],
        "Square150x150Logo": r"Assets\Square150x150Logo.png",
        "Square44x44Logo": r"Assets\Square44x44Logo.png", "BackgroundColor": "#162536",
    })
    add(add(root, "Capabilities"), "rescap:Capability", {"Name": "runFullTrust"})
    ET.indent(root)
    ET.ElementTree(root).write(layout / "AppxManifest.xml", encoding="utf-8", xml_declaration=True)


def write_assets(layout: Path) -> None:
    """Small original waveform glyph; no external font/image dependency."""
    assets = layout / "Assets"
    assets.mkdir()
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    for name, size in (("Square44x44Logo.png", 44), ("Square150x150Logo.png", 150), ("StoreLogo.png", 50)):
        rows = bytearray()
        for y in range(size):
            rows.append(0)
            for x in range(size):
                glyph = any(abs(x / size - center) <= .055 and abs(y / size - .5) <= height
                            for center, height in ((.28, .15), (.5, .3), (.72, .22)))
                rows.extend((86, 221, 191) if glyph else (22, 37, 54))
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        png += chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")
        (assets / name).write_bytes(png)


def find_makeappx(explicit: Path | None = None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    else:
        found = shutil.which("makeappx.exe")
        if found:
            candidates.append(Path(found))
        kits = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits" / "10"
        candidates.extend(sorted(kits.glob("bin/*/x64/makeappx.exe"), reverse=True))
        candidates.append(kits / "App Certification Kit" / "makeappx.exe")
    for path in candidates:
        path = assert_plain_path(path)
        if path.is_file():
            return path
    raise PackagingError("MakeAppx.exe prerequisite missing: provide --makeappx from the Windows SDK or official Microsoft.Windows.SDK.BuildTools NuGet package; use --prepare-only for layout checks")


def run_makeappx(tool: Path, layout: Path, output: Path, log: Path) -> None:
    def sanitized(value):
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        return re.sub(r'(?i)[a-z]:\\Users\\[^\\\r\n"]+', "%USERPROFILE%", value or "")
    with log.open("x", encoding="utf-8") as stream:
        try:
            result = subprocess.run([str(tool), "pack", "/d", layout.name, "/p", output.name, "/h", "SHA256", "/no"],
                                    cwd=output.parent, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired as exc:
            stream.write(sanitized(exc.stdout) + sanitized(exc.stderr))
            raise PackagingError("MakeAppx exceeded its 30 minute packaging timeout") from exc
        stream.write(sanitized(result.stdout) + sanitized(result.stderr))
    if result.returncode != 0 or not output.is_file():
        raise PackagingError("MakeAppx validation/packaging failed; inspect makeappx.log in the output directory")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def package(*, app_dir: Path, version: str, output_dir: Path, identity: dict | None = None,
            validation_only: bool = False, prepare_only: bool = False, makeappx: Path | None = None,
            source_commit: str | None = None) -> dict:
    expected = application_version(version)
    if bool(identity is not None) == bool(validation_only):
        raise PackagingError("Provide a Store identity OR explicit --validation-only; identity modes cannot be mixed")
    selected_identity = dict(VALIDATION_IDENTITY) if validation_only else validate_identity(identity)
    if source_commit is not None and not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise PackagingError("Source commit must be a full lowercase Git commit hash")
    source, output = assert_plain_path(app_dir), assert_plain_path(output_dir)
    if not source.is_dir():
        raise PackagingError("Application onedir input is missing")
    if source == output or source in output.parents or output in source.parents:
        raise PackagingError("Package output and application input must not overlap")
    if output.exists():
        raise PackagingError("Output directory already exists; choose a new exclusive output directory")
    files = source_files(source)
    executable = source / f"ToneMatchTMP-v{version}.exe"
    for required in (executable, source / "_internal/resources/ffmpeg.exe", source / "_internal/resources/tonematch_dsp.dll"):
        if required not in files:
            raise PackagingError("Expected versioned executable and _internal/resources runtime files are required")
    assert_x64(executable)
    if read_executable_versions(executable) != (expected, expected):
        raise PackagingError("Embedded executable file/product version does not match the requested application version")
    tool = None if prepare_only else find_makeappx(makeappx)
    # mkdir is the exclusive claim. A failed attempt is retained for investigation.
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise PackagingError("Output directory already exists") from exc
    layout_name = "NONPUBLISHABLE-layout" if validation_only else "store-layout"
    package_name = f"ToneMatchTMP-v{version}-{'NONPUBLISHABLE-VALIDATION' if validation_only else 'store-candidate'}-unsigned.msix"
    receipt = {
        "schema_version": 1, "status": "preparing", "app_version": version, "package_version": store_version(version),
        "architecture": "x64", "distribution_channel": "microsoft-store", "signing_status": "unsigned",
        "identity_mode": "validation-only" if validation_only else "partner-center-configured",
        "identity": selected_identity, "publishable": False,
        "source_commit": source_commit, "source_commit_evidence": "caller-provided; use accompanying build provenance",
        "checks": {"embedded_version": True, "x64_executable": True, "safe_input_paths": True,
                   "makeappx_validation": False, "installation": False, "runtime_smoke": False, "store_certification": False},
        "submission_eligible": False, "files": [],
        "packaging_tool": {"name": tool.name, "sha256": sha256(tool)} if tool else None,
    }
    try:
        layout = output / layout_name
        (layout / "app").mkdir(parents=True)
        for path in files:
            assert_plain_path(path)
            destination = layout / "app" / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
        # Check the actual staged executable again, after the copy boundary.
        staged_executable = layout / "app" / executable.name
        assert_x64(staged_executable)
        if read_executable_versions(staged_executable) != (expected, expected):
            raise PackagingError("Staged executable version changed during packaging")
        write_manifest(layout, selected_identity, version, executable.name)
        write_assets(layout)
        receipt["files"] = [{"path": path.relative_to(layout).as_posix(), "sha256": sha256(path), "size": path.stat().st_size}
                            for path in sorted(layout.rglob("*")) if path.is_file()]
        receipt["status"] = "layout-prepared"
        if tool:
            artifact = output / package_name
            run_makeappx(tool, layout, artifact, output / "makeappx.log")
            receipt["checks"]["makeappx_validation"] = True
            receipt["status"] = "package-created"
            receipt["artifact"] = {"name": artifact.name, "sha256": sha256(artifact), "size": artifact.stat().st_size}
            # This is eligibility for manual review/submission, never approval or publication.
            receipt["submission_eligible"] = not validation_only
        return receipt
    except BaseException:
        receipt["status"] = "failed"
        raise
    finally:
        with (output / "packaging-receipt.json").open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-dir", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--identity", type=Path, help="Explicit Partner Center identity JSON")
    modes.add_argument("--validation-only", action="store_true", help="Nonpublishable local test identity")
    parser.add_argument("--prepare-only", action="store_true", help="Prepare checked layout without MakeAppx")
    parser.add_argument("--makeappx", type=Path)
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    try:
        identity = None
        if args.identity:
            identity = json.loads(assert_plain_path(args.identity).read_text(encoding="utf-8-sig"))
        receipt = package(app_dir=args.app_dir, version=args.version, output_dir=args.output_dir, identity=identity,
                          validation_only=args.validation_only, prepare_only=args.prepare_only,
                          makeappx=args.makeappx, source_commit=args.source_commit)
    except (PackagingError, OSError, json.JSONDecodeError) as exc:
        # Do not echo full user-profile paths from OS exceptions into release logs.
        message = str(exc) if isinstance(exc, PackagingError) else type(exc).__name__
        print(f"MSIX preparation failed: {message}", file=sys.stderr)
        return 1
    print(json.dumps({key: receipt[key] for key in ("status", "identity_mode", "app_version", "package_version", "signing_status", "submission_eligible")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
