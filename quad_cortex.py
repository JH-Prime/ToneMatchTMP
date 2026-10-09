"""Quad Cortex native starting points and provenance-preserving offline inventory."""
import json
import math
from pathlib import Path
import re
import sys

from i18n import choice_label, tr

TARGET_COROS = '4.1.1'
CATALOG_SOURCE = 'https://neuraldsp.com/device-list'
MODEL_REFERENCE = 'Neural DSP Device List · 2026-10-07'
# These are app heuristics, not measured Neural DSP transfer functions.
# name, amp, cabinet, optional drive, six target features (same order as below).
STARTING_POINTS = (
    ('Studio clean', 'US TWN Normal', '212 US TWN CK2', None, (.10, .62, .48, .22, .20, .05)),
    ('Jazz clean', 'Rols Jazz CH120', '212 Rols Jazz ’87', None, (.08, .70, .36, .18, .28, .10)),
    ('Deluxe edge', 'US DLX 65 Reissue', '112 US DLX SC64', 'Myth Drive', (.28, .55, .48, .34, .24, .06)),
    ('British chime', 'UK C30 TopBoost', '212 UK C30 ’65', None, (.35, .70, .35, .32, .24, .05)),
    ('British crunch', 'Brit 2203', '412 Brit 60B GB 90s', 'Green 808', (.65, .56, .60, .55, .18, .04)),
    ('Modern lead', 'CA Duo Ch3 Modern', '412 CA Stand OS A V30 ’01', 'Green 808', (.88, .50, .70, .75, .30, .04)),
)


def load_catalog():
    """소스·포터블 실행 위치에서 출처가 포함된 공식 목록을 읽는다."""
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    data = json.loads((root / 'resources' / 'quad_cortex_catalog.json').read_text(encoding='utf-8'))
    if data.get('schema') != 'tonematch-qc-catalog/v1' or not data.get('devices'):
        raise ValueError('Invalid Quad Cortex catalog')
    return data


def validate_firmware(value):
    """CorOS 버전 형식을 검사하고 비교 가능한 세 정수로 반환한다."""
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('CorOS must be a released major.minor.patch version')
    return tuple(map(int, value.split('.')))


def eligible_native(row, firmware=TARGET_COROS):
    """해당 펌웨어의 내장 장치만 추천 대상으로 허용한다."""
    version = validate_firmware(firmware)
    return (row['kind'] == 'native' and not row.get('required_plugin')
            and bool(row.get('added_in')) and validate_firmware(row['added_in']) <= version)


def instructions(language):
    """실측하지 않은 노브 값을 꾸미지 않고 수동 적용 안내를 반환한다."""
    if language == 'en':
        return ['Create an empty Quad Cortex preset and connect the listed blocks in order.',
                'Use only blocks available in your CorOS version; these recipes require no plugins.',
                'Start at device defaults. Numerical knob ranges have not been verified; no TMP percentages are transferred.',
                'Match listening levels first, then adjust gain, tonal balance and ambience by ear. No automatic preset transfer.']
    return ['Quad Cortex의 빈 프리셋에 표시된 블록을 순서대로 연결하세요.',
            '선택한 CorOS에서 사용 가능한 내장 모델만 사용합니다. 별도 플러그인은 필요 없습니다.',
            '장비 기본값에서 시작하세요. 개별 노브 범위는 미검증이며 TMP 백분율을 옮겨 쓰지 않습니다.',
            '먼저 청감 음량을 맞춘 뒤 왜곡량·음색·공간감을 조정하세요. 프리셋 자동 전송은 하지 않습니다.']


def recipes(features, output_mode, language='ko', firmware=TARGET_COROS):
    """네이티브 모델과 출력 경로에 맞는 휴리스틱 시작점 세 개를 고른다."""
    if output_mode not in {'frfr', 'power_amp_cab', 'amp_front'}:
        raise ValueError('Unsupported output route')
    rows = {(r['category'], r['name']): r for r in load_catalog()['devices'] if eligible_native(r, firmware)}
    keys = ('saturation', 'brightness', 'body', 'compression', 'ambience', 'modulation')
    weights = (.30, .17, .15, .14, .16, .08)
    ranked = []
    for index, (name, amp, cab, drive, target) in enumerate(STARTING_POINTS):
        desired = []
        if drive:
            desired.append(('Guitar overdrive', drive, 'Stompbox'))
        if output_mode != 'amp_front':
            desired.append(('Guitar amps', amp, 'Amp Head'))
        if output_mode == 'frfr':
            desired.append(('Guitar cabinets', cab, 'Cabinet'))
        delay_omitted = features.ambience > .22 and ('Delay', 'Digital Delay') not in rows
        if features.ambience > .22 and not delay_omitted:
            desired.append(('Delay', 'Digital Delay', 'Delay'))
        desired.append(('Reverb', 'Room', 'Reverb'))
        # Do not offer a template whose reference devices exceed the selected CorOS.
        if any(key not in rows for key in [('Guitar amps', amp), ('Guitar cabinets', cab)]):
            continue
        if any((category, model) not in rows for category, model, _ in desired):
            continue
        distance = sum(w * (getattr(features, k) - t) ** 2 for k, w, t in zip(keys, weights, target))
        score = round(100 * math.exp(-distance / .10))
        notice = instructions(language)[2]
        blocks = [dict(order=i, category=label, category_label=tr(f'category.{label}', language),
                       model=model, catalog_id=rows[(category, model)]['id'], parameters={},
                       parameter_status='device_defaults_unverified', reason=notice,
                       added_in=rows[(category, model)]['added_in'], source_url=CATALOG_SOURCE)
                  for i, (category, model, label) in enumerate(desired, 1)]
        applicability = 'high' if output_mode == 'frfr' else 'medium' if output_mode == 'power_amp_cab' else 'low'
        limits = [notice, 'Heuristic similarity, not accuracy or original equipment identification.' if language == 'en'
                  else '휴리스틱 유사도이며 정확도·원곡 장비 식별 결과가 아닙니다.']
        if delay_omitted:
            limits.append('Digital Delay omitted: requires CorOS 2.1.0 or later.' if language == 'en'
                          else 'Digital Delay 제외: CorOS 2.1.0 이상에서 사용할 수 있습니다.')
        if output_mode != 'frfr':
            limits.append(tr('limit.amp_front' if output_mode == 'amp_front' else 'limit.real_cab', language))
        ranked.append(dict(template_id=f'qc_{index}', name=f'Quad Cortex · {name}',
                           archetype=name, description='Native-device starting point' if language == 'en' else '내장 모델 기반 수동 적용 시작점',
                           match_percent=score, tags=['Quad Cortex', 'native'],
                           pickup_correction='Adjust by ear; no numerical pickup correction.' if language == 'en' else '픽업 차이는 청감 보정하세요. 수치 보정은 미적용입니다.',
                           output_mode=output_mode, output_mode_label=choice_label('output', output_mode, language),
                           route_applicability=applicability, route_applicability_label=tr(f'route.{applicability}', language),
                           reference_amp=amp, reference_cabinet=cab,
                           amp_included=output_mode != 'amp_front', cabinet_included=output_mode == 'frfr',
                           omitted_reference_amp=amp if output_mode == 'amp_front' else None,
                           omitted_reference_cabinet=cab if output_mode != 'frfr' else None,
                           blocks=blocks, limitations=limits))
    if len(ranked) < 3:
        raise ValueError('Not enough verified native recipes for this CorOS version')
    return sorted(ranked, key=lambda item: item['match_percent'], reverse=True)[:3]
