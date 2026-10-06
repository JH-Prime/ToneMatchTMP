"""현재 유효 코드표를 한글 글꼴이 포함된 A4 벡터 PDF로 안전하게 저장한다."""

from pathlib import Path
import os
import sys
import tempfile

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4

from chord_chart import build_chord_chart, initial_chart_settings
from chord_edits import effective_voicing
from stem_removal import _commit_new_output
from voicing import pitch_class_names


FONT = "ToneMatchNanum"
MARGIN = 36
WIDTH, HEIGHT = A4
CONTENT_WIDTH = WIDTH - 2 * MARGIN


class PdfExportCancelled(RuntimeError):
    """사용자가 저장을 취소했으며 완성 파일은 만들지 않았다."""


def _font():
    """설치된 OS 글꼴이 아니라 배포에 포함한 OFL 글꼴만 사용한다."""
    if FONT not in pdfmetrics.getRegisteredFontNames():
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        path = root / "resources" / "fonts" / "NanumGothic-Regular.ttf"
        if not path.is_file():
            raise FileNotFoundError("PDF Korean font is missing: NanumGothic-Regular.ttf")
        pdfmetrics.registerFont(TTFont(FONT, str(path)))


def _text(value):
    """제어 문자와 글꼴에 없는 문자는 안전한 표시로 대체한다."""
    widths = pdfmetrics.getFont(FONT).face.charWidths
    return "".join(character if ord(character) in widths and ord(character) >= 32 else "?"
                   for character in str(value))


def _wrap(text, width=CONTENT_WIDTH, size=9):
    """한글과 긴 코드 이름도 실제 글꼴 폭으로 줄바꿈해 잘리지 않게 한다."""
    lines, line, used = [], "", 0.
    for character in _text(text):
        advance = pdfmetrics.stringWidth(character, FONT, size)
        if line and used + advance > width:
            lines.append(line)
            line, used = "", 0.
        line += character
        used += advance
    return lines + ([line] if line else [""])


def _draw_text(canvas, x, y, text, size=9):
    """문자열을 PDF 명령이나 마크업으로 평가하지 않는다."""
    canvas.setFont(FONT, size)
    canvas.drawString(x, y, _text(text))


def _header(canvas, title, subtitle):
    """일관된 제목과 페이지 머리말을 그린다."""
    canvas.setFillColorRGB(.05, .16, .2)
    _draw_text(canvas, MARGIN, HEIGHT - 43, title, 18)
    canvas.setFillColorRGB(.25, .3, .33)
    for index, line in enumerate(_wrap(subtitle, size=9)[:2]):
        _draw_text(canvas, MARGIN, HEIGHT - 62 - 13 * index, line)
    canvas.setStrokeColorRGB(.15, .55, .5)
    canvas.line(MARGIN, HEIGHT - 92, WIDTH - MARGIN, HEIGHT - 92)


def _footer(canvas, language):
    """수동 격자·수정·미확정의 의미를 모든 페이지에 남긴다."""
    canvas.setFillColorRGB(.3, .33, .35)
    note = ("수동 BPM/마디 격자 · ? 미확정 · * 사용자 수정 · 정확한 채보 보장 아님"
            if language == "ko" else "Manual tempo/bar grid | ? unknown | * user edit | Estimates, not verified transcription")
    _draw_text(canvas, MARGIN, 30, note, 8)
    canvas.setFont(FONT, 8)
    canvas.drawRightString(WIDTH - MARGIN, 16, str(canvas.getPageNumber()))


def _draw_chart_page(canvas, chart, page, title, subtitle, language):
    """16마디 본문은 기호 우선으로 그리고 밀집 변화는 상세 영역을 참조한다."""
    _header(canvas, title, subtitle)
    cell_width, cell_height, top = CONTENT_WIDTH / 4, 105, HEIGHT - 112
    for row_index, row in enumerate(page["rows"]):
        for column, bar in enumerate(row):
            x, y = MARGIN + column * cell_width, top - row_index * cell_height
            canvas.setStrokeColorRGB(.75, .78, .78)
            canvas.rect(x, y - cell_height, cell_width, cell_height, fill=0)
            canvas.setFillColorRGB(.4, .43, .45)
            _draw_text(canvas, x + 7, y - 14, f'{bar["number"]} | {bar["absolute_start_seconds"]:.2f}s', 8)
            for index, segment in enumerate(bar["segments"][:3]):
                label = segment["label"] + (" *" if segment.get("manual_edit") else "")
                prefix = "~ " if segment["continues_from_previous"] else ""
                size = min(15., (cell_width - 16) / max(.01, pdfmetrics.stringWidth(prefix + label, FONT, 1)))
                canvas.setFillColorRGB(.06, .16, .2)
                _draw_text(canvas, x + 8, y - 35 - 21 * index, prefix + label, size)
            canvas.setFillColorRGB(.4, .43, .45)
            if len(bar["segments"]) > 3:
                marker = f'+{len(bar["segments"]) - 3} ' + ("상세 참조" if language == "ko" else "see details")
                _draw_text(canvas, x + 8, y - 95, marker, 8)
    _footer(canvas, language)
    # 상세 줄은 차트 아래에서 시작하고 다음 보충 페이지로 계속된다.
    return top - 4 * cell_height - 26


