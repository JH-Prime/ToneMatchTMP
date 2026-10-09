"""원본 분석과 분리된 코드 수정 지도 및 제한된 분석 JSON 재열기."""

from copy import deepcopy
import json
import math
from pathlib import Path
import re

from chord_chart import build_chord_chart, initial_chart_settings
from catalog import APP_VERSION, TARGET_FIRMWARE, MODEL_GUIDE_REVISION
from voicing import CHORD_INTERVALS, CHORD_SUFFIX


MAX_RESULT_BYTES = 8 * 1024 * 1024
MAX_EDIT_EVENTS = 10_000
_NOTES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
_SUFFIX_TYPES = {CHORD_SUFFIX[key].replace('♭', 'b').replace('♯', '#'): key for key in CHORD_INTERVALS}


def _note_pc(note):
    """검증된 음이름의 임시표를 반영해 pitch class로 바꾼다."""
    return (_NOTES[note[0]] + (1 if note.endswith('#') else -1 if note.endswith('b') else 0)) % 12


def parse_symbol(symbol):
    """지원 코드 문법만 허용하며 6/9와 마지막 베이스 음표를 구분한다."""
    if not isinstance(symbol, str) or not 1 <= len(symbol.strip()) <= 32:
        raise ValueError('Invalid chord symbol / 코드 기호를 확인하세요.')
    symbol = symbol.strip().replace('♭', 'b').replace('♯', '#')
    if symbol == '?':
        return {'symbol': '?', 'chord_type': 'unknown', 'root_pc': None, 'bass_pc': None, 'pitch_classes': []}
    match = re.fullmatch(r'([A-G][#b]?)(.*?)(?:/([A-G][#b]?))?', symbol)
    if not match or match[2] not in _SUFFIX_TYPES:
        raise ValueError('Unsupported chord symbol / 지원하지 않는 코드 기호입니다.')
    root, suffix, bass = match.groups()
    chord_type = _SUFFIX_TYPES[suffix]
    root_pc = _note_pc(root)
    return {'symbol': symbol, 'chord_type': chord_type, 'root_pc': root_pc,
            'bass_pc': _note_pc(bass) if bass else None,
            'pitch_classes': [(root_pc + interval) % 12 for interval in CHORD_INTERVALS[chord_type]]}


def _validated_corrections(result):
    """수정 지도는 기존 이벤트 범위의 정규화된 문자열 키만 받는다."""
    events = result.get('chord_voicing', {}).get('events', [])
    corrections = result.get('chord_corrections', {})
    if not isinstance(events, list) or len(events) > MAX_EDIT_EVENTS or not isinstance(corrections, dict):
        raise ValueError('Invalid chord corrections')
    normalized = {}
    for key, value in corrections.items():
        if not isinstance(key, str) or not re.fullmatch(r'0|[1-9][0-9]{0,4}', key) or int(key) >= len(events):
            raise ValueError('Correction index outside analysis')
        normalized[key] = parse_symbol(value)['symbol']
    return normalized


def set_correction(result, event_index, symbol):
    """새 결과 사본에만 수정·복원을 적용하여 검증 실패의 부분 변경을 막는다."""
    corrections = _validated_corrections(result)
    events = result.get('chord_voicing', {}).get('events', [])
    if type(event_index) is not int or not 0 <= event_index < len(events):
        raise ValueError('Correction index outside analysis')
    if symbol is None:
        corrections.pop(str(event_index), None)
    else:
        corrections[str(event_index)] = parse_symbol(symbol)['symbol']
    return {**result, 'chord_corrections': corrections}


