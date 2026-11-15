"""MSIX boundary checks never start the application or install a package."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from tools import package_msix as msix


class VersionAndIdentityTests(unittest.TestCase):
    def test_store_version_is_monotonic_and_reserves_revision(self):
        self.assertEqual(msix.store_version("0.1.09"), "1.1.9.0")
        self.assertEqual(msix.store_version("1.0.00"), "2.0.0.0")
        self.assertEqual(msix.store_version("65534.65535.65535"), "65535.65535.65535.0")
        for value in ("v0.1.09", "0.1.09.1", "0.1.-1", "65535.0.0", "0.65536.0", "0.1.9-beta", " 0.1.09"):
            with self.subTest(value=value), self.assertRaises(msix.PackagingError):
                msix.store_version(value)

    def test_production_identity_needs_explicit_partner_center_confirmation(self):
        identity = production_identity()
        self.assertEqual(msix.validate_identity(identity)["name"], identity["name"])
        for field, value in (("partner_center_confirmed", False), ("publisher", "CN=YOUR-PUBLISHER"),
                             ("name", "ToneMatchTMP.ValidationOnly"), ("name", "../escape"),
                             ("name", "con.name"), ("name", "xn--invalid"),
                             ("display_name", "<YOUR APP NAME>"), ("publisher_display_name", "")):
            with self.subTest(field=field, value=value), self.assertRaises(msix.PackagingError):
                msix.validate_identity(dict(identity, **{field: value}))


def production_identity():
    # A synthetic unit-test value, never used to create a submission artifact.
    return {"name": "12345.UnitTestApp", "publisher": "CN=06f50291-24d5-45fb-b9f5-504a4c8e97b7",
            "display_name": "Test App", "publisher_display_name": "Test Maintainer",
            "description": "Audio analysis", "partner_center_confirmed": True}


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = self.root / "onedir"
        (self.app / "_internal" / "resources").mkdir(parents=True)
        self.exe = self.app / "ToneMatchTMP-v0.1.09.exe"
        pe = bytearray(128)
        pe[:2] = b"MZ"
        struct.pack_into("<I", pe, 0x3c, 64)
        pe[64:68] = b"PE\0\0"
        struct.pack_into("<H", pe, 68, 0x8664)
        self.exe.write_bytes(pe)
        (self.app / "_internal" / "resources" / "ffmpeg.exe").write_bytes(b"fixture")
        (self.app / "_internal" / "resources" / "tonematch_dsp.dll").write_bytes(b"fixture")
        (self.app / "_internal" / "payload.txt").write_text("preserve", encoding="utf-8")
        self.metadata = patch.object(msix, "read_executable_versions", return_value=((0, 1, 9, 0), (0, 1, 9, 0)))
        self.metadata.start()
        self.addCleanup(self.metadata.stop)

    def prepare(self, **kwargs):
        args = dict(app_dir=self.app, version="0.1.09", output_dir=self.root / "output",
                    validation_only=True, prepare_only=True)
        args.update(kwargs)
        return msix.package(**args)

    def test_private_media_models_and_local_credentials_are_not_packaged(self):
        from tools.write_manifest import write_manifest
        for name in ('private.mp3', 'recording.wav', 'model.safetensors', 'jit.nbc', 'signpath.local.json'):
            with self.subTest(name=name):
                private = self.app / name
                private.write_bytes(b'private fixture')
                try:
                    with self.assertRaises(msix.PackagingError):
                        self.prepare()
                    with self.assertRaises(RuntimeError):
                        write_manifest(self.app, self.root / 'manifest.json', '0.1.09')
                finally:
                    private.unlink()
        self.assertFalse((self.root / 'output').exists())

    def test_validation_layout_preserves_internal_files_and_declares_full_trust(self):
        receipt = self.prepare()
        output = self.root / "output"
        self.assertFalse(receipt["publishable"])
        self.assertEqual(receipt["identity_mode"], "validation-only")
        self.assertEqual(receipt["signing_status"], "unsigned")
        self.assertEqual(receipt["package_version"], "1.1.9.0")
        self.assertFalse(receipt["checks"]["makeappx_validation"])
        layout = output / "NONPUBLISHABLE-layout"
        self.assertEqual((layout / "app" / "_internal" / "payload.txt").read_text(), "preserve")
        root = ET.parse(layout / "AppxManifest.xml").getroot()
        application = root.find("m:Applications/m:Application", msix.NS)
        self.assertEqual(application.get("Executable"), r"app\ToneMatchTMP-v0.1.09.exe")
        self.assertEqual(application.get("{" + msix.NS["uap10"] + "}RuntimeBehavior"), "packagedClassicApp")
        self.assertEqual(application.get("{" + msix.NS["uap10"] + "}TrustLevel"), "mediumIL")
        self.assertEqual([e.get("Name") for e in root.find("m:Capabilities", msix.NS)], ["runFullTrust"])
        self.assertEqual(json.loads((output / "packaging-receipt.json").read_text())["status"], "layout-prepared")
        for name, size in (("Square44x44Logo.png", 44), ("Square150x150Logo.png", 150), ("StoreLogo.png", 50)):
            image = (layout / "Assets" / name).read_bytes()
            self.assertEqual(image[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", image[16:24]), (size, size))

    def test_output_collision_preserves_existing_bytes(self):
        output = self.root / "output"
        output.mkdir()
        existing = output / "keep.msix"
        existing.write_bytes(b"published")
        with self.assertRaisesRegex(msix.PackagingError, "exists"):
            self.prepare()
        self.assertEqual(existing.read_bytes(), b"published")

    def test_version_mismatch_is_rejected_before_creating_output(self):
        with patch.object(msix, "read_executable_versions", return_value=((0, 1, 8, 0), (0, 1, 8, 0))):
            with self.assertRaisesRegex(msix.PackagingError, "version"):
                self.prepare()
        self.assertFalse((self.root / "output").exists())

    def test_missing_identity_and_mixed_modes_fail_closed(self):
        with self.assertRaisesRegex(msix.PackagingError, "identity"):
            self.prepare(validation_only=False)
        with self.assertRaisesRegex(msix.PackagingError, "identity"):
            self.prepare(identity=production_identity())

    def test_wrong_architecture_fails_before_staging(self):
        data = bytearray(self.exe.read_bytes())
        struct.pack_into("<H", data, 68, 0x14c)
        self.exe.write_bytes(data)
        with self.assertRaisesRegex(msix.PackagingError, "x64"):
            self.prepare()
        self.assertFalse((self.root / "output").exists())

    def test_output_inside_source_and_traversal_are_rejected(self):
        for output in (self.app / "output", self.root / "unused" / ".." / "output"):
            with self.subTest(output=output), self.assertRaises(msix.PackagingError):
                self.prepare(output_dir=output)

    def test_reparse_source_is_rejected_before_copy(self):
        original = msix.assert_plain_path
        def reject_payload(path):
            if Path(path).name == "payload.txt":
                raise msix.PackagingError("reparse point")
            return original(path)
        with patch.object(msix, "assert_plain_path", side_effect=reject_payload):
            with self.assertRaisesRegex(msix.PackagingError, "reparse"):
                self.prepare()
        self.assertFalse((self.root / "output").exists())

    def test_missing_makeappx_does_not_leave_an_apparent_candidate(self):
        with patch.object(msix, "find_makeappx", side_effect=msix.PackagingError("MakeAppx prerequisite")):
            with self.assertRaisesRegex(msix.PackagingError, "prerequisite"):
                self.prepare(prepare_only=False)
        self.assertFalse((self.root / "output").exists())

    def test_pack_failure_is_recorded_and_no_success_is_claimed(self):
        tool = self.root / "makeappx.exe"
        tool.write_bytes(b"fixture")
        with patch.object(msix, "find_makeappx", return_value=tool), patch.object(msix, "run_makeappx", side_effect=msix.PackagingError("failed")):
            with self.assertRaisesRegex(msix.PackagingError, "failed"):
                self.prepare(prepare_only=False)
        receipt = json.loads((self.root / "output" / "packaging-receipt.json").read_text())
        self.assertEqual(receipt["status"], "failed")
        self.assertFalse(receipt["publishable"])
        self.assertFalse(receipt["checks"]["makeappx_validation"])

    def test_makeappx_log_redacts_windows_profile_paths(self):
        output = self.root / "fixture.msix"
        output.write_bytes(b"package")
        result = subprocess.CompletedProcess([], 0, stdout=r'Using C:\Users\private-person\work\AppxManifest.xml', stderr="")
        with patch.object(msix.subprocess, "run", return_value=result):
            msix.run_makeappx(self.root / "makeappx.exe", self.app, output, self.root / "makeappx.log")
        log = (self.root / "makeappx.log").read_text()
        self.assertNotIn("private-person", log)
        self.assertIn("%USERPROFILE%", log)


if __name__ == "__main__":
    unittest.main()
