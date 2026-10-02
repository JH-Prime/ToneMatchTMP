"""분석 결과와 구분되는 코드·스케일·다이어토닉 건반 참고 자료를 만든다.

코드의 음고 집합은 실제 보이싱 엔진과 공유하지만 참고표의 옥타브 배치는
이론적인 기본 배치일 뿐, 음원에서 검출한 운지나 자동 조성 판정이 아니다.
"""

from __future__ import annotations

import re

from voicing import CHORD_INTERVALS, CHORD_SUFFIX, NOTE_NAMES


ROOT_NAMES = NOTE_NAMES
REFERENCE_SOURCES = (
    "https://musictheory.pugetsound.edu/mt21c/MinorScales.html",
    "https://musictheory.pugetsound.edu/mt21c/RomanNumeralsOfDiatonicSeventhChords.html",
    "https://musictheory.pugetsound.edu/mt21c/JazzScales.html",
    "https://hub.yamaha.com/guitars/g-how-to/a-guitarists-guide-to-major-and-minor-pentatonic-scales/",
)

# 차트의 도수는 확장음을 상위 옥타브에 배치하고 이명동음 철자를 보존한다.
CHORD_DEGREES = {
    "power5": ("1", "5"),
    "major": ("1", "3", "5"),
    "minor": ("1", "♭3", "5"),
    "sus2": ("1", "2", "5"),
    "sus4": ("1", "4", "5"),
    "dim": ("1", "♭3", "♭5"),
    "7": ("1", "3", "5", "♭7"),
    "maj7": ("1", "3", "5", "7"),
    "min7": ("1", "♭3", "5", "♭7"),
    "6": ("1", "3", "5", "6"),
    "min6": ("1", "♭3", "5", "6"),
    "min7b5": ("1", "♭3", "♭5", "♭7"),
    "dim7": ("1", "♭3", "♭5", "♭♭7"),
    "aug": ("1", "3", "♯5"),
    "add9": ("1", "3", "5", "9"),
    "minadd9": ("1", "♭3", "5", "9"),
    "9": ("1", "3", "5", "♭7", "9"),
    "maj9": ("1", "3", "5", "7", "9"),
    "min9": ("1", "♭3", "5", "♭7", "9"),
    "7sus4": ("1", "4", "5", "♭7"),
    "7sus2": ("1", "2", "5", "♭7"),
    "11": ("1", "3", "5", "♭7", "9", "11"),
    "maj11": ("1", "3", "5", "7", "9", "11"),
    "min11": ("1", "♭3", "5", "♭7", "9", "11"),
    "13": ("1", "3", "5", "♭7", "9", "11", "13"),
    "maj13": ("1", "3", "5", "7", "9", "11", "13"),
    "min13": ("1", "♭3", "5", "♭7", "9", "11", "13"),
    "minmaj7": ("1", "♭3", "5", "7"),
    "minmaj9": ("1", "♭3", "5", "7", "9"),
    "6add9": ("1", "3", "5", "6", "9"),
    "min6add9": ("1", "♭3", "5", "6", "9"),
    "7b5": ("1", "3", "♭5", "♭7"),
    "7sharp5": ("1", "3", "♯5", "♭7"),
    "7b9": ("1", "3", "5", "♭7", "♭9"),
    "7sharp9": ("1", "3", "5", "♭7", "♯9"),
    "7sharp11": ("1", "3", "5", "♭7", "♯11"),
    "7b13": ("1", "3", "5", "♭7", "♭13"),
    "maj7sharp5": ("1", "3", "♯5", "7"),
    "maj7sharp11": ("1", "3", "5", "7", "♯11"),
    "add11": ("1", "3", "5", "11"),
    "minadd11": ("1", "♭3", "5", "11"),
}
CHORD_NAMES = {
    "power5": ("파워 코드 · 5", "Power chord · 5"),
    "major": ("메이저 · 장3화음", "Major triad"),
    "minor": ("마이너 · 단3화음", "Minor triad"),
    "sus2": ("서스펜디드 2 · sus2", "Suspended 2 · sus2"),
    "sus4": ("서스펜디드 4 · sus4", "Suspended 4 · sus4"),
    "dim": ("디미니시드 · 감3화음", "Diminished triad"),
    "7": ("도미넌트 7", "Dominant 7th"),
    "maj7": ("메이저 7", "Major 7th"),
    "min7": ("마이너 7", "Minor 7th"),
    "6": ("메이저 6", "Major 6th"),
    "min6": ("마이너 6", "Minor 6th"),
    "min7b5": ("마이너 7 ♭5 · 하프 디미니시드", "Minor 7 ♭5 · Half-diminished"),
    "dim7": ("디미니시드 7 · 감7화음", "Diminished 7th"),
    "aug": ("어그멘티드 · 증3화음", "Augmented triad"),
    "add9": ("메이저 add9", "Major add9"),
    "minadd9": ("마이너 add9", "Minor add9"),
    "9": ("도미넌트 9", "Dominant 9th"),
    "maj9": ("메이저 9", "Major 9th"),
    "min9": ("마이너 9", "Minor 9th"),
    "7sus4": ("7 서스펜디드 4 · 7sus4", "7 suspended 4 · 7sus4"),
    "7sus2": ("7 서스펜디드 2 · 7sus2", "7 suspended 2 · 7sus2"),
    "11": ("도미넌트 11", "Dominant 11th"),
    "maj11": ("메이저 11", "Major 11th"),
    "min11": ("마이너 11", "Minor 11th"),
    "13": ("도미넌트 13", "Dominant 13th"),
    "maj13": ("메이저 13", "Major 13th"),
    "min13": ("마이너 13", "Minor 13th"),
    "minmaj7": ("마이너 메이저 7", "Minor-major 7th"),
    "minmaj9": ("마이너 메이저 9", "Minor-major 9th"),
    "6add9": ("메이저 6/9", "Major 6/9"),
    "min6add9": ("마이너 6/9", "Minor 6/9"),
    "7b5": ("도미넌트 7 ♭5", "Dominant 7 ♭5"),
    "7sharp5": ("도미넌트 7 ♯5", "Dominant 7 ♯5"),
    "7b9": ("도미넌트 7 ♭9", "Dominant 7 ♭9"),
    "7sharp9": ("도미넌트 7 ♯9", "Dominant 7 ♯9"),
    "7sharp11": ("도미넌트 7 ♯11", "Dominant 7 ♯11"),
    "7b13": ("도미넌트 7 ♭13", "Dominant 7 ♭13"),
    "maj7sharp5": ("메이저 7 ♯5", "Major 7 ♯5"),
    "maj7sharp11": ("메이저 7 ♯11", "Major 7 ♯11"),
    "add11": ("메이저 add11", "Major add11"),
    "minadd11": ("마이너 add11", "Minor add11"),
}
SCALE_DEGREES = {
    "major": ("1", "2", "3", "4", "5", "6", "7"),
    "natural_minor": ("1", "2", "♭3", "4", "5", "♭6", "♭7"),
    "major_pentatonic": ("1", "2", "3", "5", "6"),
    "minor_pentatonic": ("1", "♭3", "4", "5", "♭7"),
    "harmonic_minor": ("1", "2", "♭3", "4", "5", "♭6", "7"),
    "melodic_minor": ("1", "2", "♭3", "4", "5", "6", "7"),
    "dorian": ("1", "2", "♭3", "4", "5", "6", "♭7"),
    "phrygian": ("1", "♭2", "♭3", "4", "5", "♭6", "♭7"),
    "lydian": ("1", "2", "3", "♯4", "5", "6", "7"),
    "mixolydian": ("1", "2", "3", "4", "5", "6", "♭7"),
    "locrian": ("1", "♭2", "♭3", "4", "♭5", "♭6", "♭7"),
    "minor_blues": ("1", "♭3", "4", "♭5", "5", "♭7"),
}
SCALE_NAMES = {
    "major": ("메이저 · 아이오니안", "Major · Ionian"),
    "natural_minor": ("내추럴 마이너 · 에올리안", "Natural minor · Aeolian"),
    "major_pentatonic": ("메이저 펜타토닉", "Major pentatonic"),
    "minor_pentatonic": ("마이너 펜타토닉", "Minor pentatonic"),
    "harmonic_minor": ("하모닉 마이너", "Harmonic minor"),
    "melodic_minor": ("멜로딕 마이너 · 상행형", "Melodic minor · Ascending"),
    "dorian": ("도리안", "Dorian"),
    "phrygian": ("프리지안", "Phrygian"),
    "lydian": ("리디안", "Lydian"),
    "mixolydian": ("믹솔리디안", "Mixolydian"),
    "locrian": ("로크리안", "Locrian"),
    "minor_blues": ("마이너 블루스 · 6음", "Minor blues · Six-note"),
}
_DIATONIC_QUALITIES = {
    "major": (
        ("I", "major", "maj7", "Imaj7"),
        ("ii", "minor", "min7", "ii7"),
        ("iii", "minor", "min7", "iii7"),
        ("IV", "major", "maj7", "IVmaj7"),
        ("V", "major", "7", "V7"),
        ("vi", "minor", "min7", "vi7"),
        ("vii°", "dim", "min7b5", "viiø7"),
    ),
    "natural_minor": (
        ("i", "minor", "min7", "i7"),
        ("ii°", "dim", "min7b5", "iiø7"),
        ("III", "major", "maj7", "IIImaj7"),
        ("iv", "minor", "min7", "iv7"),
        ("v", "minor", "min7", "v7"),
        ("VI", "major", "maj7", "VImaj7"),
        ("VII", "major", "7", "VII7"),
    ),
}
_NATURAL_PITCHES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_LETTERS = "CDEFGAB"
_MAJOR_STEPS = (0, 2, 4, 5, 7, 9, 11)


