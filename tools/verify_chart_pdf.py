"""사용자 음원을 포함하지 않는 한영·밀집 PDF를 생성해 렌더 검증에 사용한다."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chart_pdf import save_chart_pdf
from chord_edits import set_correction
from tests.test_chart_pdf import pdf_result


def main():
    """새 QA 폴더에서만 저장하고 테스트 문서 경로와 페이지 수를 출력한다."""
    destination = ROOT / "build" / "qa-v0.1.01-pdf"
    destination.mkdir(parents=True, exist_ok=True)
    outputs = []
    for name, language, dense in (("korean", "ko", False), ("english-dense", "en", True)):
        result = set_correction(pdf_result(language, dense), 0, "Dm9")
        outputs.append(save_chart_pdf(result, destination / f"{name}.pdf"))
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
