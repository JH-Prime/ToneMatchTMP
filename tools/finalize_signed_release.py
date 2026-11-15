"""Bind SignPath's returned EXE to its source build and verify before packaging."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import tempfile
import uuid
import zipfile

try:
    from .write_manifest import assert_distributable_file, write_manifest
except ImportError:
    from write_manifest import assert_distributable_file, write_manifest


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_identity(version: str, source_commit: str) -> str:
    if not re.fullmatch(r"[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}", version):
        raise ValueError("Invalid application version.")
    if any(int(part) > 65535 for part in version.split(".")):
        raise ValueError("Application version exceeds Windows version limits.")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("A full lowercase source commit SHA is required.")
    return f"ToneMatchTMP-v{version}"


def inventory(root: Path) -> dict:
    """Reject links/reparse points and bind all regular files with exact casing."""
    if not root.is_dir() or root.is_symlink() or root.is_junction():
        raise ValueError("Build directory must be a regular directory.")
    result, seen = {}, set()
    for directory, directories, filenames in os.walk(root, followlinks=False):
        for name in directories + filenames:
            path = Path(directory) / name
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            if (stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                raise ValueError("Build input contains a link or reparse point.")
            if relative.casefold() in seen or any(char in name for char in "\\:<>"):
                raise ValueError("Build input contains an ambiguous path.")
            seen.add(relative.casefold())
            if stat.S_ISREG(info.st_mode):
                assert_distributable_file(relative)
                result[relative] = {"bytes": info.st_size, "sha256": sha256(path)}
            elif not stat.S_ISDIR(info.st_mode):
                raise ValueError("Build input contains a non-regular file.")
    return dict(sorted(result.items()))


def _pe_fields(data: bytes) -> tuple[int, int, int, int]:
    try:
        if data[:2] != b"MZ":
            raise ValueError("Invalid PE DOS header.")
        pe = struct.unpack_from("<I", data, 60)[0]
        optional = pe + 24
        if (pe < 64 or data[pe:pe + 4] != b"PE\0\0"
                or struct.unpack_from("<H", data, pe + 4)[0] != 0x8664
                or struct.unpack_from("<H", data, pe + 20)[0] < 152
                or struct.unpack_from("<H", data, optional)[0] != 0x20B
                or struct.unpack_from("<I", data, optional + 108)[0] < 5):
            raise ValueError("Expected a Windows x64 PE32+ executable.")
        checksum, security = optional + 64, optional + 144
        certificate_offset, certificate_size = struct.unpack_from("<II", data, security)
        return checksum, security, certificate_offset, certificate_size
    except struct.error as error:
        raise ValueError("Truncated PE headers.") from error


def verify_pe_binding(unsigned: bytes, signed: bytes) -> None:
    """Only allow Authenticode's checksum, certificate entry and appended table."""
    checksum, security, old_offset, old_size = _pe_fields(unsigned)
    other_checksum, other_security, offset, size = _pe_fields(signed)
    if old_offset or old_size:
        raise ValueError("Signing input must be an unsigned build.")
    if ((checksum, security) != (other_checksum, other_security)
            or offset != (len(unsigned) + 7) // 8 * 8
            or size < 8 or offset + size != len(signed)):
        raise ValueError("Signed PE does not match the unsigned build envelope.")
    length, revision, kind = struct.unpack_from("<IHH", signed, offset)
    if (revision != 0x200 or kind != 2 or length < 8 or (length + 7) // 8 * 8 != size
            or any(signed[offset + length:])):
        raise ValueError("Invalid Authenticode certificate table.")
    original, returned = bytearray(unsigned), bytearray(signed[:len(unsigned)])
    for start, count in ((checksum, 4), (security, 8)):
        original[start:start + count] = b"\0" * count
        returned[start:start + count] = b"\0" * count
    if original != returned or any(signed[len(unsigned):offset]):
        raise ValueError("Signed executable differs from the unsigned build.")


