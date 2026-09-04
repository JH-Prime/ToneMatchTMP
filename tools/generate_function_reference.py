"""배포 Python 소스의 모든 함수와 한글 docstring을 Markdown 표로 만든다."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE_NAMES = (
    "app.py",
    "catalog.py",
    "debug_info.py",
    "devices.py",
    "engine.py",
    "i18n.py",
    "recorder.py",
    "report.py",
    "separator.py",
    "voicing.py",
    "tests/test_developer_mode.py",
    "tests/test_engine.py",
    "tests/test_separator.py",
    "tests/test_voicing.py",
    "tools/collect_licenses.py",
    "tools/generate_function_reference.py",
    "tools/write_manifest.py",
)


def _function_rows(path: Path) -> list[tuple[int, str, str]]:
    """한 소스 파일에서 함수 줄 번호·정규 이름·설명을 소스 순으로 모은다."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rows: list[tuple[int, str, str]] = []

    def walk(body: list[ast.stmt], prefix: str = "") -> None:
        """클래스와 중첩 함수의 이름 경로를 유지하며 AST 본문을 순회한다."""
        for node in body:
            if isinstance(node, ast.ClassDef):
                walk(node.body, f"{prefix}{node.name}.")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified = f"{prefix}{node.name}"
                description = " ".join((ast.get_docstring(node) or "설명 누락").split())
                rows.append((node.lineno, qualified, description))
                walk(node.body, f"{qualified}.<local>.")

    walk(list(tree.body))
    return sorted(rows)


def generate(project_root: Path, output: Path) -> None:
    """모든 배포 모듈의 함수 설명을 버전이 적힌 단일 문서로 저장한다."""
    lines = [
        "# ToneMatch TMP 0.0.04 함수 설명서",
        "",
        "이 문서는 배포 소스의 모든 함수와 한국어 docstring을 자동으로 모은 색인입니다.",
        "앱의 `개발자 옵션`에서는 처리 순서 블록을 클릭해 같은 함수의 실제 소스와 원본 줄 번호를 볼 수 있습니다.",
        "",
    ]
    total = 0
    for file_name in SOURCE_NAMES:
        rows = _function_rows(project_root / file_name)
        lines.extend([f"## `{file_name}`", "", "| 줄 | 함수 | 설명 |", "|---:|---|---|"])
        for line_number, name, description in rows:
            escaped = description.replace("|", "\\|")
            lines.append(f"| {line_number} | `{name}` | {escaped} |")
        if not rows:
            lines.append("| - | 함수 없음 | 상수·카탈로그 데이터 모듈 |")
        lines.append("")
        total += len(rows)
    lines.extend(["---", "", f"총 함수 수: **{total}**", ""])
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    """현재 프로젝트 기준 함수 색인을 기본 파일명으로 생성한다."""
    project_root = Path(__file__).resolve().parents[1]
    generate(project_root, project_root / "FUNCTION_REFERENCE_KO.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