def _localized(pair: tuple[str, str], language: str) -> str:
    """언어 코드에 맞는 한국어 또는 영어 참고표 문구를 선택한다."""
    return pair[1] if str(language).lower().startswith("en") else pair[0]


def _root_index(root_pc: int) -> int:
    """잘못된 근음이 다른 음으로 조용히 바뀌지 않도록 0부터 11만 허용한다."""
    if isinstance(root_pc, bool) or not isinstance(root_pc, int) or not 0 <= root_pc < 12:
        raise ValueError("root_pc must be an integer from 0 to 11")
    return root_pc


def _degree_parts(degree: str) -> tuple[int, int]:
    """임시표가 붙은 도수 표기를 음정 번호와 반음 변화량으로 나눈다."""
    match = re.fullmatch(r"([♭♯]*)([1-9][0-9]*)", degree)
    if match is None:
        raise ValueError(f"Invalid scale degree: {degree}")
    accidentals, number = match.groups()
    return int(number), accidentals.count("♯") - accidentals.count("♭")


def _degree_interval(degree: str) -> int:
    """도수를 근음 기준 반음 간격으로 바꾸되 9·11·13의 옥타브를 유지한다."""
    number, adjustment = _degree_parts(degree)
    octave, step = divmod(number - 1, 7)
    return 12 * octave + _MAJOR_STEPS[step] + adjustment


