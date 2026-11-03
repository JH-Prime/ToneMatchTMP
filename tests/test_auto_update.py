"""Offline updater contracts; no GUI, real executable launch or live network."""
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

import auto_update as updater


VERSION = '0.1.08'
BASE = 'ToneMatchTMP-v' + VERSION


def archive_bytes(extra=None, change_manifest=None):
    files = {BASE + '.exe': b'MZ offline fixture, never executed', '_internal/library.dll': b'runtime'}
    manifest = {'schema': 'tonematch-portable-manifest/v1', 'app_version': VERSION,
                'file_count': len(files), 'files': [
                    {'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                    for name, data in files.items()]}
    if change_manifest:
        change_manifest(manifest)
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        for name, contents in files.items():
            package.writestr(BASE + '/' + name, contents)
        package.writestr(BASE + '/MANIFEST.json', json.dumps(manifest))
        for name, contents in extra or []:
            package.writestr(name, contents)
    return data.getvalue()


def release(data, version=VERSION):
    name = f'ToneMatchTMP-v{version}-Windows-x64-Portable-Dev.zip'
    return {'tag_name': 'v' + version, 'draft': False, 'prerelease': True,
            'published_at': '2026-11-02T14:00:00Z', 'assets': [{
                'name': name, 'size': len(data), 'state': 'uploaded',
                'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
                'browser_download_url': f'https://github.com/JH-Prime/ToneMatchTMP/releases/download/v{version}/{name}'}]}


class Response(io.BytesIO):
    def __init__(self, data, url):
        super().__init__(data)
        self.url = url
    def geturl(self):
        return self.url


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.install = self.root / 'portable'
        self.install.mkdir()
        (self.install / 'user-result.json').write_text('preserve')
        self.cache = self.root / 'updates'
        self.cancel = threading.Event()
        self.progress = []

    def prepare(self, data=None, releases=None, fail=None, callback=None):
        data = archive_bytes() if data is None else data
        payload = [release(data)] if releases is None else releases
        def open_url(url):
            if fail:
                raise fail
            return Response(json.dumps(payload).encode() if url == updater.RELEASES_URL else data, url)
        def progress(*values):
            self.progress.append(values)
            if callback:
                callback(*values)
        with patch.object(updater, '_open', side_effect=open_url):
            return updater.prepare_update('0.1.07', self.install, self.cache, self.cancel, progress)

    def test_numeric_versions_and_only_newer_published_assets(self):
        self.assertGreater(updater.parse_version('0.1.10'), updater.parse_version('0.1.09'))
        for value in ('v0.1.08', '1.2', '1.2.3.4', '1.2.-1', '1.2.3-rc1', '../1.2.3', '1.2.3 ', True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                updater.parse_version(value)
        data = archive_bytes()
        for adjust in (lambda row: row.update(draft=True), lambda row: row.update(published_at=None),
                       lambda row: row['assets'][0].update(digest=None),
                       lambda row: row['assets'][0].update(state='new'),
                       lambda row: row['assets'][0].update(browser_download_url='https://evil.example/app.zip'),
                       lambda row: row['assets'][0].update(name='unexpected.exe')):
            row = release(data)
            adjust(row)
            with self.subTest(row=row):
                self.assertIsNone(updater.select_release([row], '0.1.07'))
        self.assertIsNone(updater.select_release([release(data, '0.1.07')], '0.1.07'))
        self.assertIsNone(updater.select_release([release(data, '0.1.06')], '0.1.07'))
        self.assertEqual(updater.select_release([release(data)], '0.1.07').version, VERSION)

    def test_valid_archive_installs_separately_and_offline_cache_reuses(self):
        target = self.prepare()
        self.assertEqual(target.name, BASE + '.exe')
        self.assertTrue(target.is_file())
        self.assertNotIn(self.install, target.parents)
        self.assertEqual((self.install / 'user-result.json').read_text(), 'preserve')
        self.assertEqual(self.prepare(fail=OSError('offline')), target)
        self.assertTrue(any(stage == 'downloading' and done == total for stage, done, total in self.progress))

    def test_network_failure_without_cache_returns_current(self):
        self.assertIsNone(self.prepare(fail=OSError('offline')))

    def test_corrupt_archive_or_manifest_does_not_activate(self):
        original = archive_bytes()
        self.assertIsNone(self.prepare(data=b'not a zip', releases=[release(original)]))
        for change in (lambda m: m.update(app_version='0.1.09'),
                       lambda m: m['files'][0].update(sha256='0' * 64),
                       lambda m: m['files'][0].update(bytes=999),
                       lambda m: m['files'].pop()):
            with self.subTest(change=change):
                self.assertIsNone(self.prepare(data=archive_bytes(change_manifest=change)))
        self.assertFalse(list(self.cache.rglob('current.json')))

    def test_path_alias_traversal_and_unlisted_entries_rejected(self):
        for name in ('../escape', '/absolute', BASE + '/../escape', BASE + '/AUX.txt',
                     BASE + '/trailing. ', BASE + '/file:stream', BASE + '/a\\b',
                     BASE + '/_internal/../x', 'other/file', BASE + '/extra.txt',
                     BASE + '/MANIFEST.JSON'):
            with self.subTest(name=name):
                self.assertIsNone(self.prepare(data=archive_bytes([(name, b'x')])) )
        self.assertFalse((self.root / 'escape').exists())

    def test_symlinks_and_zip_bombs_rejected(self):
        symlink = zipfile.ZipInfo(BASE + '/link')
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.assertIsNone(self.prepare(data=archive_bytes([(symlink, b'/outside')])) )
        with patch.object(updater, 'MAX_EXPANDED_BYTES', 10):
            self.assertIsNone(self.prepare())

    def test_cancelled_download_never_activates(self):
        self.assertIsNone(self.prepare(callback=lambda stage, *_: self.cancel.set() if stage == 'downloading' else None))
        self.assertFalse(list(self.cache.rglob('current.json')))

    def test_cancelled_verification_never_hands_off(self):
        self.assertIsNone(self.prepare(callback=lambda stage, *_: self.cancel.set() if stage == 'verifying' else None))
        self.assertFalse(list(self.cache.rglob('current.json')))

    def test_corrupt_cached_manifest_is_not_launched(self):
        target = self.prepare()
        target.write_bytes(b'changed')
        self.assertIsNone(self.prepare(fail=OSError('offline')))

    def test_unreferenced_directory_must_match_verified_download(self):
        managed = updater.installation_cache(self.install, self.cache)
        versions = managed / 'versions'
        versions.mkdir(parents=True)
        target = versions / BASE
        with zipfile.ZipFile(io.BytesIO(archive_bytes())) as package:
            package.extractall(versions)
        # A self-consistent manifest cannot authenticate an abandoned folder.
        executable = target / (BASE + '.exe')
        executable.write_bytes(b'planted, never executed')
        manifest = json.loads((target / 'MANIFEST.json').read_text())
        manifest['files'][0].update(bytes=executable.stat().st_size,
                                   sha256=hashlib.sha256(executable.read_bytes()).hexdigest())
        (target / 'MANIFEST.json').write_text(json.dumps(manifest))
        self.assertIsNone(self.prepare())
        self.assertFalse((managed / 'current.json').exists())
        self.assertEqual(executable.read_bytes(), b'planted, never executed')

    def test_complete_directory_without_pointer_recovers_from_verified_download(self):
        managed = updater.installation_cache(self.install, self.cache)
        versions = managed / 'versions'
        versions.mkdir(parents=True)
        with zipfile.ZipFile(io.BytesIO(archive_bytes())) as package:
            package.extractall(versions)
        self.assertEqual(self.prepare(), versions / BASE / (BASE + '.exe'))
        self.assertTrue((managed / 'current.json').is_file())

    def test_cache_pointer_cannot_escape_managed_versions(self):
        target = self.prepare()
        pointer = next(self.cache.rglob('current.json'))
        pointer.write_text(json.dumps({'version': '../portable', 'manifest_sha256': '0'*64}))
        self.assertIsNone(self.prepare(fail=OSError('offline')))
        self.assertTrue(target.exists())

    def test_competing_transaction_returns_current_without_waiting(self):
        managed = updater.installation_cache(self.install, self.cache)
        managed.mkdir(parents=True)
        with updater._cache_lock(managed):
            self.assertIsNone(self.prepare())

    def test_installations_use_separate_cache_names(self):
        self.assertNotEqual(updater.installation_cache(self.install, self.cache),
                            updater.installation_cache(self.root / 'other', self.cache))

    def test_untrusted_redirect_destinations_rejected(self):
        for url in ('http://github.com/a', 'https://evil.example/a',
                    'https://github.com@evil.example/a', 'https://github.com:444/a',
                    'https://github.com/other/repo/releases/download/a/b'):
            with self.subTest(url=url), self.assertRaises(updater.UpdateError):
                updater._validate_url(url)

    def test_offline_diagnostic_requires_no_network(self):
        with patch.object(updater, '_open', side_effect=AssertionError('network forbidden')):
            result = updater.offline_self_test()
            self.assertTrue(result['ok'])
            self.assertTrue(result['archive_verified'])
            self.assertTrue(result['tamper_rejected'])


if __name__ == '__main__':
    unittest.main()
