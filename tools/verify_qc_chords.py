"""사용자가 제공한 로컬 곡으로 v0.1.02 코드 전용 경로를 무음 검증한다.

공개 출력에는 파일명·경로·오디오·코드 시퀀스를 넣지 않는다. 정답률 평가가 아니다.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog import APP_VERSION
from chart_pdf import save_chart_pdf
from chord_edits import load_result, set_correction
from engine import AnalysisError, analyze_file, save_json
from report import save_html


def digest(path):
    """원본 보존 여부만 비교하며 해시 자체는 보고서에 공개하지 않는다."""
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(source):
    """전체 곡·발췌·실제 취소와 저장 호환성을 검사한다."""
    before = digest(source)
    checks = []
    for start, end in ((0, 0), (30, 90)):
        updates = []
        began = time.perf_counter()
        with patch('engine.separate_guitar_wav', side_effect=AssertionError('AI is not needed')):
            result = analyze_file(source, start, end, 'unknown', 'full_mix', 'frfr',
                                  analysis_kind='chords', device_id='line6_helix',
                                  progress=lambda value, _: updates.append(value))
        elapsed = time.perf_counter() - began
        assert result['recipes'] == [] and result['features'] == {}
        assert updates == sorted(updates) and updates[-1] == 100
        assert result['chord_voicing']['analysis_source'] == 'original_mix'
        assert all(not event['candidate_shapes'] for event in result['chord_voicing']['events'])
        # 임시 결과는 이 컴퓨터에만 두고 파일명도 저장 전에 익명화한다.
        result['source']['file_name'] = 'Private authorized sample'
        with tempfile.TemporaryDirectory(prefix='tonematch-v102-check-') as folder:
            root = Path(folder)
            edited = set_correction(result, 0, 'Dm9')
            save_json(edited, root / 'result.json')
            restored = load_result(root / 'result.json', 'en')
            assert restored['analysis_kind'] == 'chords'
            save_html(restored, root / 'result.html')
            pdf = save_chart_pdf(restored, root / 'chart.pdf')
            assert pdf['chart_pages'] > 0
        chords = result['chord_voicing']
        checks.append(dict(start_seconds=start, duration_seconds=result['source']['duration_seconds'],
                           elapsed_seconds=round(elapsed, 3), event_count=chords['event_count'],
                           tonal_coverage=chords['tonal_coverage'], diagnostics=chords['diagnostics'],
                           progress_updates=len(updates), progress_monotonic=True,
                           json_edit_reopen_html_pdf=True))
    cancelled = False
    def progress(value, _message):
        """첫 CQT 진행 알림 뒤 취소를 요청한다."""
        nonlocal cancelled
        cancelled = cancelled or value >= 21
    try:
        analyze_file(source, 0, 0, 'unknown', 'full_mix', 'frfr', analysis_kind='chords',
                     progress=progress, cancel_requested=lambda: cancelled)
    except AnalysisError:
        assert cancelled
    else:
        raise AssertionError('Expected cancellation')
    assert digest(source) == before
    return dict(ok=True, app_version=APP_VERSION, checks=checks, source_unchanged=True,
                cancelled_as_requested=True, temporary_exports_cleaned=True,
                real_song_accuracy_measured=False, audible_output_tested=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        parser.error('Output already exists; choose a new receipt')
    receipt = verify(arguments.source.resolve(strict=True))
    with arguments.output.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
    print(json.dumps(receipt, ensure_ascii=False))