def _spelled_note(root_name: str, root_pc: int, degree: str) -> str:
    """도수의 음이름 글자를 유지하여 E♯·C♭·겹내림표까지 올바르게 표기한다."""
    number, _ = _degree_parts(degree)
    letter = _LETTERS[(_LETTERS.index(root_name[0]) + number - 1) % 7]
    target_pc = (root_pc + _degree_interval(degree)) % 12
    adjustment = (target_pc - _NATURAL_PITCHES[letter] + 6) % 12 - 6
    accidental = "♯" * adjustment if adjustment > 0 else "♭" * -adjustment
    return letter + accidental


def _reference_limits(language: str) -> list[str]:
    """이론 참고표와 오디오 검출·실제 운지의 차이를 분명하게 알린다."""
    return [
        _localized((
            "이 표는 음악 이론 참고 자료입니다. 현재 음원의 코드·스케일 검출 결과가 아닙니다.",
            "This is a music-theory reference, not a detected chord or scale from the current audio.",
        ), language),
        _localized((
            "건반은 12평균율의 기본 배치 예시입니다. 실제 연주의 옥타브·역위·생략음·기타 운지는 다를 수 있습니다.",
            "Keys show a basic 12-tone equal-tempered layout. Played octaves, inversions, omitted tones and guitar fingerings may differ.",
        ), language),
        _localized((
            "E♯와 F처럼 같은 건반이어도 도수에 따라 음이름이 달라집니다. 9·11·13도는 상위 옥타브로 표시합니다.",
            "Enharmonic names such as E♯ and F share a key but preserve the degree spelling. 9ths, 11ths and 13ths appear in the upper octave.",
        ), language),
    ]


def chord_options(language: str = "ko") -> list[dict]:
    """오디오 엔진과 동일한 코드 유형 목록을 표시 언어에 맞춰 반환한다."""
    return [{"key": key, "name": _localized(CHORD_NAMES[key], language)} for key in CHORD_INTERVALS]


def scale_options(language: str = "ko") -> list[dict]:
    """코드 유형과 별개인 음계·모드 참고 목록을 반환한다."""
    return [{"key": key, "name": _localized(SCALE_NAMES[key], language)} for key in SCALE_DEGREES]


def diatonic_options(language: str = "ko") -> list[dict]:
    """다이어토닉 화음을 쌓을 수 있는 장음계와 자연단음계 선택지를 반환한다."""
    return [{"key": key, "name": _localized(SCALE_NAMES[key], language)} for key in _DIATONIC_QUALITIES]


def _chord_reference(root_pc: int, chord_type: str, language: str, root_name: str) -> dict:
    """주어진 철자의 근음에서 엔진과 같은 구성음을 가진 이론 코드 자료를 만든다."""
    degrees = CHORD_DEGREES[chord_type]
    intervals = [_degree_interval(degree) for degree in degrees]
    if tuple(interval % 12 for interval in intervals) != tuple(CHORD_INTERVALS[chord_type]):
        raise ValueError(f"Chord reference does not match audio engine: {chord_type}")
    return {
        "kind": "chord", "key": chord_type, "chord_type": chord_type,
        "name": _localized(CHORD_NAMES[chord_type], language),
        "root_pc": root_pc, "root_name": root_name,
        "symbol": root_name + CHORD_SUFFIX[chord_type],
        "intervals": intervals,
        "pitch_classes": [(root_pc + interval) % 12 for interval in intervals],
        "note_names": [_spelled_note(root_name, root_pc, degree) for degree in degrees],
        "degree_labels": list(degrees),
        "explanation": _localized((
            "선택한 코드의 이론적 구성음입니다. 확장 코드는 전체 구성음을 표시하며 실제 연주에서는 일부를 생략할 수 있습니다.",
            "Theoretical tones of the selected chord. Extended chords show the complete formula; some tones may be omitted in performance.",
        ), language),
        "limitations": _reference_limits(language),
    }


