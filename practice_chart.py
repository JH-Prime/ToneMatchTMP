"""Validated 4/4 practice charts, project files and offline AI prompts."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata

from chord_edits import parse_symbol
from voicing import CHORD_SUFFIX


STYLES = ("Rock", "Pop", "Ballad", "Funk", "Blues Shuffle", "Bossa Nova", "Jazz Swing")
MAX_BARS = 128
MAX_CHART_CHARS = 24_576
MAX_PROJECT_BYTES = 128 * 1024
_SCHEMA = "tonematch.practice/v1"
_DEFAULT_BEATS = ((), (4,), (2, 2), (2, 1, 1), (1, 1, 1, 1))
_SHARPS = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_FLATS = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
_KEY = re.compile(r"([A-G][#b]?) *(major|minor|maj|min|m)?", re.IGNORECASE)


class ChartError(ValueError):
    """Report where pasted chart text needs correction."""

    def __init__(self, line: int, bar: int | None, reason: str):
        self.line = line
        self.bar = bar
        location = f"line {line}" if bar is None else f"line {line}, bar {bar}"
        korean = f"{line}행" if bar is None else f"{line}행 {bar}마디"
        super().__init__(f"{korean} ({location}) · {reason}")


def _plain_text(value: str, limit: int, label: str) -> str:
    if (not isinstance(value, str) or len(value) > limit
            or any(unicodedata.category(char).startswith(("C", "Zl", "Zp")) for char in value)):
        raise ValueError(f"{label} 입력을 확인하세요. / Invalid {label.lower()}.")
    return value.strip()


def normalize_key(key: str) -> str:
    """Accept a bare tonic, major/minor label or common short form."""
    text = _plain_text(key, 24, "Key").replace("♭", "b").replace("♯", "#")
    if not text:
        return ""
    match = _KEY.fullmatch(text)
    if match is None:
        raise ValueError("키는 C, Bb Major, F# Minor 형식으로 입력하세요. / Use a key such as C, Bb Major or F# Minor.")
    tonic, quality = match.groups()
    quality = "Minor" if quality == "m" or (quality or "").lower() in ("min", "minor") else "Major"
    return f"{tonic[0].upper()}{tonic[1:].lower()} {quality}"


@dataclass(frozen=True)
class Bar:
    """A section start, if present, and one to four timed chord symbols."""

    section: str | None
    chords: tuple[str, ...]
    beats: tuple[int, ...]

    def __post_init__(self):
        if self.section is not None:
            section = _plain_text(self.section, 40, "Section")
            if not section or any(char in "[]|`" for char in section):
                raise ValueError("섹션 이름이 잘못되었습니다. / Invalid section name.")
            object.__setattr__(self, "section", section)
        if (not isinstance(self.chords, tuple) or not 1 <= len(self.chords) <= 4
                or not isinstance(self.beats, tuple) or len(self.beats) != len(self.chords)
                or any(type(beats) is not int or not 1 <= beats <= 4 for beats in self.beats)
                or sum(self.beats) != 4):
            raise ValueError("마디는 양의 정수 박자로 총 4박이어야 합니다. / A bar must total four whole beats.")
        symbols = tuple(symbol if symbol == "-" else parse_symbol(symbol)["symbol"]
                        for symbol in self.chords)
        object.__setattr__(self, "chords", symbols)


def _validate_bars(bars: tuple[Bar, ...]) -> None:
    if (not isinstance(bars, tuple) or not 1 <= len(bars) <= MAX_BARS
            or not all(isinstance(bar, Bar) for bar in bars)):
        raise ValueError(f"코드표는 1–{MAX_BARS}마디여야 합니다. / A chart needs 1–{MAX_BARS} bars.")


@dataclass(frozen=True)
class PracticeProject:
    """A self-contained synthetic accompaniment project with validated settings."""

    bars: tuple[Bar, ...]
    title: str = ""
    key: str = ""
    bpm: float = 110
    style: str = "Pop"
    count_in: int = 1
    loop: bool = True

    def __post_init__(self):
        _validate_bars(self.bars)
        object.__setattr__(self, "title", _plain_text(self.title, 160, "Title"))
        object.__setattr__(self, "key", normalize_key(self.key))
        # Ordered bounds reject NaN and infinities without converting huge JSON integers.
        if type(self.bpm) not in (int, float) or not 40 <= self.bpm <= 240:
            raise ValueError("템포는 40–240 BPM이어야 합니다. / Tempo must be 40–240 BPM.")
        if self.style not in STYLES:
            raise ValueError("반주 스타일이 잘못되었습니다. / Invalid accompaniment style.")
        if type(self.count_in) is not int or self.count_in not in (0, 1, 2) or type(self.loop) is not bool:
            raise ValueError("카운트인 또는 반복 설정이 잘못되었습니다. / Invalid count-in or loop setting.")

    @property
    def unresolved_bars(self) -> tuple[int, ...]:
        """Return one-based bar numbers requiring confirmation before rendering."""
        return tuple(number for number, bar in enumerate(self.bars, 1) if "?" in bar.chords)


def _parse_bar(text: str, section: str | None) -> Bar:
    tokens = text.split()
    if not 1 <= len(tokens) <= 4:
        raise ValueError("마디에 코드 또는 쉼표를 1–4개 넣으세요. / Enter one to four chords or rests per bar.")
    if not any(":" in token for token in tokens):
        return Bar(section, tuple(tokens), _DEFAULT_BEATS[len(tokens)])
    pairs = [token.rpartition(":") for token in tokens]
    if any(separator == "" or beats not in ("1", "2", "3", "4") for _, separator, beats in pairs):
        raise ValueError("마디 안의 박자는 모두 C:2 형식으로 적으세요. / Use whole-beat durations such as C:2 for all chords in this bar.")
    return Bar(section, tuple(symbol for symbol, _, _ in pairs), tuple(int(beats) for _, _, beats in pairs))


def parse_chart(text: str) -> tuple[Bar, ...]:
    """Parse pipe-separated bars with optional section headers and one outer fence."""
    if not isinstance(text, str) or len(text) > MAX_CHART_CHARS:
        raise ValueError("코드표가 너무 깁니다. / Chart text is too large.")
    lines = [(number, line.strip()) for number, line in enumerate(text.splitlines(), 1) if line.strip()]
    if lines and lines[0][1].startswith("```"):
        first_number, opening = lines[0]
        if (len(lines) < 2 or not re.fullmatch(r"```[A-Za-z0-9_+-]*", opening)
                or lines[-1][1] != "```"):
            raise ChartError(first_number, None, "코드 블록을 닫으세요. / Close the code block.")
        lines = lines[1:-1]
    bars = []
    section = None
    section_line = 0
    for line_number, line in lines:
        if line.startswith("["):
            header = re.match(r"\[([^\[\]]*)\](.*)", line)
            if header is None or section is not None:
                raise ChartError(line_number, None, "섹션 뒤에 마디를 넣으세요. / Add bars after each section label.")
            section, line = header[1], header[2].strip()
            section_line = line_number
            if not line:
                continue
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        for token in line.split("|"):
            number = len(bars) + 1
            if number > MAX_BARS:
                raise ChartError(line_number, number, f"최대 {MAX_BARS}마디 / Maximum {MAX_BARS} bars.")
            try:
                bars.append(_parse_bar(token, section))
            except ValueError as error:
                raise ChartError(line_number, number, str(error)) from error
            section = None
    if section is not None:
        raise ChartError(section_line, None, "섹션에 마디가 없습니다. / This section has no bars.")
    result = tuple(bars)
    _validate_bars(result)
    return result


def format_chart(bars: tuple[Bar, ...]) -> str:
    """Format valid chart text while preserving every bar's timing and section."""
    _validate_bars(bars)
    lines = []
    row = []
    for bar in bars:
        if bar.section is not None:
            if row:
                lines.append("| " + " | ".join(row) + " |")
                row.clear()
            lines.append(f"[{bar.section}]")
        if bar.beats == _DEFAULT_BEATS[len(bar.chords)]:
            row.append(" ".join(bar.chords))
        else:
            row.append(" ".join(f"{symbol}:{beats}" for symbol, beats in zip(bar.chords, bar.beats)))
        if len(row) == 4:
            lines.append("| " + " | ".join(row) + " |")
            row.clear()
    if row:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def transpose_chart(bars: tuple[Bar, ...], semitones: int, prefer_flats: bool = False) -> tuple[Bar, ...]:
    """Transpose harmonic roots and slash bass independently, retaining chord quality."""
    _validate_bars(bars)
    if type(semitones) is not int:
        raise ValueError("이조는 정수 반음으로 지정하세요. / Transpose by whole semitones.")
    if semitones % 12 == 0:
        return bars
    notes = _FLATS if prefer_flats else _SHARPS
    result = []
    for bar in bars:
        moved = []
        for symbol in bar.chords:
            if symbol in ("-", "?"):
                moved.append(symbol)
                continue
            parsed = parse_symbol(symbol)
            suffix = CHORD_SUFFIX[parsed["chord_type"]].replace("♭", "b").replace("♯", "#")
            chord = notes[(parsed["root_pc"] + semitones) % 12] + suffix
            if parsed["bass_pc"] is not None:
                chord += "/" + notes[(parsed["bass_pc"] + semitones) % 12]
            moved.append(chord)
        result.append(Bar(bar.section, tuple(moved), bar.beats))
    return tuple(result)


