"""Verified, side-by-side portable updates; never replaces or launches an EXE.

Only project-controlled GitHub release assets are accepted. Hash validation is
integrity relative to GitHub metadata, not independent publisher code signing.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile


REPOSITORY = 'JH-Prime/ToneMatchTMP'
RELEASES_URL = f'https://api.github.com/repos/{REPOSITORY}/releases?per_page=100'
MAX_METADATA_BYTES = 4 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_EXPANDED_BYTES = 4 * 1024 * 1024 * 1024
MAX_ENTRIES = 20000
NETWORK_TIMEOUT = 7
MAX_DOWNLOAD_SECONDS = 15 * 60
CHUNK = 256 * 1024
_VERSION = re.compile(r'[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}\Z')
_DIGEST = re.compile(r'[0-9a-fA-F]{64}\Z')
_RESERVED = re.compile(r'(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?\Z', re.I)


class UpdateError(Exception):
    """An expected update failure that must leave the current app usable."""


class UpdateCancelled(UpdateError):
    pass


@dataclass(frozen=True)
class Release:
    version: str
    name: str
    url: str
    size: int
    digest: str


def parse_version(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        raise ValueError('Unsupported version')
    return tuple(int(part) for part in value.split('.'))


def select_release(payload, current_version: str) -> Release | None:
    """Choose the highest newer published portable build, including dev releases."""
    current = parse_version(current_version)
    if not isinstance(payload, list) or len(payload) > 100:
        raise UpdateError('Invalid release metadata')
    accepted = []
    for row in payload:
        if not isinstance(row, dict) or row.get('draft') is not False or not row.get('published_at'):
            continue
        tag = row.get('tag_name')
        if not isinstance(tag, str) or not tag.startswith('v'):
            continue
        version = tag[1:]
        try:
            parsed = parse_version(version)
        except ValueError:
            continue
        if parsed <= current:
            continue
        name = f'ToneMatchTMP-v{version}-Windows-x64-Portable-Dev.zip'
        assets = row.get('assets')
        if not isinstance(assets, list):
            continue
        matching = [a for a in assets if isinstance(a, dict) and a.get('name') == name]
        if len(matching) != 1:
            continue
        asset = matching[0]
        size, digest = asset.get('size'), asset.get('digest')
        expected_url = f'https://github.com/{REPOSITORY}/releases/download/{tag}/{name}'
        if (asset.get('state') != 'uploaded' or type(size) is not int or not 0 < size <= MAX_ARCHIVE_BYTES
                or not isinstance(digest, str) or not digest.startswith('sha256:')
                or not _DIGEST.fullmatch(digest[7:]) or asset.get('browser_download_url') != expected_url):
            continue
        accepted.append(Release(version, name, expected_url, size, digest[7:].lower()))
    return max(accepted, key=lambda release: parse_version(release.version), default=None)


def _validate_url(url: str) -> None:
    parts = urlsplit(url)
    try:
        port = parts.port
    except ValueError as exc:
        raise UpdateError('Untrusted update address') from exc
    if (parts.scheme != 'https' or parts.username or parts.password or port not in (None, 443)
            or parts.fragment or any(ord(char) < 32 for char in url)):
        raise UpdateError('Untrusted update address')
    if parts.hostname == 'api.github.com':
        valid = parts.path == f'/repos/{REPOSITORY}/releases'
    elif parts.hostname == 'github.com':
        valid = parts.path.startswith(f'/{REPOSITORY}/releases/download/')
    else:
        valid = parts.hostname == 'release-assets.githubusercontent.com'
    if not valid:
        raise UpdateError('Untrusted update address')


class _TrustedRedirect(HTTPRedirectHandler):
    max_repeats = 2
    max_redirections = 4

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url: str):
    _validate_url(url)
    request = Request(url, headers={'User-Agent': 'ToneMatchTMP-Updater',
                                  'Accept': 'application/vnd.github+json' if url == RELEASES_URL
                                  else 'application/octet-stream'})
    response = build_opener(_TrustedRedirect()).open(request, timeout=NETWORK_TIMEOUT)
    try:
        _validate_url(response.geturl())
    except Exception:
        response.close()
        raise
    return response


def _cancelled(cancel) -> None:
    if cancel.is_set():
        raise UpdateCancelled('Update cancelled')


def installation_cache(installation_root: Path, cache_root: Path) -> Path:
    """The original portable path gives each installation a separate cache."""
    identity = os.path.normcase(str(Path(installation_root).resolve()))
    key = hashlib.sha256(identity.encode('utf-8')).hexdigest()[:32]
    return Path(cache_root).resolve() / key


def _ordinary(path: Path) -> None:
    """Do not follow a junction/symlink while reading or modifying managed state."""
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise UpdateError('Unsafe update cache path')


@contextmanager
def _cache_lock(root: Path):
    path = root / 'update.lock'
    if path.exists() or path.is_symlink():
        _ordinary(path)
    stream = path.open('a+b')
    acquired = False
    try:
        if stream.seek(0, 2) == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError as exc:
            raise UpdateError('Another update is running') from exc
        yield
    finally:
        if acquired:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def _relative_parts(name: str) -> tuple[str, ...]:
    if not isinstance(name, str) or not name or '\\' in name or name.startswith('/'):
        raise UpdateError('Unsafe archive path')
    parts = tuple(name.split('/'))
    for part in parts:
        if (not part or part in ('.', '..') or part[-1] in (' ', '.') or _RESERVED.fullmatch(part)
                or any(ord(char) < 32 or char in '<>:"|?*' for char in part)):
            raise UpdateError('Unsafe archive path')
    return parts


def _digest_file(path: Path, cancel) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            _cancelled(cancel)
            chunk = stream.read(CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, limit: int):
    _ordinary(path)
    if path.stat().st_size > limit:
        raise UpdateError('Update metadata too large')
    return json.loads(path.read_text(encoding='utf-8'))


def verify_installation(root: Path, version: str, cancel, progress) -> str:
    """Verify every manifest entry and the actual file inventory before handoff."""
    parse_version(version)
    _ordinary(root)
    manifest_path = root / 'MANIFEST.json'
    manifest = _read_json(manifest_path, MAX_MANIFEST_BYTES)
    if (not isinstance(manifest, dict) or manifest.get('schema') != 'tonematch-portable-manifest/v1'
            or manifest.get('app_version') != version or not isinstance(manifest.get('files'), list)):
        raise UpdateError('Invalid portable manifest')
    files = manifest['files']
    if not 1 <= len(files) <= MAX_ENTRIES or manifest.get('file_count') != len(files):
        raise UpdateError('Invalid portable inventory')
    expected, total = {}, 0
    for row in files:
        if not isinstance(row, dict):
            raise UpdateError('Invalid portable inventory')
        parts = _relative_parts(row.get('path'))
        key = '/'.join(parts).casefold()
        size, digest = row.get('bytes'), row.get('sha256')
        if (key == 'manifest.json' or key in expected or type(size) is not int or size < 0
                or not isinstance(digest, str) or not _DIGEST.fullmatch(digest)):
            raise UpdateError('Invalid portable inventory')
        total += size
        if total > MAX_EXPANDED_BYTES:
            raise UpdateError('Portable installation too large')
        expected[key] = (parts, size, digest.lower())
    actual = set()
    for directory, directories, names in os.walk(root, followlinks=False):
        _cancelled(cancel)
        for name in directories + names:
            _ordinary(Path(directory) / name)
        for name in names:
            relative = (Path(directory) / name).relative_to(root).as_posix()
            key = relative.casefold()
            if key in actual:
                raise UpdateError('Duplicate installed path')
            actual.add(key)
            if len(actual) > MAX_ENTRIES + 1:
                raise UpdateError('Portable inventory too large')
    if actual != set(expected) | {'manifest.json'}:
        raise UpdateError('Portable inventory mismatch')
    executable = f'ToneMatchTMP-v{version}.exe'
    if executable.casefold() not in expected:
        raise UpdateError('Portable executable is missing')
    done = 0
    progress('verifying', done, total)
    for parts, size, digest in expected.values():
        _cancelled(cancel)
        path = root.joinpath(*parts)
        if path.stat().st_size != size or _digest_file(path, cancel) != digest:
            raise UpdateError('Portable file checksum mismatch')
        done += size
        progress('verifying', done, total)
    _cancelled(cancel)
    return _digest_file(manifest_path, cancel)


def _extract(archive: Path, destination: Path, release: Release, cancel) -> Path:
    expected_root = 'ToneMatchTMP-v' + release.version
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if not 1 <= len(entries) <= MAX_ENTRIES + 1:
            raise UpdateError('Archive inventory too large')
        seen, paths, total = set(), [], 0
        for entry in entries:
            _cancelled(cancel)
            name = entry.filename[:-1] if entry.is_dir() else entry.filename
            parts = _relative_parts(name)
            key = '/'.join(parts).casefold()
            mode = entry.external_attr >> 16
            if (parts[0] != expected_root or key in seen or entry.flag_bits & 1
                    or stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)
                    or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise UpdateError('Unsupported archive entry')
            seen.add(key)
            total += entry.file_size
            if total > MAX_EXPANDED_BYTES or entry.file_size > max(1, entry.compress_size) * 1000:
                raise UpdateError('Archive expansion limit exceeded')
            paths.append((entry, parts))
        if shutil.disk_usage(destination).free < total + 64 * 1024 * 1024:
            raise UpdateError('Insufficient space for update')
        for entry, parts in paths:
            _cancelled(cancel)
            target = destination.joinpath(*parts)
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with package.open(entry) as source, target.open('xb') as output:
                copied = 0
                while True:
                    _cancelled(cancel)
                    chunk = source.read(CHUNK)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > entry.file_size:
                        raise UpdateError('Archive size mismatch')
                    output.write(chunk)
                if copied != entry.file_size:
                    raise UpdateError('Truncated archive entry')
    return destination / expected_root


def _download(release: Release, target: Path, cancel, progress) -> None:
    digest, received = hashlib.sha256(), 0
    deadline = time.monotonic() + MAX_DOWNLOAD_SECONDS
    progress('downloading', 0, release.size)
    _cancelled(cancel)
    with _open(release.url) as source, target.open('xb') as output:
        while True:
            _cancelled(cancel)
            if time.monotonic() > deadline:
                raise UpdateError('Update download timed out')
            chunk = source.read(CHUNK)
            if not chunk:
                break
            received += len(chunk)
            if received > release.size:
                raise UpdateError('Update download size mismatch')
            output.write(chunk)
            digest.update(chunk)
            progress('downloading', received, release.size)
    _cancelled(cancel)
    if received != release.size or digest.hexdigest() != release.digest:
        raise UpdateError('Update download checksum mismatch')


def _cached(root: Path, current_version: str, cancel, progress) -> Path | None:
    pointer = root / 'current.json'
    if not pointer.exists():
        return None
    state = _read_json(pointer, 4096)
    if not isinstance(state, dict):
        raise UpdateError('Invalid update cache')
    version = state.get('version')
    if parse_version(version) <= parse_version(current_version):
        return None
    digest = state.get('manifest_sha256')
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise UpdateError('Invalid update cache')
    versions = root / 'versions'
    _ordinary(versions)
    target = versions / ('ToneMatchTMP-v' + version)
    if verify_installation(target, version, cancel, progress) != digest:
        raise UpdateError('Update cache checksum mismatch')
    return target / ('ToneMatchTMP-v' + version + '.exe')


def prepare_update(current_version: str, installation_root: Path, cache_root: Path,
                   cancel, progress) -> Path | None:
    """Prepare a newer verified executable, falling back safely on any I/O failure.

    Call on a worker thread. progress(stage, completed_bytes, total_bytes) must
    not touch Tk directly. None means continue with the installed application.
    """
    cached = None
    try:
        parse_version(current_version)
        _cancelled(cancel)
        root = installation_cache(installation_root, cache_root)
        root.mkdir(parents=True, exist_ok=True)
        _ordinary(root)
        with _cache_lock(root):
            try:
                cached = _cached(root, current_version, cancel, progress)
            except (OSError, ValueError, UpdateError):
                _cancelled(cancel)
            progress('checking', 0, 0)
            _cancelled(cancel)
            with _open(RELEASES_URL) as response:
                raw = response.read(MAX_METADATA_BYTES + 1)
            if len(raw) > MAX_METADATA_BYTES:
                raise UpdateError('Release metadata too large')
            release = select_release(json.loads(raw), current_version)
            _cancelled(cancel)
            if release is None:
                progress('ready' if cached else 'current', 0, 0)
                return None if cancel.is_set() else cached
            if cached and parse_version(cached.parent.name.removeprefix('ToneMatchTMP-v')) >= parse_version(release.version):
                progress('ready', 0, 0)
                return None if cancel.is_set() else cached
            versions = root / 'versions'
            versions.mkdir(exist_ok=True)
            _ordinary(versions)
            target = versions / ('ToneMatchTMP-v' + release.version)
            if shutil.disk_usage(root).free < release.size + 64 * 1024 * 1024:
                raise UpdateError('Insufficient space for update')
            with tempfile.TemporaryDirectory(prefix='staging-', dir=root) as staging_name:
                staging = Path(staging_name)
                archive = staging / 'download.zip'
                _download(release, archive, cancel, progress)
                progress('verifying', 0, 0)
                extracted = _extract(archive, staging, release, cancel)
                manifest_digest = verify_installation(extracted, release.version, cancel, progress)
                _cancelled(cancel)
                if target.exists():
                    # A crash can leave a complete directory without its
                    # pointer. Its own manifest is not provenance: bind it to
                    # the freshly authenticated archive before accepting it.
                    if verify_installation(target, release.version, cancel, progress) != manifest_digest:
                        raise UpdateError('Existing installation differs from verified release')
                else:
                    os.replace(extracted, target)
            _cancelled(cancel)
            state = {'version': release.version, 'manifest_sha256': manifest_digest}
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root,
                                             prefix='pointer-', delete=False) as stream:
                temporary_pointer = Path(stream.name)
                json.dump(state, stream)
            try:
                _cancelled(cancel)
                os.replace(temporary_pointer, root / 'current.json')
            finally:
                temporary_pointer.unlink(missing_ok=True)
            progress('ready', 0, 0)
            return None if cancel.is_set() else target / ('ToneMatchTMP-v' + release.version + '.exe')
    except UpdateCancelled:
        return None
    except (OSError, ValueError, UpdateError, zipfile.BadZipFile, EOFError):
        progress('unavailable', 0, 0)
        return None if cancel.is_set() else cached


def offline_self_test() -> dict:
    """Small frozen-runtime check with no network, GUI or process execution."""
    import threading

    version_order = parse_version('0.1.10') > parse_version('0.1.09')
    address_rejection = False
    try:
        _validate_url('https://example.invalid/update.zip')
    except UpdateError:
        address_rejection = True
    path_rejection = False
    try:
        _relative_parts('portable/../outside.exe')
    except UpdateError:
        path_rejection = True
    version = '0.1.08'
    base = 'ToneMatchTMP-v' + version
    files = {base + '.exe': b'MZ inert diagnostic fixture, never executed',
             '_internal/runtime.dll': b'inert runtime fixture'}
    manifest = {'schema': 'tonematch-portable-manifest/v1', 'app_version': version,
                'file_count': len(files), 'files': [
                    {'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                    for name, data in files.items()]}
    with tempfile.TemporaryDirectory(prefix='tonematch-update-check-') as temporary:
        directory = Path(temporary)
        archive = directory / 'fixture.zip'
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
            for name, data in files.items():
                package.writestr(base + '/' + name, data)
            package.writestr(base + '/MANIFEST.json', json.dumps(manifest))
        cancel = threading.Event()
        release = Release(version, archive.name, '', archive.stat().st_size, _digest_file(archive, cancel))
        extracted = _extract(archive, directory, release, cancel)
        archive_verified = bool(verify_installation(extracted, version, cancel, lambda *_: None))
        (extracted / (base + '.exe')).write_bytes(b'altered')
        tamper_rejected = False
        try:
            verify_installation(extracted, version, cancel, lambda *_: None)
        except UpdateError:
            tamper_rejected = True
    return {'ok': version_order and address_rejection and path_rejection and archive_verified and tamper_rejected,
            'version_order': version_order, 'address_rejection': address_rejection,
            'path_rejection': path_rejection, 'archive_verified': archive_verified,
            'tamper_rejected': tamper_rejected, 'network_used': False, 'process_launched': False}
