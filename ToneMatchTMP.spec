# -*- mode: python ; coding: utf-8 -*-

"""ToneMatch TMP 0.0.04 Windows x64 onedir 배포 사양이다.

PyTorch와 Demucs는 단일 파일 압축 해제 방식보다 onedir에서 첫 실행과 모델
로딩이 안정적이다. AI 모델 가중치는 포함하지 않고 첫 분리 시 사용자 캐시에
받는다.
"""

from PyInstaller.utils.hooks import collect_all, copy_metadata


APP_VERSION = "0.0.04"
APP_BASENAME = f"ToneMatchTMP-v{APP_VERSION}"

source_files = [
    ("app.py", "devsource"),
    ("catalog.py", "devsource"),
    ("debug_info.py", "devsource"),
    ("devices.py", "devsource"),
    ("engine.py", "devsource"),
    ("i18n.py", "devsource"),
    ("recorder.py", "devsource"),
    ("report.py", "devsource"),
    ("separator.py", "devsource"),
    ("voicing.py", "devsource"),
]

notice_files = [
    ("LICENSE.txt", "notices"),
    ("THIRD_PARTY_NOTICES.txt", "notices"),
    ("THIRD_PARTY_RUNTIME_INVENTORY.txt", "notices"),
    ("licenses", "notices/licenses"),
]

# Demucs는 실제 분리 시점에 동적으로 여러 하위 모듈을 불러오므로 패키지
# 전체를 수집한다. torch 자체는 PyInstaller의 공식 hook에 맡긴다.
dynamic_packages = [
    "demucs",
    "huggingface_hub",
    "safetensors",
    "sphn",
    "soundcard",
    "julius",
    "einops",
    "lameenc",
    "yaml",
    "tqdm",
    "httpx",
    "httpcore",
    "hf_xet",
]

extra_datas = []
extra_binaries = []
hidden_imports = []
for package_name in dynamic_packages:
    package_datas, package_binaries, package_hidden = collect_all(package_name)
    extra_datas += package_datas
    extra_binaries += package_binaries
    hidden_imports += package_hidden

# 버전 조회와 Hugging Face 다운로드가 frozen 환경에서도 동작하도록 핵심
# dist-info 메타데이터를 명시적으로 보존한다.
for distribution_name in (
    "demucs",
    "huggingface-hub",
    "safetensors",
    "sphn",
    "SoundCard",
):
    extra_datas += copy_metadata(distribution_name)

a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[("resources/ffmpeg.exe", "resources")] + extra_binaries,
    datas=source_files + notice_files + extra_datas,
    hiddenimports=sorted(set(hidden_imports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "pandas", "scipy", "torchaudio", "torchvision"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_BASENAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_BASENAME,
)