def transpose_key(key: str, semitones: int) -> str:
    """Shift a known key label while keeping the major or minor mode."""
    key = normalize_key(key)
    if type(semitones) is not int:
        raise ValueError("이조는 정수 반음으로 지정하세요. / Transpose by whole semitones.")
    if not key or semitones % 12 == 0:
        return key
    tonic, quality = key.split()
    notes = _FLATS if tonic.endswith("b") or tonic == "F" else _SHARPS
    pc = parse_symbol(tonic)["root_pc"]
    return f"{notes[(pc + semitones) % 12]} {quality}"


def build_prompt(title: str, key: str, language: str = "ko") -> str:
    """Create a local, provider-independent request for a draft chart."""
    title = _plain_text(title, 160, "Title")
    if not title:
        raise ValueError("곡 제목을 입력하세요. / Enter a song title.")
    key = normalize_key(key)
    subject = json.dumps({"title": title, "key": key or None}, ensure_ascii=False)
    if language == "en":
        return (
            f"Suggest a 4/4 practice chord chart for this song: {subject}\n"
            "If the key is null, use the original key if you know it. Use ? for uncertain chords; do not guess.\n"
            "Return only chords with pipe-separated bars. Put optional section labels like [Verse] at the start of a line.\n"
            "One to four symbols per bar, e.g. | C | Am7 D7 | Gsus4 G C/E | - |. Use - for rests.\n"
            "Default beat lengths are 4, 2+2, 2+1+1, or 1+1+1+1. For other divisions, put whole beats after every chord "
            "in the bar (e.g. | C:1 F:3 |). Use up to 128 bars. Omit lyrics, melody, explanations and song metadata."
        )
    return (
        f"다음 곡의 4/4 연습용 코드표 초안을 만들어 주세요: {subject}\n"
        "키가 null이면 알고 있는 경우 원곡 키를 사용하세요. 미확정 코드는 ?로 두고 추측하지 마세요.\n"
        "코드표만 출력하고 마디는 |로 나누세요. 섹션은 필요할 때 줄 시작에 [Verse]처럼 적으세요.\n"
        "한 마디에 기호 1–4개를 사용하세요. 예: | C | Am7 D7 | Gsus4 G C/E | - |. 쉼표는 -입니다.\n"
        "기본 박자는 4, 2+2, 2+1+1, 1+1+1+1입니다. 다르게 나누려면 마디 안 모든 코드에 정수 박자를 "
        "붙이세요(예: | C:1 F:3 |). 최대 128마디로, 가사·멜로디·설명·곡 정보는 제외하세요."
    )