def effective_voicing(result):
    """표시용 수정 이벤트를 만들고 자동 분석의 근거·신뢰도는 원본에 남긴다."""
    corrections = _validated_corrections(result)
    analysis = deepcopy(result.get('chord_voicing', {}))
    for key, symbol in corrections.items():
        index = int(key)
        original = analysis['events'][index]
        parsed = parse_symbol(symbol)
        analysis['events'][index] = {
            'start_seconds': original['start_seconds'], 'end_seconds': original['end_seconds'],
            **parsed, 'confidence': None, 'candidate_shapes': [], 'manual_edit': True,
            'original_symbol': original.get('symbol', '?'), 'register': 'unknown',
            'spacing': 'unknown', 'inversion': 'unknown',
        }
    return analysis


def _validate_tree(value, depth=0):
    """작은 로컬 JSON만 허용하고 비유한 숫자·과도한 깊이와 컬렉션을 거부한다."""
    if depth > 24:
        raise ValueError('Analysis JSON is too deeply nested')
    if isinstance(value, dict):
        if len(value) > MAX_EDIT_EVENTS:
            raise ValueError('Analysis object is too large')
        for key, child in value.items():
            if len(key) > 128:
                raise ValueError('Analysis key is too long')
            _validate_tree(child, depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_EDIT_EVENTS:
            raise ValueError('Analysis list is too large')
        for child in value:
            _validate_tree(child, depth + 1)
    elif isinstance(value, str) and len(value) > 4096:
        raise ValueError('Analysis string is too long')
    elif isinstance(value, (int, float)) and (not math.isfinite(value) or abs(value) > 1e12):
        raise ValueError('Analysis number is invalid')


def load_result(path, language='ko'):
    """검증된 분석 JSON만 다시 열고 파일 경로·명령·임의 재생 요청은 가져오지 않는다."""
    from engine import ToneFeatures, TEMPLATES, relocalize_result

    try:
        with Path(path).open('rb') as stream:
            payload = stream.read(MAX_RESULT_BYTES + 1)
        if len(payload) > MAX_RESULT_BYTES:
            raise ValueError('Analysis file exceeds 8 MiB')
        incoming = json.loads(payload)
        _validate_tree(incoming)
        if not isinstance(incoming, dict):
            raise ValueError('Analysis must be an object')
        kind = incoming.get('analysis_kind', 'tone')
        if kind not in {'tone', 'chords'}:
            raise ValueError('Invalid analysis purpose')
        chord_only = kind == 'chords'
        features = incoming['features']
        if not isinstance(features, dict) or (chord_only and features):
            raise ValueError('Invalid chord-only features')
        if not chord_only:
            ToneFeatures(**features)
        if not all(type(value) in (int, float) for value in features.values()):
            raise ValueError('Invalid analysis features')
        source = incoming['source']
        start, duration = float(source.get('start_seconds', 0)), float(source['duration_seconds'])
        if not math.isfinite(start + duration) or start < 0 or not 0 < duration <= 1200.1:
            raise ValueError('Invalid analysis range')
        recipes = incoming['recipes']
        templates = {item['id'] for item in TEMPLATES}
        if incoming.get('device_id') == 'quad_cortex':
            from quad_cortex import STARTING_POINTS
            templates = {f'qc_{index}' for index in range(len(STARTING_POINTS))}
        if not isinstance(recipes, list) or (len(recipes) != 0 if chord_only else not 1 <= len(recipes) <= 3):
            raise ValueError('Invalid recipes')
        for recipe in recipes:
            if recipe['template_id'] not in templates or not 0 <= float(recipe['match_percent']) <= 100:
                raise ValueError('Invalid recipe template or score')
        analysis = incoming.get('chord_voicing', {})
        result = {key: incoming[key] for key in ('features', 'input_profile', 'recipes', 'chord_voicing',
                  'chord_corrections', 'chord_chart_settings', 'device_id', 'app_version') if key in incoming}
        result['analysis_kind'] = kind
        result['source'] = {'file_name': Path(str(source.get('file_name', 'analysis'))).name,
                            'start_seconds': start, 'end_seconds': start + duration, 'duration_seconds': duration}
        separation = incoming.get('source_separation', {'used': analysis.get('analysis_source') == 'guitar_stem'})
        if not isinstance(separation, dict) or type(separation.get('used', False)) is not bool:
            raise ValueError('Invalid tone separation metadata')
        result['source_separation'] = {'used': separation.get('used', False)}
        if 'guitar_rms_dbfs' in separation:
            if type(separation['guitar_rms_dbfs']) not in (int, float):
                raise ValueError('Invalid tone level')
            result['source_separation']['guitar_rms_dbfs'] = separation['guitar_rms_dbfs']
        for key, default in (('app_version', APP_VERSION), ('target_firmware', TARGET_FIRMWARE), ('model_guide', MODEL_GUIDE_REVISION)):
            value = incoming.get(key, default)
            if not isinstance(value, str):
                raise ValueError('Invalid report metadata')
            result[key] = value
        result['chord_corrections'] = _validated_corrections(result)
        for name in ('diagnostics', 'fallback'):
            metadata = analysis.get(name, {})
            if not isinstance(metadata, dict):
                raise ValueError('Invalid chord metadata')
            for key in ('input_rms_dbfs', 'primary_input_rms_dbfs'):
                if key in metadata and type(metadata[key]) not in (int, float):
                    raise ValueError('Invalid chord level')
        for event in analysis.get('events', []):
            if not isinstance(event.get('symbol', '?'), str) or len(event.get('symbol', '?')) > 32 or event.get('chord_type') not in (*CHORD_INTERVALS, 'unknown'):
                raise ValueError('Invalid chord event')
            if not 0 <= float(event['start_seconds']) < float(event['end_seconds']) <= duration + .01:
                raise ValueError('Chord time outside source range')
            for key in ('root_pc', 'bass_pc'):
                value = event.get(key)
                if value is not None and (type(value) is not int or not 0 <= value < 12):
                    raise ValueError('Invalid pitch class')
            score = event.get('confidence')
            if score is not None and type(score) not in (int, float):
                raise ValueError('Invalid evidence score')
            evidence = event.get('evidence') or {}
            if not isinstance(evidence, dict):
                raise ValueError('Invalid chord evidence')
            for values in (event.get('pitch_classes', []), evidence.get('observed_pitch_classes', []),
                           evidence.get('required_pitch_classes', [])):
                if not isinstance(values, list) or len(values) > 12 or any(type(pc) is not int or not 0 <= pc < 12 for pc in values):
                    raise ValueError('Invalid evidence notes')
            for key in ('supported_window_count', 'analyzed_window_count'):
                if key in evidence and (type(evidence[key]) is not int or not 0 <= evidence[key] <= 10000):
                    raise ValueError('Invalid evidence counts')
            alternatives = event.get('alternatives', [])
            if not isinstance(alternatives, list) or len(alternatives) > 3:
                raise ValueError('Invalid chord alternatives')
            for alternative in alternatives:
                if not isinstance(alternative, dict) or not isinstance(alternative.get('symbol'), str) or len(alternative['symbol']) > 32:
                    raise ValueError('Invalid alternative symbol')
            for shape in event.get('candidate_shapes', []):
                frets = shape['frets_low_e_to_high_e']
                if len(frets) != 6 or not all(value in ('x', 'X') or (type(value) is int and 0 <= value <= 36) for value in frets):
                    raise ValueError('Invalid guitar shape')
        settings = initial_chart_settings(result)
        saved = result.get('chord_chart_settings', {})
        if not isinstance(saved, dict):
            raise ValueError('Invalid chart settings')
        settings.update({key: saved[key] for key in ('bpm', 'beats_per_bar', 'first_downbeat_seconds') if key in saved})
        build_chord_chart(effective_voicing(result), **settings)
        return relocalize_result(result, language)
    except (KeyError, TypeError, AttributeError, OverflowError, RecursionError, json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError('Invalid ToneMatch analysis JSON / 올바른 분석 JSON이 아닙니다.') from exc
