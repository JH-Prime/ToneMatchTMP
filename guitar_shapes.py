"""표준 조율에서 화음 구성음을 빠짐없이 담는 이론상 기타 운지 후보를 찾는다.

실제 연주의 현·프렛이나 손가락 번호를 검출하는 모듈이 아니다. 연속된 네
프렛, 여섯 현, 대략 네 손가락이라는 제한 안에서만 후보를 제시하며, 일곱
구성음의 13화음처럼 모든 음을 담을 수 없는 경우 음을 몰래 생략하지 않는다.
"""

from __future__ import annotations

from functools import lru_cache
from numbers import Integral
from typing import Iterable


STANDARD_TUNING_MIDI = (40, 45, 50, 55, 59, 64)
MAX_FRET = 15
MAX_FRET_SPAN = 3
MAX_FINGERS = 4


def _finger_count(frets: tuple[int, ...]) -> int:
    """낮은 음·개방현·뮤트현을 넘지 않는 바레를 허용해 손가락 수를 근사한다."""
    count = 0
    for fret in sorted({value for value in frets if value > 0}):
        group_has_note = False
        for value in (*frets, -1):
            if value < fret:
                count += int(group_has_note)
                group_has_note = False
            elif value == fret:
                group_has_note = True
    return count


def _shape_rank(frets: tuple[int, ...], root_pc: int) -> tuple:
    """근음 베이스·낮은 위치·적은 손가락·적은 내부 뮤트 순으로 후보를 정렬한다."""
    sounding = [(index, midi + fret) for index, (midi, fret) in
                enumerate(zip(STANDARD_TUNING_MIDI, frets)) if fret >= 0]
    positive = [fret for fret in frets if fret > 0]
    first, last = sounding[0][0], sounding[-1][0]
    internal_mutes = sum(fret < 0 for fret in frets[first:last + 1])
    return (min(midi for _index, midi in sounding) % 12 != root_pc,
            min(positive, default=0), _finger_count(frets), internal_mutes,
            -len(sounding), max(positive, default=0), frets)


@lru_cache(maxsize=512)
def _search_shapes(root_pc: int, pitch_classes: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    """프렛별 가지치기 탐색 결과를 불변 튜플로 캐시해 반복 분석 비용을 줄인다."""
    required_mask = sum(1 << pc for pc in pitch_classes)
    best: list[tuple[tuple, tuple[int, ...]]] = []
    seen: set[tuple[int, ...]] = set()

    for base_fret in range(1, MAX_FRET + 1):
        positions = (0, *range(base_fret, min(MAX_FRET, base_fret + MAX_FRET_SPAN) + 1))
        options = [tuple([(-1, 0)] + [(fret, 1 << ((midi + fret) % 12))
                   for fret in positions if (midi + fret) % 12 in pitch_classes])
                   for midi in STANDARD_TUNING_MIDI]
        available = [0] * 7
        for index in range(5, -1, -1):
            available[index] = available[index + 1]
            for _fret, mask in options[index]:
                available[index] |= mask
        frets: list[int] = []

        def visit(index: int, mask: int, has_base: bool) -> None:
            """남은 현에서 누락된 구성음을 채울 수 있는 조합만 재귀적으로 검사한다."""
            missing = required_mask & ~mask
            if missing.bit_count() > 6 - index or missing & ~available[index]:
                return
            if index == 6:
                candidate = tuple(frets)
                if not has_base and (base_fret != 1 or any(fret > 0 for fret in candidate)):
                    return
                if candidate in seen or _finger_count(candidate) > MAX_FINGERS:
                    return
                seen.add(candidate)
                best.append((_shape_rank(candidate, root_pc), candidate))
                best.sort(key=lambda item: item[0])
                del best[2:]
                return
            for fret, bit in options[index]:
                frets.append(fret)
                visit(index + 1, mask | bit, has_base or fret == base_fret)
                frets.pop()

        visit(0, 0, False)
    return tuple(frets for _rank, frets in best)


def candidate_shapes(root_pc: int | None, chord_type: str, intervals: Iterable[int]) -> tuple[dict, ...]:
    """모든 화음 구성음을 포함하는 운지 후보를 최대 두 개의 독립된 사전으로 돌려준다."""
    if root_pc is None or chord_type == "unknown":
        return ()
    if isinstance(root_pc, bool) or not isinstance(root_pc, Integral) or not 0 <= int(root_pc) < 12:
        raise ValueError("root_pc must be an integer from 0 to 11")
    values = tuple(intervals)
    if any(isinstance(value, bool) or not isinstance(value, Integral) for value in values):
        raise ValueError("intervals must contain integer semitone distances")
    pitch_classes = tuple(sorted({(int(root_pc) + int(value)) % 12 for value in values}))
    if not 2 <= len(pitch_classes) <= 6 or int(root_pc) not in pitch_classes:
        return ()
    result = []
    for index, frets in enumerate(_search_shapes(int(root_pc), pitch_classes), 1):
        positive = [fret for fret in frets if fret > 0]
        sounding = [midi + fret for midi, fret in zip(STANDARD_TUNING_MIDI, frets) if fret >= 0]
        result.append({
            "label": f"Theoretical shape {index}",
            "frets_low_e_to_high_e": ["x" if fret < 0 else fret for fret in frets],
            "detected": False,
            "theoretical": True,
            "base_fret": min(positive, default=1),
            "root_pitch_class": int(root_pc),
            "bass_pitch_class": min(sounding) % 12,
            "pitch_classes": list(pitch_classes),
            "tuning": "EADGBE",
            "completeness": "all_pitch_classes",
            "approximate_finger_count": _finger_count(frets),
        })
    return tuple(result)
