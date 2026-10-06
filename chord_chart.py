"""추정 코드의 실제 시간을 보존하며 수동 등간격 마디 차트를 구성한다.

이 모듈은 박자나 첫 강박을 검출하지 않는다. BPM·박자·첫 마디 위치는 표시용
격자이며, 분석 구간 기준 시간과 원본 파일 기준 시간을 별도로 유지한다.
"""

from __future__ import annotations

from copy import deepcopy
import math


MAX_BARS = 10_000
MAX_SEGMENTS = 100_000
_EPSILON = 1e-9


def _finite_number(value: object, name: str) -> float:
    """유한한 실수만 허용하고 잘못된 표시 설정을 명확한 오류로 알린다."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def _integer_setting(value: object, name: str, minimum: int, maximum: int) -> int:
    """정수 설정의 범위를 검사해 과도한 마디 또는 페이지 할당을 방지한다."""
    number = _finite_number(value, name)
    if number != int(number) or not minimum <= number <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
    return int(number)


def _grid_coordinate(seconds: float, first_downbeat: float, seconds_per_bar: float) -> float:
    """부동소수점 오차로 정확한 마디 경계에 빈 마디가 생기지 않게 한다."""
    coordinate = (seconds - first_downbeat) / seconds_per_bar
    nearest = round(coordinate)
    return float(nearest) if abs(coordinate - nearest) < _EPSILON else coordinate


def initial_chart_settings(result: dict) -> dict:
    """분석 결과의 기존 BPM을 표시 초깃값으로 쓰되 검출된 박자로 단정하지 않는다."""
    features = result.get("features", {})
    source = result.get("source", {})
    if not isinstance(features, dict):
        features = {}
    if not isinstance(source, dict):
        source = {}
    try:
        bpm = _finite_number(features.get("bpm"), "bpm")
        if not 20 <= bpm <= 300:
            raise ValueError("bpm outside supported range")
    except ValueError:
        bpm = 120.0
    try:
        duration = _finite_number(source.get("duration_seconds"), "duration_seconds")
        if duration < 0:
            raise ValueError("negative duration")
    except ValueError:
        duration = None
    return {
        "bpm": bpm,
        "beats_per_bar": 4,
        "first_downbeat_seconds": 0.0,
        "page_size": 16,
        "duration_seconds": duration,
    }


def _normalise_events(voicing: dict) -> list[dict]:
    """원래 이벤트 번호와 근거를 유지하며 표시용 시간 구간을 검증한다."""
    raw_events = voicing.get("events", ())
    if not isinstance(raw_events, (list, tuple)):
        raise ValueError("events must be a list or tuple")
    if len(raw_events) > MAX_SEGMENTS:
        raise ValueError(f"chart exceeds {MAX_SEGMENTS} input events")
    events = []
    source_kind = str(voicing.get("analysis_source", "provided_audio"))
    for index, event in enumerate(raw_events):
        if not isinstance(event, dict):
            raise ValueError(f"event {index} must be a dictionary")
        start = _finite_number(event.get("start_seconds"), "event start_seconds")
        end = _finite_number(event.get("end_seconds"), "event end_seconds")
        if start < 0 or end <= start:
            raise ValueError(f"event {index} must have 0 <= start_seconds < end_seconds")
        chord_type = str(event.get("chord_type", "unknown"))
        label = str(event.get("symbol") or "?")
        unknown = chord_type == "unknown" or label == "?"
        events.append({
            "start_seconds": start,
            "end_seconds": end,
            "label": "?" if unknown else label,
            "chord_type": "unknown" if unknown else chord_type,
            "event_index": index,
            "source_kind": source_kind,
            "candidate_shapes": [],
            "unknown": unknown,
            "confidence": deepcopy(event.get("confidence")),
            "root_pc": event.get("root_pc"),
            "manual_edit": bool(event.get('manual_edit')),
        })
    return sorted(events, key=lambda item: (item["start_seconds"], item["end_seconds"], item["event_index"]))


def _unknown_gap(start: float, end: float, source_kind: str) -> dict:
    """미관측 공백을 코드 추정으로 채우지 않고 명시적인 미상 구간으로 만든다."""
    return {
        "start_seconds": start, "end_seconds": end, "label": "?",
        "chord_type": "unknown", "event_index": None, "source_kind": source_kind,
        "candidate_shapes": [], "unknown": True, "confidence": None, "root_pc": None,
    }


def build_chord_chart(
    voicing: dict,
    *,
    bpm: float,
    beats_per_bar: int = 4,
    first_downbeat_seconds: float = 0,
    page_size: int = 16,
    duration_seconds: float | None = None,
) -> dict:
    """원래 코드 시점을 양자화하지 않고 4마디 행과 16마디 페이지로 분할한다."""
    tempo = _finite_number(bpm, "bpm")
    if not 20 <= tempo <= 300:
        raise ValueError("bpm must be between 20 and 300")
    meter = _integer_setting(beats_per_bar, "beats_per_bar", 2, 12)
    page_length = _integer_setting(page_size, "page_size", 1, 16)
    first = _finite_number(first_downbeat_seconds, "first_downbeat_seconds")
    offset = _finite_number(voicing.get("source_start_seconds", 0), "source_start_seconds")
    if offset < 0:
        raise ValueError("source_start_seconds must not be negative")
    supplied_duration = None if duration_seconds is None else _finite_number(duration_seconds, "duration_seconds")
    if supplied_duration is not None and supplied_duration < 0:
        raise ValueError("duration_seconds must not be negative")
    events = _normalise_events(voicing)
    last_event_end = max((event["end_seconds"] for event in events), default=0.0)
    duration = max(supplied_duration or 0.0, last_event_end)
    seconds_per_beat = 60.0 / tempo
    seconds_per_bar = seconds_per_beat * meter
    if duration / seconds_per_bar > MAX_BARS:
        raise ValueError(f"chart exceeds {MAX_BARS} bars")
    if abs(first / seconds_per_bar) > MAX_BARS:
        raise ValueError("first_downbeat_seconds is too far from the analysis segment")
    first_index = math.floor(_grid_coordinate(0, first, seconds_per_bar))
    last_index = math.ceil(_grid_coordinate(duration, first, seconds_per_bar)) - 1
    bar_count = max(0, last_index - first_index + 1) if duration > 0 else 0
    if bar_count > MAX_BARS:
        raise ValueError(f"chart exceeds {MAX_BARS} bars")
    diagnostics = deepcopy(voicing.get("diagnostics", {}))
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    diagnostics.update({
        "events_truncated": bool(diagnostics.get("events_truncated", False)),
        "event_count_before_limit": diagnostics.get("event_count_before_limit", len(events)),
        "chart_input_event_count": len(events),
        "duration_extended_for_events": supplied_duration is not None and last_event_end > supplied_duration + _EPSILON,
        "overlapping_events": False,
    })
    chart = {
        "schema": "tonematch-chord-chart-v1", "grid_mode": "manual_constant_tempo",
        "automatic_downbeat": False, "bpm": tempo, "beats_per_bar": meter,
        "first_downbeat_seconds": first, "seconds_per_beat": seconds_per_beat,
        "seconds_per_bar": seconds_per_bar, "duration_seconds": duration,
        "source_start_seconds": offset, "source_kind": str(voicing.get("analysis_source", "provided_audio")),
        "page_size": page_length, "bars_per_row": 4, "bar_count": bar_count,
        "event_count": len(events), "page_count": 0, "segment_count": 0,
        "diagnostics": diagnostics, "pages": [],
    }
    if not bar_count:
        return chart
    bars = []
    for grid_index in range(first_index, last_index + 1):
        grid_start = first + grid_index * seconds_per_bar
        grid_end = first + (grid_index + 1) * seconds_per_bar
        start = max(0.0, grid_start)
        end = min(duration, grid_end)
        bars.append({
            "number": grid_index + 1, "start_seconds": start, "end_seconds": end,
            "absolute_start_seconds": offset + start, "absolute_end_seconds": offset + end,
            "grid_start_seconds": grid_start, "grid_end_seconds": grid_end,
            "is_pickup": grid_index < 0, "is_partial": start > grid_start + _EPSILON or end < grid_end - _EPSILON,
            "segments": [],
        })
    intervals = list(events)
    covered_until = 0.0
    for event in events:
        start = event["start_seconds"]
        if start > covered_until + _EPSILON:
            intervals.append(_unknown_gap(covered_until, start, chart["source_kind"]))
        elif start < covered_until - _EPSILON:
            diagnostics["overlapping_events"] = True
        covered_until = max(covered_until, event["end_seconds"])
    if covered_until < duration - _EPSILON:
        intervals.append(_unknown_gap(covered_until, duration, chart["source_kind"]))
    segment_count = 0
    for interval in intervals:
        event_start = interval["start_seconds"]
        event_end = interval["end_seconds"]
        start_index = max(first_index, math.floor(_grid_coordinate(event_start, first, seconds_per_bar)))
        end_index = min(last_index, math.ceil(_grid_coordinate(event_end, first, seconds_per_bar)) - 1)
        for grid_index in range(start_index, end_index + 1):
            bar = bars[grid_index - first_index]
            start = max(event_start, bar["start_seconds"])
            end = min(event_end, bar["end_seconds"])
            if end <= start:
                continue
            segment_count += 1
            if segment_count > MAX_SEGMENTS:
                raise ValueError(f"chart exceeds {MAX_SEGMENTS} segments")
            segment = deepcopy(interval)
            segment.update({
                "start_seconds": start, "end_seconds": end,
                "absolute_start_seconds": offset + start, "absolute_end_seconds": offset + end,
                "start_beat": 1.0 + (start - bar["grid_start_seconds"]) / seconds_per_beat,
                "end_beat": 1.0 + (end - bar["grid_start_seconds"]) / seconds_per_beat,
                "start_fraction": max(0.0, min(1.0, (start - bar["grid_start_seconds"]) / seconds_per_bar)),
                "end_fraction": max(0.0, min(1.0, (end - bar["grid_start_seconds"]) / seconds_per_bar)),
                "continues_from_previous": event_start < start - _EPSILON,
                "continues_to_next": event_end > end + _EPSILON,
            })
            bar["segments"].append(segment)
    for bar in bars:
        bar["segments"].sort(key=lambda item: (item["start_seconds"], item["event_index"] if item["event_index"] is not None else -1))
    for start in range(0, len(bars), page_length):
        page_bars = bars[start:start + page_length]
        chart["pages"].append({
            "page_index": len(chart["pages"]), "first_bar_number": page_bars[0]["number"],
            "last_bar_number": page_bars[-1]["number"], "bars": page_bars,
            "rows": [page_bars[row:row + 4] for row in range(0, len(page_bars), 4)],
        })
    chart["page_count"] = len(chart["pages"])
    chart["segment_count"] = segment_count
    return chart
