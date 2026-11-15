"""Inert signing boundary tests; never execute or sign a fixture executable."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools import finalize_signed_release as release


VERSION = "0.1.09"
COMMIT = "a" * 40
PUBLISHER = "CN=Approved publisher, O=Approved publisher, C=AT"
THUMBPRINT = "A1" * 20
REQUEST = "12345678-1234-1234-1234-123456789012"
EXE = f"ToneMatchTMP-v{VERSION}.exe"


def pe_bytes(signed=False):
    """Minimal non-executable x64 PE envelope with an inert certificate blob."""
    data = bytearray(513)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 128)
    data[128:132] = b"PE\0\0"
    struct.pack_into("<H", data, 132, 0x8664)
    struct.pack_into("<H", data, 148, 240)
    struct.pack_into("<H", data, 152, 0x20B)
    struct.pack_into("<I", data, 260, 16)
    data[512] = 42
    if signed:
        data.extend(b"\0" * 7)
        struct.pack_into("<II", data, 296, 520, 16)
        struct.pack_into("<I", data, 216, 12345)
        data.extend(struct.pack("<IHH", 16, 0x200, 2) + b"FAKECERT")
    return bytes(data)


class SigningBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / f"ToneMatchTMP-v{VERSION}"
        self.root.mkdir()
        (self.root / EXE).write_bytes(pe_bytes())
        (self.root / "thirdparty.dll").write_bytes(b"upstream binary unchanged")
        (self.root / "MANIFEST.json").write_text('{"old": true}', encoding="utf-8")
        self.inputs = self.base / "input"
        self.signed = self.base / "signed"
        self.output = self.base / "release"

    def prepare(self):
        release.prepare(self.root, self.inputs, VERSION, COMMIT)
        shutil.copytree(self.inputs, self.signed)
        (self.signed / EXE).write_bytes(pe_bytes(signed=True))

    def finalize(self, **overrides):
        args = dict(root=self.root, input_directory=self.inputs,
                    signed_directory=self.signed, output_dir=self.output,
                    version=VERSION, source_commit=COMMIT,
                    expected_publisher=PUBLISHER, expected_thumbprint=THUMBPRINT,
                    signing_request_id=REQUEST)
        args.update(overrides)
        return release.finalize(**args)

    def valid_receipt(self):
        return {"status": "Valid", "publisher": PUBLISHER,
                "thumbprint": THUMBPRINT, "product_version": VERSION,
                "sha256": hashlib.sha256((self.signed / EXE).read_bytes()).hexdigest().upper()}

    def test_only_signing_bytes_may_change(self):
        release.verify_pe_binding(pe_bytes(), pe_bytes(signed=True))
        changed = bytearray(pe_bytes(signed=True))
        changed[500] = 1
        with self.assertRaisesRegex(ValueError, "unsigned build"):
            release.verify_pe_binding(pe_bytes(), bytes(changed))

    def test_unsigned_or_trailing_payload_is_rejected(self):
        for content in (pe_bytes(), pe_bytes(signed=True) + b"payload", b"not a PE"):
            with self.subTest(length=len(content)), self.assertRaises(ValueError):
                release.verify_pe_binding(pe_bytes(), content)

    def test_missing_signing_configuration_does_not_write_output(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "publisher"):
            self.finalize(expected_publisher="")
        self.assertFalse(self.output.exists())

    def test_unrelated_runtime_change_is_rejected_before_verifier(self):
        self.prepare()
        (self.root / "thirdparty.dll").write_bytes(b"replaced")
        with patch.object(release, "verify_authenticode") as verify:
            with self.assertRaisesRegex(ValueError, "binding"):
                self.finalize()
            verify.assert_not_called()

    def test_returned_binding_or_extra_file_is_rejected(self):
        self.prepare()
        (self.signed / "build-binding.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "binding"):
            self.finalize()
        shutil.copyfile(self.inputs / "build-binding.json", self.signed / "build-binding.json")
        (self.signed / "other.exe").write_bytes(pe_bytes(signed=True))
        with self.assertRaisesRegex(ValueError, "exactly"):
            self.finalize()

    def test_bad_signature_verifier_failure_is_not_bypassed_by_json(self):
        self.prepare()
        (self.root / "fake-signature.json").write_text(json.dumps(self.valid_receipt()))
        # Rebind the inert build so failure is specifically the actual verifier.
        shutil.rmtree(self.inputs)
        release.prepare(self.root, self.inputs, VERSION, COMMIT)
        shutil.copyfile(self.inputs / "build-binding.json", self.signed / "build-binding.json")
        with patch.object(release, "verify_authenticode", side_effect=ValueError("Authenticode invalid")):
            with self.assertRaisesRegex(ValueError, "Authenticode"):
                self.finalize()
        self.assertFalse(self.output.exists())

    def test_final_bytes_manifest_and_checksums_are_rebuilt(self):
        self.prepare()
        with patch.object(release, "verify_authenticode", return_value=self.valid_receipt()) as verify:
            result = self.finalize()
        verify.assert_called_once()
        final_root = Path(result["portable_directory"])
        self.assertEqual((final_root / EXE).read_bytes(), pe_bytes(signed=True))
        self.assertEqual((self.root / EXE).read_bytes(), pe_bytes())
        manifest = json.loads((final_root / "MANIFEST.json").read_text(encoding="utf-8"))
        entry = next(row for row in manifest["files"] if row["path"] == EXE)
        self.assertEqual(entry["sha256"], self.valid_receipt()["sha256"])
        with zipfile.ZipFile(result["zip"]) as archive:
            self.assertEqual(archive.read(f"{self.root.name}/{EXE}"), pe_bytes(signed=True))
        checksums = Path(result["checksums"]).read_text(encoding="ascii")
        self.assertIn(hashlib.sha256(Path(result["zip"]).read_bytes()).hexdigest().upper(), checksums)
        # Existing v0.1.07/08 clients require this published asset contract.
        from auto_update import select_release
        archive_path = Path(result['zip'])
        candidate = select_release([{
            'draft': False, 'published_at': '2026-11-15T00:00:00Z', 'tag_name': 'v' + VERSION,
            'assets': [{'name': archive_path.name, 'state': 'uploaded', 'size': archive_path.stat().st_size,
                        'digest': 'sha256:' + hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                        'browser_download_url': f'https://github.com/JH-Prime/ToneMatchTMP/releases/download/v{VERSION}/{archive_path.name}'}],
        }], '0.1.08')
        self.assertIsNotNone(candidate, 'Signed ZIP must remain discoverable by already shipped updaters')

    def test_existing_outputs_are_preserved(self):
        self.prepare()
        self.output.mkdir()
        existing = self.output / f"ToneMatchTMP-v{VERSION}-SHA256SUMS.txt"
        existing.write_bytes(b"published")
        with self.assertRaisesRegex(FileExistsError, "already exists"):
            self.finalize()
        self.assertEqual(existing.read_bytes(), b"published")

    def test_version_and_commit_must_match_prepared_build(self):
        self.prepare()
        with self.assertRaises(ValueError):
            self.finalize(source_commit="b" * 40)
        with self.assertRaises(ValueError):
            self.finalize(version="../../escape")

    def test_windows_verifier_rejects_unsigned_file_without_running_it(self):
        shell = shutil.which("pwsh") or shutil.which("powershell")
        if not shell:
            self.skipTest("PowerShell unavailable")
        script = Path(release.__file__).with_name("verify_release_signatures.ps1")
        result = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-File", str(script),
                                 "-FilePath", str(self.root / EXE), "-ExpectedPublisher", PUBLISHER,
                                 "-ExpectedThumbprint", THUMBPRINT, "-Version", VERSION],
                                capture_output=True, text=True, timeout=45)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Authenticode", result.stderr)


if __name__ == "__main__":
    unittest.main()
