"""개발자 모드에서 쓰는 처리 블록 설명과 소스 추출 도구.

PyInstaller 포터블 배포 안에서도 실제 배포 소스를 읽을 수 있도록 ``devsource``
데이터 폴더를 먼저 찾고, 소스 실행 중에는 현재 프로젝트 파일을 대신 사용한다.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


# 화면 순서는 실제 ``engine.analyze_file`` 순서이며 ``*_en``은 영어 UI에 쓴다.
PIPELINE_BLOCKS: list[dict] = [
    {
        "id": "boot",
        "order": 1,
        "title": "앱 초기화",
        "title_en": "App initialization",
        "short": "테마 · 화면 · 개발 도구",
        "short_en": "Theme · UI · dev tools",
        "description": "Tkinter 상태와 화면을 만들고, 개발자 블록 다이어그램과 변경 기록을 준비한 뒤 이벤트 루프를 시작합니다.",
        "description_en": "Creates Tkinter state and UI, prepares the developer sequence diagram and changelog, then starts the event loop.",
        "inputs": "프로그램 실행",
        "inputs_en": "Program launch",
        "outputs": "사용 가능한 데스크톱 UI",
        "outputs_en": "Ready desktop UI",
        "symbols": [
            ("app.py", "_center_window"),
            ("app.py", "ToneMatchApp.__init__"),
            ("app.py", "ToneMatchApp._configure_style"),
            ("app.py", "ToneMatchApp._build_ui"),
            ("app.py", "ToneMatchApp._build_debug_tab"),
            ("app.py", "ToneMatchApp._build_changelog_tab"),
            ("app.py", "ToneMatchApp._toggle_developer_mode"),
            ("app.py", "ToneMatchApp._draw_debug_diagram"),
            ("app.py", "ToneMatchApp._select_debug_block"),
            ("app.py", "ToneMatchApp._append_debug_log"),
            ("app.py", "ToneMatchApp._set_debug_progress"),
            ("app.py", "main"),
        ],
        "progress": (-1, -1),
    },
    {
        "id": "input",
        "order": 2,
        "title": "입력 검증",
        "title_en": "Input validation",
        "short": "파일/녹음 · 구간 · 조건",
        "short_en": "File/recording · range · options",
        "description": "로컬 파일 또는 PC 재생음 녹음을 준비하고, 최대 20분 구간·장치·픽업·AI 분리·출력 조건을 검사합니다.",
        "description_en": "Prepares a local file or PC-playback recording and validates the up-to-20-minute range, device, pickup, AI-isolation, and output settings.",
        "inputs": "파일/녹음, 시작/끝 초, 장치, 픽업, 분리, 출력",
        "inputs_en": "File/recording, range, device, pickup, isolation, output",
        "outputs": "검증된 분석 요청",
        "outputs_en": "Validated analysis request",
        "symbols": [
            ("app.py", "ToneMatchApp._choose_audio"),
            ("app.py", "ToneMatchApp._open_reference"),
            ("app.py", "ToneMatchApp._parse_inputs"),
            ("app.py", "ToneMatchApp._start_analysis"),
            ("app.py", "ToneMatchApp._analysis_worker"),
            ("app.py", "ToneMatchApp._drain_events"),
            ("recorder.py", "list_capture_devices"),
            ("recorder.py", "record_device_to_wav"),
        ],
        "progress": (0, 7),
    },
    {
        "id": "decode",
        "order": 3,
        "title": "오디오 디코딩",
        "title_en": "Audio decoding",
        "short": "FFmpeg → 표준 PCM",
        "short_en": "FFmpeg → standard PCM",
        "description": "오디오·영상의 선택 구간 또는 전체 곡을 최대 20분까지 스테레오 16-bit PCM으로 바꿉니다.",
        "description_en": "Converts the chosen range or full audio/video item, up to 20 minutes, to stereo 16-bit PCM.",
        "inputs": "오디오 파일, 시작/길이",
        "inputs_en": "Audio source, start/duration",
        "outputs": "44.1 kHz 분리용 PCM 또는 22.05 kHz 분석 PCM",
        "outputs_en": "44.1 kHz separation PCM or 22.05 kHz analysis PCM",
        "symbols": [("engine.py", "decode_to_pcm_wav"), ("engine.py", "decode_segment"), ("engine.py", "read_pcm_wav")],
        "progress": (8, 17),
    },
    {
        "id": "separation",
        "order": 4,
        "title": "AI 기타 분리",
        "title_en": "AI guitar isolation",
        "short": "장치 탐지 · Demucs · 성능 진단",
        "short_en": "Device probe · Demucs · performance",
        "description": "백그라운드에서 CPU·CUDA와 GPU/VRAM을 탐지하고 자동·CPU·CUDA 선택을 검증한 뒤, Demucs가 30초 조각별 guitar stem만 분리합니다. 추론 시간·청크 속도·실시간 배수·최대 GPU 메모리를 진단에 남깁니다.",
        "description_en": "Probes CPU/CUDA and GPU/VRAM in the background, validates Auto/CPU/CUDA selection, then isolates only the guitar stem in 30-second Demucs chunks. Inference time, chunk speed, realtime factor, and peak GPU memory are recorded for diagnostics.",
        "inputs": "44.1 kHz 풀믹스 PCM, 연산 장치 선택",
        "inputs_en": "44.1 kHz full-mix PCM, compute-device preference",
        "outputs": "guitar stem WAV, 장치·VRAM·성능 진단",
        "outputs_en": "Guitar-stem WAV plus device, VRAM, and performance diagnostics",
        "symbols": [
            ("app.py", "ToneMatchApp._start_hardware_probe"),
            ("app.py", "ToneMatchApp._hardware_probe_worker"),
            ("app.py", "ToneMatchApp._apply_hardware_status"),
            ("app.py", "ToneMatchApp._change_compute_backend"),
            ("app.py", "ToneMatchApp._set_compute_controls_enabled"),
            ("app.py", "ToneMatchApp._format_bytes"),
            ("app.py", "ToneMatchApp._populate_diagnostics"),
            ("separator.py", "resolve_compute_device"),
            ("separator.py", "separator_runtime_status"),
            ("separator.py", "_pcm16_chunk"),
            ("separator.py", "_tensor_to_pcm16"),
            ("separator.py", "separate_guitar_wav"),
        ],
        "progress": (18, 69),
    },
    {
        "id": "features",
        "order": 5,
        "title": "DSP 특징 추출",
        "title_en": "DSP feature extraction",
        "short": "FFT · 레벨 · 공간 · 반복",
        "short_en": "FFT · level · space · repeats",
        "description": "프레임 FFT, 밴드 에너지, 다이내믹, 제로 크로싱, 온셋 자기상관과 스테레오 폭으로 톤 지문을 계산합니다.",
        "description_en": "Computes a tone fingerprint from frame FFT, band energy, dynamics, zero crossings, onset autocorrelation, and stereo width.",
        "inputs": "스테레오 PCM",
        "inputs_en": "Stereo PCM",
        "outputs": "ToneFeatures 원본 측정값",
        "outputs_en": "Raw ToneFeatures measurements",
        "symbols": [
            ("engine.py", "_frames"),
            ("engine.py", "_frame_rms"),
            ("engine.py", "_band_ratio"),
            ("engine.py", "_autocorrelation_metrics"),
            ("engine.py", "extract_features"),
        ],
        "progress": (70, 81),
    },
    {
        "id": "voicing",
        "order": 6,
        "title": "코드 보이싱 분석",
        "title_en": "Chord-voicing analysis",
        "short": "Chroma · 코드 · 역위 · 음역",
        "short_en": "Chroma · chord · inversion · range",
        "description": "guitar stem의 시간창별 chroma를 보수적인 코드 템플릿과 비교해 코드명·구성음·베이스/역위·음역·간격을 추정합니다.",
        "description_en": "Compares time-window chroma from the guitar stem with conservative chord templates to estimate symbol, pitch classes, bass/inversion, register, and spacing.",
        "inputs": "기타 단독 스테레오 PCM",
        "inputs_en": "Guitar-only stereo PCM",
        "outputs": "코드 보이싱 타임라인과 연주 후보",
        "outputs_en": "Chord-voicing timeline and playable candidates",
        "symbols": [
            ("voicing.py", "_window_pitch_profile"),
            ("voicing.py", "_score_chord"),
            ("voicing.py", "_classify_window"),
            ("voicing.py", "_merge_events"),
            ("voicing.py", "candidate_guitar_shapes"),
            ("voicing.py", "analyze_voicings"),
        ],
        "progress": (82, 85),
    },
    {
        "id": "correction",
        "order": 7,
        "title": "소스 보정",
        "title_en": "Source correction",
        "short": "기타 stem · 픽업 · 출력",
        "short_en": "Guitar stem · pickup · output",
        "description": "분리된 guitar stem 또는 기타 단독 입력의 잔여 오염도를 보수적으로 조정하고 픽업·출력 연결 보정을 준비합니다.",
        "description_en": "Conservatively adjusts residual contamination in the isolated guitar stem or guitar-only input and prepares pickup/output correction.",
        "inputs": "원본 ToneFeatures, 믹스 모드",
        "inputs_en": "Raw ToneFeatures, source mode",
        "outputs": "보정된 ToneFeatures",
        "outputs_en": "Corrected ToneFeatures",
        "symbols": [("engine.py", "_adjust_for_mix")],
        "progress": (86, 88),
    },
    {
        "id": "matching",
        "order": 8,
        "title": "모델 후보 매칭",
        "title_en": "Model candidate matching",
        "short": "특징 벡터 ↔ 템플릿",
        "short_en": "Feature vector ↔ templates",
        "description": "포화도·밝기·바디·압축·공간·모듈레이션의 가중 거리를 계산하여 기준 톤 중 상위 3개를 고릅니다.",
        "description_en": "Uses weighted distances for saturation, brightness, body, compression, ambience, and modulation to select the top three reference tones.",
        "inputs": "보정된 ToneFeatures, TEMPLATES",
        "inputs_en": "Corrected ToneFeatures, TEMPLATES",
        "outputs": "유사도순 템플릿 3개",
        "outputs_en": "Three templates ranked by similarity",
        "symbols": [("catalog.py", "@module"), ("engine.py", "_template_score")],
        "progress": (89, 92),
    },
    {
        "id": "recipe",
        "order": 9,
        "title": "TMP 레시피 생성",
        "title_en": "TMP recipe generation",
        "short": "출력 경로 · Amp/Cab · 파라미터",
        "short_en": "Output route · Amp/Cab · parameters",
        "description": "선택된 템플릿을 Tone Master Pro 블록으로 바꾸고 FRFR·파워앰프+실캐비닛·앰프 입력 연결에 맞춰 Amp Only와 Cabinet의 포함·생략 정책, 마이크 위치, 적용 순서를 생성합니다.",
        "description_en": "Converts selected templates into Tone Master Pro blocks and generates route-specific Amp Only/Cabinet inclusion rules, microphone placement, and application steps for FRFR, power amp plus real cabinet, or amp-input connections.",
        "inputs": "상위 템플릿, ToneFeatures, 픽업/출력 조건",
        "inputs_en": "Top templates, ToneFeatures, pickup/output settings",
        "outputs": "출력 경로 적합도가 표시된 추천 체인 3개",
        "outputs_en": "Three recommended chains with output-route applicability",
        "symbols": [
            ("engine.py", "_amp_parameters"),
            ("engine.py", "_drive_parameters"),
            ("engine.py", "_reverb_parameters"),
            ("engine.py", "_parse_mic_position"),
            ("engine.py", "_cabinet_parameters"),
            ("engine.py", "_recipe_from_template"),
            ("engine.py", "_application_steps"),
        ],
        "progress": (93, 96),
    },
    {
        "id": "result",
        "order": 10,
        "title": "결과 조립",
        "title_en": "Result assembly",
        "short": "진단 · 경고 · 적용 순서",
        "short_en": "Diagnostics · warnings · steps",
        "description": "원본/보정 특징과 추천 3개, 주의사항, 적용 순서를 버전이 명시된 JSON 구조로 조립합니다.",
        "description_en": "Assembles raw/corrected features, three recipes, warnings, and application steps into a versioned JSON structure.",
        "inputs": "특징과 레시피",
        "inputs_en": "Features and recipes",
        "outputs": "tonematch-tmp-recipe/v1 결과",
        "outputs_en": "tonematch-tmp-recipe/v1 result",
        "symbols": [
            ("engine.py", "analyze_file"),
            ("app.py", "ToneMatchApp._show_result"),
            ("app.py", "ToneMatchApp._render_recipe"),
            ("app.py", "ToneMatchApp._show_error"),
        ],
        "progress": (97, 100),
    },
    {
        "id": "export",
        "order": 11,
        "title": "내보내기",
        "title_en": "Export",
        "short": "JSON · HTML · 클립보드",
        "short_en": "JSON · HTML · clipboard",
        "description": "분석 결과를 기계 판독용 JSON, 사람이 읽는 HTML 리포트로 저장하거나 현재 결과·진단·개발자 탭을 텍스트로 복사합니다.",
        "description_en": "Saves results as machine-readable JSON or a human-readable HTML report, or copies the current result, diagnostics, or developer tab as text.",
        "inputs": "분석 결과",
        "inputs_en": "Analysis result",
        "outputs": "JSON/HTML/현재 탭 텍스트",
        "outputs_en": "JSON/HTML/current-tab text",
        "symbols": [
            ("engine.py", "save_json"),
            ("report.py", "recipe_as_text"),
            ("report.py", "_feature_bar"),
            ("report.py", "save_html"),
            ("app.py", "ToneMatchApp._default_export_name"),
            ("app.py", "ToneMatchApp._export_json"),
            ("app.py", "ToneMatchApp._export_html"),
            ("app.py", "ToneMatchApp._update_copy_availability"),
            ("app.py", "ToneMatchApp._copy_recipe"),
        ],
        "progress": (101, 101),
    },
]


def block_by_id(block_id: str) -> dict:
    """블록 식별자에 해당하는 설명 사전을 반환한다."""
    for block in PIPELINE_BLOCKS:
        if block["id"] == block_id:
            return block
    raise KeyError(block_id)


def localized_block(block_id: str, language: str = "ko") -> dict:
    """개발자 블록의 제목·설명·입출력을 선택한 표시 언어로 복사한다."""
    source = block_by_id(block_id)
    localized = dict(source)
    if language == "en":
        for key in ("title", "short", "description", "inputs", "outputs"):
            localized[key] = source.get(f"{key}_en", source[key])
    return localized


def block_for_progress(progress: int) -> str:
    """0~100 진행률을 현재 처리 중인 블록 식별자로 바꾼다."""
    value = max(0, min(100, int(progress)))
    for block in PIPELINE_BLOCKS[:-1]:
        low, high = block["progress"]
        if low <= value <= high:
            return str(block["id"])
    return "result"


def _source_roots() -> list[Path]:
    """EXE 번들 및 소스 실행 환경에서 코드 원본 후보 폴더를 만든다."""
    executable_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    module_root = Path(__file__).resolve().parent
    return [executable_root / "devsource", module_root / "devsource", module_root]


def source_file_path(file_name: str) -> Path:
    """개발자 뷰어에 표시할 배포 소스 파일의 실제 경로를 찾는다."""
    safe_name = Path(file_name).name
    for root in _source_roots():
        candidate = root / safe_name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"번들 소스 파일을 찾을 수 없습니다: {safe_name}")


def _find_symbol_node(tree: ast.AST, qualified_name: str) -> ast.AST | None:
    """점으로 구분된 함수 또는 클래스 메서드 이름의 AST 노드를 찾는다."""
    parts = qualified_name.split(".")
    nodes: list[ast.AST] = list(getattr(tree, "body", []))
    current: ast.AST | None = None
    for part in parts:
        current = next(
            (
                node
                for node in nodes
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and getattr(node, "name", None) == part
            ),
            None,
        )
        if current is None:
            return None
        nodes = list(getattr(current, "body", []))
    return current


def source_for_symbol(file_name: str, qualified_name: str) -> str:
    """한 함수의 한글 주석을 포함한 원문과 원본 줄 번호를 반환한다."""
    path = source_file_path(file_name)
    source = path.read_text(encoding="utf-8")
    if qualified_name == "@module":
        lines = source.splitlines()
        numbered = [f"{line_number:04d}  {line}" for line_number, line in enumerate(lines, start=1)]
        return f"# {file_name} · 전체 모듈 · L1–L{len(lines)}\n" + "\n".join(numbered)
    tree = ast.parse(source, filename=str(path))
    node = _find_symbol_node(tree, qualified_name)
    if node is None or not hasattr(node, "lineno"):
        return f"# {qualified_name}: 소스 위치를 찾지 못했습니다."
    lines = source.splitlines()
    start = int(node.lineno)
    end = int(getattr(node, "end_lineno", start))
    numbered = [f"{line_number:04d}  {lines[line_number - 1]}" for line_number in range(start, end + 1)]
    return f"# {file_name} · {qualified_name} · L{start}–L{end}\n" + "\n".join(numbered)


def code_for_block(block_id: str) -> str:
    """선택 블록에 연결된 모든 함수 소스를 구분선과 함께 합친다."""
    block = block_by_id(block_id)
    sections = []
    for file_name, qualified_name in block["symbols"]:
        sections.append(source_for_symbol(file_name, qualified_name))
    return ("\n\n" + "─" * 92 + "\n\n").join(sections)


def changelog_as_text(entries: list[dict], language: str = "ko") -> str:
    """구조화된 변경 기록을 앱 화면용 한국어 또는 영어 텍스트로 변환한다."""
    if language == "en":
        lines = ["ToneMatch TMP · Changelog", "Patch rule: 0.0.01 → 0.0.02 → 0.0.03 → 0.0.04 …", ""]
        changes_heading = "Changes"
        limits_heading = "Known limitations"
    else:
        lines = ["ToneMatch TMP · 변경 기록", "패치 규칙: 0.0.01 → 0.0.02 → 0.0.03 → 0.0.04 …", ""]
        changes_heading = "변경사항"
        limits_heading = "알려진 제한"
    for entry in entries:
        status = entry.get("status_en", entry["status"]) if language == "en" else entry["status"]
        changes = entry.get("changes_en", entry.get("changes", [])) if language == "en" else entry.get("changes", [])
        issue_key = "known_issues_en" if language == "en" else "known_issues"
        lines.extend([f"v{entry['version']}  ·  {entry['date']}  ·  {status}", "", changes_heading])
        lines.extend(f"  • {item}" for item in changes)
        if entry.get(issue_key):
            lines.extend(["", limits_heading])
            lines.extend(f"  • {item}" for item in entry[issue_key])
        lines.extend(["", "" + "─" * 72, ""])
    return "\n".join(lines)
