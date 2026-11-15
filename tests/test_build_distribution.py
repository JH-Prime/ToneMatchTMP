"""Exercise the PowerShell artifact gate without invoking a compiler or UI."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SHELL = shutil.which('pwsh') or shutil.which('powershell')


@unittest.skipUnless(SHELL, 'PowerShell is required for the Windows build gate')
class BuildDistributionTests(unittest.TestCase):
    def run_gate(self, root, mode='SigningInput', version='0.1.09', skip_zip=False):
        # Parameters are passed as argv; no input is interpolated into shell code.
        script = Path(root) / 'gate.ps1'
        script.write_text(
            'param($Policy, $Output, $Mode, $Version, $Skip)\n'
            '$ErrorActionPreference = "Stop"\n'
            '. $Policy\n'
            'Get-DistributionPlan -OutputDir $Output -Mode $Mode -Version $Version '
            '-SkipZip:($Skip -eq "yes") | ConvertTo-Json -Compress\n', encoding='utf-8')
        return subprocess.run([SHELL, '-NoProfile', '-NonInteractive', '-File', str(script),
                               str(ROOT / 'tools' / 'build_distribution.ps1'), str(root),
                               mode, version, 'yes' if skip_zip else 'no'],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)

    def test_default_signing_input_never_emits_release_files(self):
        with tempfile.TemporaryDirectory(prefix='서명 gate ') as root:
            result = self.run_gate(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertFalse(plan['WriteReleaseFiles'])
            self.assertFalse(plan['CreateZip'])
            self.assertEqual(plan['Status'], 'unsigned_signing_input')

    def test_development_requires_explicit_mode_and_records_unsigned(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.run_gate(root, 'Development')
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertEqual(plan['Status'], 'unsigned_development')
            self.assertTrue(plan['CreateZip'])
            self.assertTrue(plan['WriteReleaseFiles'])

    def test_existing_zip_or_checksum_is_never_replaced(self):
        for suffix in ('-Windows-x64-Portable-Dev.zip', '-SHA256SUMS.txt'):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as root:
                artifact = Path(root) / ('ToneMatchTMP-v0.1.09' + suffix)
                artifact.write_bytes(b'previous immutable artifact')
                result = self.run_gate(root, 'Development')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(artifact.read_bytes(), b'previous immutable artifact')

    def test_skip_zip_still_protects_existing_checksum(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / 'ToneMatchTMP-v0.1.09-SHA256SUMS.txt').mkdir()
            self.assertNotEqual(self.run_gate(root, 'Development', skip_zip=True).returncode, 0)

    def test_invalid_version_cannot_escape_output_directory(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertNotEqual(self.run_gate(root, version='../bad').returncode, 0)

    def test_unknown_distribution_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertNotEqual(self.run_gate(root, mode='Trusted').returncode, 0)

    def test_packaged_configuration_excludes_local_account_files(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source, target = root / 'source', root / 'target'
            source.mkdir()
            public = ('signpath-artifact-configuration.xml', 'signpath-settings.example.json',
                      'store-identity.example.json', 'STORE_SUBMISSION_KO.md')
            for name in public:
                (source / name).write_text('public example', encoding='utf-8')
            (source / 'signpath.local.json').write_text('private account material', encoding='utf-8')
            (source / 'store-identity.local.json').write_text('local account material', encoding='utf-8')
            script = root / 'copy.ps1'
            script.write_text('param($Policy,$Source,$Target)\n$ErrorActionPreference="Stop"\n'
                              '. $Policy\nCopy-PublicDistribution -Source $Source -Destination $Target\n', encoding='utf-8')
            result = subprocess.run([SHELL, '-NoProfile', '-NonInteractive', '-File', str(script),
                                     str(ROOT / 'tools/build_distribution.ps1'), str(source), str(target)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({p.name for p in target.iterdir()}, set(public))
