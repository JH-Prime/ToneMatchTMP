"""개발자 옵션의 블록 매핑, 번들 소스, 한글 함수 설명을 검증한다."""

from __future__ import annotations

import ast
import re
import sys
import tkinter as tk
import unittest
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import catalog  # noqa: E402
import debug_info  # noqa: E402
from app import ToneMatchApp  # noqa: E402


class DeveloperModeTests(unittest.TestCase):
    """개발자 화면이 약속한 코드와 설명을 실제로 제공하는지 확인한다."""

    def test_version_and_latest_changelog_match(self) -> None:
        """앱 버전은 두 자리 패치 규칙이며 최신 변경 기록과 같아야 한다."""
        self.assertRegex(catalog.APP_VERSION, r"^0\.0\.\d{2}$")
        self.assertEqual(catalog.CHANGELOG[0]["version"], catalog.APP_VERSION)
        self.assertTrue(catalog.CHANGELOG[0]["changes"])

    def test_pipeline_order_and_source_links_are_complete(self) -> None:
        """블록 번호가 연속이고 각 클릭 대상에서 실제 코드가 추출되는지 검사한다."""
        blocks = debug_info.PIPELINE_BLOCKS
        self.assertEqual([block["order"] for block in blocks], list(range(1, len(blocks) + 1)))
        self.assertEqual(blocks[0]["id"], "boot")
        self.assertEqual(blocks[-1]["id"], "export")
        for block in blocks:
            code = debug_info.code_for_block(block["id"])
            self.assertIn("def ", code, block["id"])
            self.assertNotIn("소스 위치를 찾지 못했습니다", code, block["id"])

    def test_every_function_has_korean_docstring(self) -> None:
        """배포 소스의 모든 함수가 개발자에게 보이는 한글 설명을 갖는지 검사한다."""
        korean = re.compile(r"[가-힣]")
        source_files = (
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
        missing: list[str] = []
        non_korean: list[str] = []
        for file_name in source_files:
            path = MODULE_DIR / file_name
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                description = ast.get_docstring(node)
                label = f"{file_name}:{node.lineno}:{node.name}"
                if not description:
                    missing.append(label)
                elif not korean.search(description):
                    non_korean.append(label)
        self.assertEqual(missing, [], f"함수 설명 누락: {missing}")
        self.assertEqual(non_korean, [], f"한글 함수 설명 누락: {non_korean}")

    def test_progress_maps_to_sequence_blocks(self) -> None:
        """대표 진행률이 입력부터 결과까지 순서대로 해당 블록을 가리키는지 확인한다."""
        checkpoints = [(2, "input"), (10, "decode"), (36, "separation"), (72, "features"), (82, "voicing"), (87, "correction"), (90, "matching"), (94, "recipe"), (97, "result")]
        for progress, expected in checkpoints:
            self.assertEqual(debug_info.block_for_progress(progress), expected)

    def test_debug_diagram_fits_and_displays_source(self) -> None:
        """개발자 탭의 모든 블록이 화면 안에 들어오고 코드 내용이 표시되는지 확인한다."""
        root = tk.Tk()
        root.withdraw()
        try:
            application = ToneMatchApp(root)
            root.update_idletasks()
            application.developer_var.set(True)
            application._toggle_developer_mode()
            root.update_idletasks()
            bounds = application.debug_canvas.bbox("all")
            self.assertIsNotNone(bounds)
            self.assertEqual(len(application.debug_nodes), len(debug_info.PIPELINE_BLOCKS))
            self.assertLessEqual(bounds[3], application.debug_canvas.winfo_height())
            self.assertIn("def ", application.debug_code.get("1.0", "end-1c"))
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
