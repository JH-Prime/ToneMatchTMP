"""Native Windows package identity and writable state, with no GUI dependencies.

Only APPMODEL_ERROR_NO_PACKAGE permits the portable updater on Windows. An
identity lookup failure keeps the app usable in per-user storage and disables
that updater; a user-controlled environment flag never selects the channel.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
import re
import sys
from typing import Literal


_ERROR_INSUFFICIENT_BUFFER = 122
_APPMODEL_ERROR_NO_PACKAGE = 15700
_ERROR_INVALID_DATA = 13
_ERROR_PROC_NOT_FOUND = 127
_FAMILY_NAME = re.compile(r'[A-Za-z0-9.-]{3,50}_[A-Za-z0-9]{13}')


@dataclass(frozen=True)
class PackageIdentity:
    status: Literal['packaged', 'unpackaged', 'unknown']
    family_name: str | None = None
    error_code: int | None = None


@lru_cache(maxsize=1)
def package_identity() -> PackageIdentity:
    """Read process identity once; Windows API errors are never 'unpackaged'."""
    if sys.platform != 'win32':
        return PackageIdentity('unpackaged')
    try:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        full_name = kernel.GetCurrentPackageFullName
        family_name = kernel.GetCurrentPackageFamilyName
        for function in (full_name, family_name):
            function.argtypes = [ctypes.POINTER(ctypes.c_uint32), wintypes.LPWSTR]
            function.restype = wintypes.LONG
    except (AttributeError, OSError) as exc:
        return PackageIdentity('unknown', error_code=getattr(exc, 'winerror', None) or _ERROR_PROC_NOT_FOUND)

    try:
        length = ctypes.c_uint32()
        result = full_name(ctypes.byref(length), None)
        if result == _APPMODEL_ERROR_NO_PACKAGE:
            return PackageIdentity('unpackaged')
        if result != _ERROR_INSUFFICIENT_BUFFER:
            return PackageIdentity('unknown', error_code=result or _ERROR_INVALID_DATA)

        length.value = 0
        result = family_name(ctypes.byref(length), None)
        if result != _ERROR_INSUFFICIENT_BUFFER:
            return PackageIdentity('unknown', error_code=result or _ERROR_INVALID_DATA)
        # A family has at most 50 name characters, '_', 13 publisher-ID
        # characters and the null terminator. Never allocate an unbounded size.
        if not 2 <= length.value <= 65:
            return PackageIdentity('unknown', error_code=_ERROR_INVALID_DATA)
        buffer = ctypes.create_unicode_buffer(length.value)
        result = family_name(ctypes.byref(length), buffer)
        if result != 0:
            return PackageIdentity('unknown', error_code=result)
        if not _FAMILY_NAME.fullmatch(buffer.value):
            return PackageIdentity('unknown', error_code=_ERROR_INVALID_DATA)
        return PackageIdentity('packaged', family_name=buffer.value)
    except OSError as exc:
        return PackageIdentity('unknown', error_code=getattr(exc, 'winerror', None) or _ERROR_INVALID_DATA)


def managed_data_root() -> Path | None:
    """Use package LocalState, or safe per-user data if identity is unknown.

    None preserves the application's existing portable data policy. This helper
    only chooses a location; normal application startup creates it when needed.
    """
    identity = package_identity()
    if identity.status == 'unpackaged':
        return None
    local = Path(os.environ.get('LOCALAPPDATA', ''))
    if not local.is_absolute():
        local = Path.home() / 'AppData' / 'Local'
    if identity.status == 'packaged' and _FAMILY_NAME.fullmatch(identity.family_name or ''):
        return local / 'Packages' / identity.family_name / 'LocalState'
    return local / 'ToneMatchTMP'


def configure_runtime_cache() -> None:
    """Call before NumPy/librosa/Numba imports to avoid installed-file writes."""
    data_root = managed_data_root()
    if data_root is not None:
        os.environ['NUMBA_CACHE_DIR'] = str(data_root / 'cache' / 'numba')