def verify_authenticode(path: Path, publisher: str, thumbprint: str, version: str) -> dict:
    """Run the checked-in Windows verifier; never accept a supplied receipt."""
    if os.name != "nt":
        raise ValueError("Authenticode release verification requires Windows.")
    shell = shutil.which("pwsh.exe") or shutil.which("powershell.exe")
    if not shell:
        raise ValueError("PowerShell is required for Authenticode verification.")
    result = subprocess.run(
        [shell, "-NoProfile", "-NonInteractive", "-File",
         str(Path(__file__).with_name("verify_release_signatures.ps1")),
         "-FilePath", str(path), "-ExpectedPublisher", publisher,
         "-ExpectedThumbprint", thumbprint, "-Version", version],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    if result.returncode:
        raise ValueError("Authenticode verification failed; no signed release was produced.")
    try:
        receipt = json.loads(result.stdout.lstrip("\ufeff"))
    except (ValueError, TypeError) as error:
        raise ValueError("Authenticode verifier returned malformed evidence.") from error
    if (receipt.get("status") != "Valid" or receipt.get("publisher") != publisher
            or receipt.get("thumbprint") != thumbprint or receipt.get("product_version") != version
            or receipt.get("sha256") != sha256(path)):
        raise ValueError("Authenticode evidence does not bind the requested file and publisher.")
    return receipt


def _disjoint(output: Path, inputs: list[Path]) -> None:
    if any(output == path or output.is_relative_to(path) or path.is_relative_to(output)
           for path in inputs):
        raise ValueError("Output and input directories must not overlap.")


def prepare(root: Path, output: Path, version: str, source_commit: str) -> dict:
    base = validate_identity(version, source_commit)
    root, output = root.resolve(), output.resolve()
    _disjoint(output, [root])
    files = inventory(root)
    exe = f"{base}.exe"
    if root.name != base or exe not in files:
        raise ValueError("Portable directory and executable must match the application version.")
    if any(_pe_fields((root / exe).read_bytes())[2:]):
        raise ValueError("Signing input already has a certificate table.")
    binding = {"schema": "tonematch-signing-input/v1", "app_version": version,
               "source_commit": source_commit, "files": files}
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(root / exe, output / exe)
    if sha256(output / exe) != files[exe]["sha256"]:
        raise ValueError("Executable changed while preparing signing input.")
    (output / "build-binding.json").write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8")
    return binding


def finalize(*, root: Path, input_directory: Path, signed_directory: Path, output_dir: Path,
             version: str, source_commit: str, expected_publisher: str,
             expected_thumbprint: str, signing_request_id: str) -> dict:
    base = validate_identity(version, source_commit)
    if not expected_publisher.strip() or expected_publisher != expected_publisher.strip():
        raise ValueError("Configure the exact approved publisher certificate subject.")
    if not re.fullmatch(r"[A-Fa-f0-9]{40}", expected_thumbprint):
        raise ValueError("Configure the approved certificate thumbprint (40 hexadecimal characters).")
    expected_thumbprint = expected_thumbprint.upper()
    try:
        uuid.UUID(signing_request_id)
    except (ValueError, AttributeError) as error:
        raise ValueError("A SignPath signing request ID is required.") from error
    root, input_directory, signed_directory, output_dir = (
        path.resolve() for path in (root, input_directory, signed_directory, output_dir))
    _disjoint(output_dir, [root, input_directory, signed_directory])
    exe = f"{base}.exe"
    portable = output_dir / base
    # Preserve the asset name recognized by already published portable updaters.
    # Actual signature state is recorded in DISTRIBUTION/SIGNING-VERIFICATION.
    archive = output_dir / f"{base}-Windows-x64-Portable-Dev.zip"
    checksums = output_dir / f"{base}-SHA256SUMS.txt"
    for target in (portable, archive, checksums):
        if target.exists():
            raise FileExistsError(f"Release output already exists: {target.name}")
    expected_names = {exe, "build-binding.json"}
    if set(inventory(input_directory)) != expected_names or set(inventory(signed_directory)) != expected_names:
        raise ValueError("SignPath input and output must contain exactly the root EXE and build-binding.json.")
    binding_bytes = (input_directory / "build-binding.json").read_bytes()
    if binding_bytes != (signed_directory / "build-binding.json").read_bytes():
        raise ValueError("SignPath returned a modified build binding.")
    try:
        binding = json.loads(binding_bytes)
    except ValueError as error:
        raise ValueError("Malformed build binding.") from error
    original_files = inventory(root)
    expected_binding = {"schema": "tonematch-signing-input/v1", "app_version": version,
                        "source_commit": source_commit, "files": original_files}
    if root.name != base or binding != expected_binding:
        raise ValueError("Portable files, version or source commit differ from the build binding.")
    unsigned_bytes = (root / exe).read_bytes()
    if unsigned_bytes != (input_directory / exe).read_bytes():
        raise ValueError("Signing input EXE differs from the build binding.")
    signed_bytes = (signed_directory / exe).read_bytes()
    verify_pe_binding(unsigned_bytes, signed_bytes)
    receipt = verify_authenticode(signed_directory / exe, expected_publisher, expected_thumbprint, version)
    if receipt.get("sha256") != hashlib.sha256(signed_bytes).hexdigest().upper():
        raise ValueError("Signed EXE changed during Authenticode verification.")
    output_dir.mkdir(parents=True, exist_ok=True)
    # All byte-changing steps happen inside disposable staging. Checksums are the
    # last commit marker; an interrupted run never overwrites an earlier output.
    with tempfile.TemporaryDirectory(prefix=".signing-finalize-", dir=output_dir) as temporary:
        stage = Path(temporary) / base
        shutil.copytree(root, stage)
        if inventory(stage) != original_files:
            raise ValueError("Portable build changed during staging.")
        (stage / exe).write_bytes(signed_bytes)
        diagnostics = stage / "diagnostics"
        diagnostics.mkdir(exist_ok=True)
        receipt.update({"schema": "tonematch-signing-verification/v1", "app_version": version,
                        "source_commit": source_commit, "signing_request_id": signing_request_id,
                        "unsigned_sha256": original_files[exe]["sha256"],
                        "unchanged_build_files_verified": True, "signed_files": [exe]})
        (diagnostics / "SIGNING-VERIFICATION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        distribution = {"schema": "tonematch-build-distribution/v1", "app_version": version,
                        "source_commit": source_commit, "status": "signed_portable",
                        "public_signing_verified": True, "store_certified": False,
                        "signature_coverage": [exe],
                        "generated_at_kst": datetime.now(timezone(timedelta(hours=9))).isoformat()}
        (diagnostics / "DISTRIBUTION.json").write_text(json.dumps(distribution, indent=2) + "\n", encoding="utf-8")
        write_manifest(stage, stage / "MANIFEST.json", version)
        staged_archive = Path(temporary) / archive.name
        final_files = inventory(stage)
        with zipfile.ZipFile(staged_archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
            for relative in final_files:
                output.write(stage / relative, f"{base}/{relative}")
        # Copy in exclusive mode: concurrent invocations cannot clobber releases.
        portable.mkdir(exist_ok=False)
        shutil.copytree(stage, portable, dirs_exist_ok=True)
        with archive.open("xb") as destination, staged_archive.open("rb") as source:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
        lines = [f"{sha256(portable / relative)}  {base}/{relative}"
                 for relative in (exe, "MANIFEST.json", "diagnostics/SIGNING-VERIFICATION.json")]
        lines.append(f"{sha256(archive)}  {archive.name}")
        with checksums.open("x", encoding="ascii", newline="\n") as output:
            output.write("\n".join(lines) + "\n")
    return {"portable_directory": str(portable), "zip": str(archive), "checksums": str(checksums)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    finalize_parser = commands.add_parser("finalize")
    for command in (prepare_parser, finalize_parser):
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--version", required=True)
        command.add_argument("--source-commit", required=True)
    prepare_parser.add_argument("--output", type=Path, required=True)
    finalize_parser.add_argument("--input-directory", type=Path, required=True)
    finalize_parser.add_argument("--signed-directory", type=Path, required=True)
    finalize_parser.add_argument("--output-dir", type=Path, required=True)
    finalize_parser.add_argument("--expected-publisher", required=True)
    finalize_parser.add_argument("--expected-thumbprint", required=True)
    finalize_parser.add_argument("--signing-request-id", required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    try:
        result = prepare(**args) if command == "prepare" else finalize(**args)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Signing gate failed: {error}\n")
    print(json.dumps({"prepared": True} if command == "prepare" else result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