def _detail_lines(page, events, language):
    """마디 내 모든 구간과 원래 이벤트 ID·근거·후보를 빠짐없이 연결한다."""
    lines = []
    seen = set()
    for bar in page["bars"]:
        for segment in bar["segments"]:
            index = segment["event_index"]
            identifier = f"#{index + 1} " if index is not None else ""
            label = segment["label"] + (" *" if segment.get("manual_edit") else "")
            line = (f'{bar["number"]} | {segment["absolute_start_seconds"]:.2f}-'
                    f'{segment["absolute_end_seconds"]:.2f}s | {identifier}{label}')
            lines.extend(_wrap(line))
            if index is None or index in seen:
                continue
            seen.add(index)
            event = events[index]
            if event.get("manual_edit"):
                detail = ("사용자 수정; 원래 추정: " if language == "ko" else "User edit; original estimate: ")
                lines.extend(_wrap("  " + detail + str(event.get("original_symbol", "?"))))
                continue
            evidence = event.get("evidence") or {}
            notes = pitch_class_names(evidence.get("observed_pitch_classes", event.get("pitch_classes", []))) or "?"
            candidates = ", ".join(str(candidate.get("symbol", "?")) for candidate in event.get("alternatives", [])[:3]) or "-"
            detail = (f"  관측음: {notes} | 후보: {candidates}" if language == "ko"
                      else f"  Observed: {notes} | Candidates: {candidates}")
            lines.extend(_wrap(detail))
    return lines


def save_chart_pdf(result, destination, *, cancel_requested=None):
    """완료된 PDF만 배타적으로 확정하고 실패·취소 시 임시 출력만 정리한다."""
    def check():
        if cancel_requested and cancel_requested():
            raise PdfExportCancelled("PDF export cancelled")

    check()
    target = Path(destination)
    if target.suffix.lower() != ".pdf":
        raise ValueError("Choose a .pdf destination")
    target = target.parent.resolve(strict=True) / target.name
    if os.path.lexists(target):
        raise FileExistsError("Choose a new PDF filename; existing files are protected")
    _font()
    analysis = effective_voicing(result)
    if len(analysis.get("events", [])) > 10000:
        raise ValueError("Too many PDF events")
    settings = initial_chart_settings(result)
    settings.update(result.get("chord_chart_settings") or {})
    settings["page_size"] = 16
    # 표시 격자에서만 허용한 설정을 전달해 임의 키를 실행 경계로 넘기지 않는다.
    chart = build_chord_chart(analysis, **{key: settings[key] for key in (
        "bpm", "beats_per_bar", "first_downbeat_seconds", "page_size", "duration_seconds")})
    if not chart["pages"]:
        raise ValueError("No chart duration to export")
    if chart["bar_count"] > 10000:
        raise ValueError("Too many PDF bars")
    language = result.get("language", "ko")
    title = "코드 진행" if language == "ko" else "Chord progression"
    source_name = Path(str(result.get("source", {}).get("file_name", "Audio")).replace("\\", "/")).name[:120]
    descriptor, temporary_name = tempfile.mkstemp(prefix=".chart-", suffix=".partial.pdf", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    total_pages = detail_pages = 0
    try:
        canvas = Canvas(str(temporary), pagesize=A4, pageCompression=1)
        canvas.setTitle(source_name + " - " + title)
        canvas.setAuthor("ToneMatch TMP")
        for page in chart["pages"]:
            check()
            subtitle = (f'{source_name} | {chart["bpm"]:g} BPM | {chart["beats_per_bar"]}/4 | '
                        f'{page["first_bar_number"]}-{page["last_bar_number"]} | '
                        f'{page["page_index"] + 1}/{chart["page_count"]}')
            y = _draw_chart_page(canvas, chart, page, title, subtitle, language)
            canvas.setFillColorRGB(.05, .16, .2)
            detail_title = "구간별 근거 / 후보" if language == "ko" else "Segment evidence / candidates"
            _draw_text(canvas, MARGIN, y, detail_title, 11)
            y -= 20
            for line in _detail_lines(page, analysis.get("events", []), language):
                check()
                if y < 54:
                    canvas.showPage()
                    total_pages += 1
                    detail_pages += 1
                    _header(canvas, detail_title, subtitle)
                    _footer(canvas, language)
                    canvas.setFillColorRGB(.1, .18, .2)
                    y = HEIGHT - 114
                _draw_text(canvas, MARGIN, y, line)
                y -= 13
            canvas.showPage()
            total_pages += 1
        canvas.save()
        check()
        _commit_new_output(temporary, target, language)
    finally:
        temporary.unlink(missing_ok=True)
    return {"path": str(target), "page_count": total_pages, "chart_pages": chart["page_count"],
            "detail_pages": detail_pages, "bar_count": chart["bar_count"]}