def save_project(project: PracticeProject, path: str | Path) -> None:
    """Atomically save the chart and arrangement settings as UTF-8 JSON."""
    if not isinstance(project, PracticeProject):
        raise ValueError("Invalid practice project")
    target = Path(path)
    payload = {"schema": _SCHEMA, "chart": format_chart(project.bars),
               "title": project.title, "key": project.key, "bpm": project.bpm,
               "style": project.style, "count_in": project.count_in, "loop": project.loop}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".practice-", suffix=".json",
                                         delete=False, mode="w", encoding="utf-8", newline="\n") as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _unique_fields(pairs: list[tuple[str, object]]) -> dict:
    payload = dict(pairs)
    if len(payload) != len(pairs):
        raise ValueError("Duplicate JSON fields")
    return payload


def load_project(path: str | Path) -> PracticeProject:
    """Return a wholly validated project, leaving existing app state to the caller."""
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_PROJECT_BYTES + 1)
    if len(raw) > MAX_PROJECT_BYTES:
        raise ValueError("연습 프로젝트가 너무 큽니다. / Practice project is too large.")
    try:
        payload = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_fields)
    except (ValueError, RecursionError) as error:
        raise ValueError("올바른 연습 프로젝트 JSON이 아닙니다. / Invalid practice project JSON.") from error
    fields = ("title", "key", "bpm", "style", "count_in", "loop")
    if (not isinstance(payload, dict) or set(payload) != {"schema", "chart", *fields}
            or payload["schema"] != _SCHEMA):
        raise ValueError("지원하지 않는 연습 프로젝트입니다. / Unsupported practice project format.")
    return PracticeProject(parse_chart(payload["chart"]), **{field: payload[field] for field in fields})