def get_chord_reference(root_pc: int, chord_type: str, language: str = "ko") -> dict:
    """12개 근음 중 선택한 코드의 기호·도수·음이름·건반 간격을 반환한다."""
    root_pc = _root_index(root_pc)
    return _chord_reference(root_pc, chord_type, language, ROOT_NAMES[root_pc])


def get_scale_reference(root_pc: int, scale_key: str, language: str = "ko") -> dict:
    """스케일의 이론적 음렬을 반환하며 음원의 조성이나 코드로 판정하지 않는다."""
    root_pc = _root_index(root_pc)
    degrees = SCALE_DEGREES[scale_key]
    intervals = [_degree_interval(degree) for degree in degrees]
    root_name = ROOT_NAMES[root_pc]
    name = _localized(SCALE_NAMES[scale_key], language)
    explanation = _localized((
        "스케일은 음계이며 코드 종류와 구분됩니다. 표시 음렬은 한 옥타브이며 끝의 중복 근음은 생략했습니다.",
        "A scale is a collection of notes, not a chord quality. One octave is shown without repeating the tonic at the end.",
    ), language)
    if scale_key == "melodic_minor":
        explanation += " " + _localized((
            "멜로딕 마이너는 상행형입니다. 고전적 하행형은 자연단음계와 같습니다.",
            "Melodic minor uses the ascending form. Its classical descending form matches natural minor.",
        ), language)
    return {
        "kind": "scale", "key": scale_key, "name": name,
        "root_pc": root_pc, "root_name": root_name, "symbol": f"{root_name} {name}",
        "intervals": intervals,
        "pitch_classes": [(root_pc + interval) % 12 for interval in intervals],
        "note_names": [_spelled_note(root_name, root_pc, degree) for degree in degrees],
        "degree_labels": list(degrees), "explanation": explanation,
        "limitations": _reference_limits(language),
    }


def get_diatonic_reference(root_pc: int, scale_key: str = "major", language: str = "ko") -> dict:
    """장음계 또는 자연단음계의 각 도수에 쌓은 3화음과 7화음을 반환한다."""
    root_pc = _root_index(root_pc)
    qualities = _DIATONIC_QUALITIES[scale_key]
    scale = get_scale_reference(root_pc, scale_key, language)
    rows = []
    for index, (degree_label, triad_type, seventh_type, seventh_label) in enumerate(qualities):
        chord_root = scale["pitch_classes"][index]
        chord_root_name = scale["note_names"][index]
        triad = _chord_reference(chord_root, triad_type, language, chord_root_name)
        seventh = _chord_reference(chord_root, seventh_type, language, chord_root_name)
        triad["degree_label"] = degree_label
        seventh["degree_label"] = seventh_label
        rows.append({
            "degree": index + 1, "degree_label": degree_label,
            "seventh_degree_label": seventh_label,
            "root_pc": chord_root, "root_name": chord_root_name,
            "triad": triad, "seventh": seventh,
        })
    explanation = _localized((
        "다이어토닉은 별도의 코드 종류가 아니라 선택한 음계의 음만으로 쌓은 화음 관계입니다. 각 도수의 3화음과 7화음을 함께 표시합니다.",
        "Diatonic describes chords built from the selected scale, not a separate chord quality. Each scale degree shows both a triad and a seventh chord.",
    ), language)
    if scale_key == "natural_minor":
        explanation += " " + _localized((
            "자연단음계만 사용합니다. 단조에서 자주 쓰는 장3화음 V 등 화성·가락단음계의 변화음은 포함하지 않습니다.",
            "Natural minor only: raised notes from harmonic or melodic minor, including the commonly used major V chord, are not included.",
        ), language)
    return {
        "kind": "diatonic", "key": scale_key, "name": scale["name"],
        "root_pc": root_pc, "root_name": scale["root_name"], "symbol": scale["symbol"],
        "intervals": list(scale["intervals"]), "pitch_classes": list(scale["pitch_classes"]),
        "note_names": list(scale["note_names"]), "degree_labels": list(scale["degree_labels"]),
        "explanation": explanation, "limitations": _reference_limits(language), "rows": rows,
    }
