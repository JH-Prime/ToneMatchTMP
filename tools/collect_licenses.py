"""잠금 파일에 적힌 Python 배포판의 라이선스 원문과 목록을 수집한다."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import shutil
from pathlib import Path

from packaging.requirements import Requirement


def _requirement_names(path: Path) -> list[str]:
    """requirements.txt에서 옵션과 주석을 제외한 배포판 이름을 읽는다."""
    names: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        names.append(Requirement(line).name)
    return names


def _license_files(distribution: metadata.Distribution) -> list[Path]:
    """설치 배포판 안에서 LICENSE·COPYING·NOTICE 계열 파일을 찾는다."""
    found: list[Path] = []
    for relative in distribution.files or ():
        lowered = str(relative).replace("\\", "/").lower()
        file_name = Path(str(relative)).name.lower()
        if (
            ".dist-info/licenses/" in lowered
            or file_name.startswith("license")
            or file_name.startswith("copying")
            or file_name.startswith("notice")
        ):
            absolute = Path(distribution.locate_file(relative))
            if absolute.is_file():
                found.append(absolute)
    return sorted(set(found), key=lambda item: str(item).lower())


def collect(requirements: Path, destination: Path, inventory: Path) -> None:
    """라이선스 파일을 구성요소별 폴더로 복사하고 사람이 읽는 목록을 쓴다."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    lines = [
        "ToneMatch TMP 0.0.03 - Python Runtime/Build Dependency Inventory",
        "=================================================================",
        "",
        "Generated from the pinned requirements and installed package metadata.",
        "The AI model weights are not included in the distribution.",
        "",
    ]
    for requested_name in _requirement_names(requirements):
        distribution = metadata.distribution(requested_name)
        canonical_name = distribution.metadata.get("Name", requested_name)
        version = distribution.version
        license_expression = (
            distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License")
            or "See copied license files and project metadata"
        )
        project_url = distribution.metadata.get("Home-page", "")
        if not project_url:
            for value in distribution.metadata.get_all("Project-URL") or ():
                if "," in value:
                    label, candidate = value.split(",", 1)
                    if label.strip().lower() in {"homepage", "source", "repository"}:
                        project_url = candidate.strip()
                        break
        component_dir = destination / f"{canonical_name}-{version}"
        copied: list[str] = []
        for index, source in enumerate(_license_files(distribution), start=1):
            target_name = source.name
            if (component_dir / target_name).exists():
                target_name = f"{index:03d}-{target_name}"
            component_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, component_dir / target_name)
            copied.append(f"licenses/runtime/{component_dir.name}/{target_name}")
        lines.extend(
            [
                f"{canonical_name} {version}",
                f"  License metadata: {' '.join(str(license_expression).splitlines())}",
                f"  Project: {project_url or '(see package metadata)'}",
                f"  Copied license files: {', '.join(copied) if copied else '(none exposed by wheel)' }",
                "",
            ]
        )
    inventory.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    """명령행 경로를 해석하여 라이선스 수집 작업을 실행한다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    arguments = parser.parse_args()
    collect(arguments.requirements.resolve(), arguments.destination.resolve(), arguments.inventory.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
