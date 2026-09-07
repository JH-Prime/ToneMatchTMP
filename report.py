"""ToneMatch TMP 결과를 사람이 읽을 수 있는 형태로 내보내는 도구."""

from __future__ import annotations

import html
import math
from pathlib import Path
from urllib.parse import urlsplit

from engine import human_feature_rows
from i18n import tr
from voicing import pitch_class_names


REPORT_TEXT = {
    "match": {"ko": "톤 유사도", "en": "Tone similarity"},
    "pickup": {"ko": "픽업 보정", "en": "Pickup correction"},
    "reason": {"ko": "이유", "en": "Reason"},
    "caution": {"ko": "주의", "en": "Caution"},
    "recipe": {"ko": "추천", "en": "Recipe"},
    "title": {"ko": "ToneMatch TMP 분석 결과", "en": "ToneMatch TMP Analysis Result"},
    "subtitle": {"ko": "오디오 특징 기반 Tone Master Pro 시작점 추천", "en": "Tone Master Pro starting points from audio features"},
    "firmware": {"ko": "대상 펌웨어", "en": "Target firmware"},
    "source": {"ko": "분석 소스", "en": "Analysis source"},
    "file": {"ko": "파일", "en": "File"},
    "range": {"ko": "구간", "en": "Range"},
    "url": {"ko": "참고 URL", "en": "Reference URL"},
    "none": {"ko": "없음", "en": "None"},
    "input": {"ko": "입력", "en": "Input"},
    "output": {"ko": "출력", "en": "Output"},
    "applicability": {"ko": "연결 경로 적용성", "en": "Route applicability"},
    "isolation": {"ko": "기타 분리", "en": "Guitar isolation"},
    "isolated": {"ko": "Demucs guitar stem만 분석", "en": "Demucs guitar stem only"},
    "skipped": {"ko": "기타 단독 파일 · 분리 생략", "en": "Guitar-only file · isolation skipped"},
    "fingerprint": {"ko": "톤 지문", "en": "Tone fingerprint"},
    "reference_compare": {"ko": "참조 비교", "en": "Reference compare"},
    "band": {"ko": "대역", "en": "Band"},
    "reference": {"ko": "Reference", "en": "Reference"},
    "current": {"ko": "Current", "en": "Current"},
    "reference_profile_note": {
        "ko": "분석 오디오에서 만든 레벨 정규화 6대역 참조 프로필입니다.",
        "en": "A level-normalized six-band reference profile built from the analyzed audio.",
    },
    "live_values_not_saved": {
        "ko": "Current와 Δ는 실시간 입력 세션 값이므로 이 저장 보고서에는 포함되지 않습니다. 앱에서 입력 모니터링을 시작하면 비교할 수 있습니다.",
        "en": "Current and Δ are live-input session values, so they are not stored in this report. Start input monitoring in the app to compare them.",
    },
    "warnings": {"ko": "해석 주의", "en": "Interpretation notes"},
    "steps": {"ko": "적용 순서", "en": "Application steps"},
    "diagnostics": {"ko": "DSP 진단값", "en": "DSP diagnostics"},
    "footer": {
        "ko": "Fender 및 Tone Master는 FMIC의 상표입니다. ToneMatch TMP는 Fender와 무관한 비공식 도구이며 실제 장비·원 프리셋을 식별한다고 보장하지 않습니다.",
        "en": "Fender and Tone Master are trademarks of FMIC. ToneMatch TMP is an unofficial, unaffiliated tool and does not claim to identify the original equipment or preset.",
    },
}


def _rt(key: str, language: str) -> str:
    """HTML·텍스트 리포트 전용 문구를 선택 언어로 반환한다."""
    return REPORT_TEXT[key].get(language, REPORT_TEXT[key]["ko"])


def recipe_as_text(result: dict, recipe_index: int = 0) -> str:
    """선택한 추천 레시피의 블록·파라미터·이유를 일반 텍스트로 만든다."""
    language = result.get("language", "ko")
    recipe = result["recipes"][recipe_index]
    lines = [
        f"{recipe['name']} · {recipe['archetype']} · {_rt('match', language)} {recipe['match_percent']}%",
        recipe["description"],
        f"{_rt('output', language)}: {recipe.get('output_mode_label', result['input_profile']['output_mode_label'])}",
        f"{_rt('applicability', language)}: {recipe.get('route_applicability_label', '-')}",
        f"{_rt('pickup', language)}: {recipe['pickup_correction']}",
        "",
    ]
    for block in recipe["blocks"]:
        lines.append(f"{block['order']:02d}. [{block.get('category_label', block['category'])}] {block['model']}")
        for name, value in block["parameters"].items():
            lines.append(f"    {name}: {value}")
        lines.append(f"    {_rt('reason', language)}: {block['reason']}")
    if recipe["limitations"]:
        lines.extend(["", f"{_rt('caution', language)}:"] + [f"- {item}" for item in recipe["limitations"]])
    return "\n".join(lines)


def _feature_bar(label: str, value: float) -> str:
    """0~1 특징값 하나를 HTML 퍼센트 막대 조각으로 변환한다."""
    percentage = max(0, min(100, int(round(value * 100))))
    return (
        '<div class="feature"><div class="feature-row"><span>'
        + html.escape(label)
        + f'</span><b>{percentage}%</b></div><div class="bar"><i style="width:{percentage}%"></i></div></div>'
    )


def _reference_link(value: object) -> str:
    """참고 주소는 HTTP(S)일 때만 링크로 만들고 나머지는 안전한 글자로 표시한다."""
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    raw_parts = urlsplit(raw_value)
    if raw_parts.scheme and raw_parts.scheme.lower() not in {"http", "https"}:
        return html.escape(raw_value)
    candidate = raw_value if raw_parts.scheme else "https://" + raw_value
    parsed = urlsplit(candidate)
    visible = html.escape(raw_value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return visible
    escaped_url = html.escape(candidate, quote=True)
    return f'<a href="{escaped_url}" rel="noopener noreferrer">{visible}</a>'


def _reference_compare_html(result: dict, language: str) -> str:
    """저장된 참조 프로필의 6대역 값과 라이브 값의 비저장 상태를 안전하게 표시한다."""
    profile = result.get("reference_spectrum")
    if not isinstance(profile, dict):
        return ""
    bands = profile.get("bands")
    if not isinstance(bands, list):
        return ""

    rows: list[str] = []
    for band in bands:
        if not isinstance(band, dict):
            continue
        label = band.get(f"label_{language}", band.get("label", band.get("name", band.get("id", "—"))))
        reference_db = next(
            (
                band[key]
                for key in ("relative_db", "reference_db", "level_db", "normalized_db")
                if key in band
            ),
            None,
        )
        if isinstance(reference_db, bool):
            continue
        try:
            reference_value = float(reference_db)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(reference_value):
            continue
        rows.append(
            "<tr>"
            f"<th>{html.escape(str(label))}</th>"
            f"<td>{reference_value:+.1f} dB</td>"
            "<td>—</td><td>—</td>"
            "</tr>"
        )
    if not rows:
        return ""

    return f"""
<section class="card recipe reference-compare">
  <div class="rank">Reference | Current | Δ</div>
  <h2>{_rt('reference_compare', language)}</h2>
  <p>{_rt('reference_profile_note', language)}</p>
  <table>
    <thead><tr><th>{_rt('band', language)}</th><th>{_rt('reference', language)}</th><th>{_rt('current', language)}</th><th>Δ</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  <p class="correction">{_rt('live_values_not_saved', language)}</p>
</section>
"""


def save_html(result: dict, path: str | Path) -> None:
    """외부 자원이 필요 없는 단일 HTML 분석 리포트를 UTF-8로 저장한다."""
    language = result.get("language", "ko")
    font_family = '"Arial Narrow",Arial,sans-serif' if language == "en" else '"Malgun Gothic","Noto Sans KR",sans-serif'
    source = result["source"]
    features = result["features"]
    recipes_html = []
    for rank, recipe in enumerate(result["recipes"], start=1):
        blocks_html = []
        for block in recipe["blocks"]:
            parameters = "".join(
                f"<tr><th>{html.escape(str(name))}</th><td>{html.escape(str(value))}</td></tr>"
                for name, value in block["parameters"].items()
            )
            blocks_html.append(
                f"""
                <article class="block">
                  <div class="block-index">{block['order']:02d}</div>
                  <div class="block-body">
                    <small>{html.escape(block.get('category_label', block['category']))}</small>
                    <h3>{html.escape(block['model'])}</h3>
                    <table>{parameters}</table>
                    <p>{html.escape(block['reason'])}</p>
                  </div>
                </article>
                """
            )
        limitations = "".join(f"<li>{html.escape(item)}</li>" for item in recipe["limitations"])
        recipes_html.append(
            f"""
            <section class="recipe">
              <div class="rank">{_rt('recipe', language)} {rank}</div>
              <div class="recipe-head">
                <div><h2>{html.escape(recipe['name'])}</h2><p>{html.escape(recipe['description'])}</p></div>
                <div class="match">{recipe['match_percent']}<small>%</small></div>
              </div>
              <p class="route">{_rt('output', language)} · {html.escape(str(recipe.get('output_mode_label', result['input_profile']['output_mode_label'])))}<br>{_rt('applicability', language)} · {html.escape(str(recipe.get('route_applicability_label', '-')))}</p>
              <p class="correction">{_rt('pickup', language)} · {html.escape(recipe['pickup_correction'])}</p>
              <div class="blocks">{''.join(blocks_html)}</div>
              {f'<ul class="limitations">{limitations}</ul>' if limitations else ''}
            </section>
            """
        )
    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in result["warnings"])
    steps = "".join(f"<li>{html.escape(item)}</li>" for item in result["application_steps"])
    reference_link = _reference_link(source.get("reference_url"))
    feature_bars = "".join(
        _feature_bar(label, features[key])
        for label, key in [
            (tr("feature.saturation", language), "saturation"),
            (tr("feature.brightness", language), "brightness"),
            (tr("feature.body", language), "body"),
            (tr("feature.compression", language), "compression"),
            (tr("feature.ambience", language), "ambience"),
            (tr("feature.modulation", language), "modulation"),
            (tr("feature.contamination", language), "mix_contamination"),
            (tr("feature.confidence", language), "analysis_confidence"),
        ]
    )
    diagnostics = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>"
        for label, value in human_feature_rows(features, language)
    )
    isolation_text = _rt("isolated", language) if result.get("source_separation", {}).get("used") else _rt("skipped", language)
    reference_compare_html = _reference_compare_html(result, language)
    voicing_rows = []
    for event in result.get("chord_voicing", {}).get("events", []):
        if event.get("chord_type") == "unknown":
            continue
        notes = pitch_class_names(event.get("pitch_classes", ())) or "—"
        profile = " · ".join(
            (
                tr(f"voicing.register.{event.get('register', 'unknown')}", language),
                tr(f"voicing.spacing.{event.get('spacing', 'unknown')}", language),
                tr(f"voicing.inversion.{event.get('inversion', 'unknown')}", language),
            )
        )
        shapes = "<br>".join(
            f"{html.escape(str(shape['label']))}: E A D G B e = {html.escape(' '.join(str(value) for value in shape['frets_low_e_to_high_e']))}"
            for shape in event.get("candidate_shapes", [])
        )
        voicing_rows.append(
            "<tr>"
            f"<td>{event['start_seconds']:.1f}s–{event['end_seconds']:.1f}s</td>"
            f"<td><b>{html.escape(str(event['symbol']))}</b><br>{int(round(event['confidence'] * 100))}%</td>"
            f"<td>{html.escape(notes)}</td><td>{html.escape(profile)}</td><td>{shapes or '—'}</td>"
            "</tr>"
        )
    voicing_body = "".join(voicing_rows) or f"<tr><td colspan='5'>{html.escape(tr('ui.voicing_empty', language))}</td></tr>"
    document = f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_rt('title', language)}</title>
<style>
:root{{--bg:#0b1117;--panel:#121b24;--panel2:#17232e;--line:#283846;--text:#edf4f7;--muted:#9fb0bc;--accent:#39d6a5;--accent2:#59a8ff;--warn:#ffca69}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(150deg,#071016,#0e1720 42%,#0b1117);color:var(--text);font:15px/1.58 {font_family}}}
.wrap{{max-width:1120px;margin:auto;padding:42px 24px 80px}} header{{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;border-bottom:1px solid var(--line);padding-bottom:26px}}
.eyebrow,.rank,small{{color:var(--accent);font-weight:700;letter-spacing:.08em;text-transform:uppercase}} h1{{font-size:34px;margin:5px 0 3px}} h2{{font-size:25px;margin:5px 0}} h3{{font-size:18px;margin:2px 0 12px}} p{{color:var(--muted)}}
.meta{{text-align:right;color:var(--muted)}} .grid{{display:grid;grid-template-columns:1.1fr .9fr;gap:20px;margin:24px 0}} .card,.recipe{{background:rgba(18,27,36,.96);border:1px solid var(--line);border-radius:18px;padding:22px;box-shadow:0 15px 35px #0003}}
.feature{{margin:13px 0}} .feature-row{{display:flex;justify-content:space-between}} .bar{{height:7px;background:#25323d;border-radius:9px;overflow:hidden;margin-top:6px}} .bar i{{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2))}}
table{{width:100%;border-collapse:collapse}} th,td{{padding:7px 9px;border-bottom:1px solid #263541;text-align:left;vertical-align:top}} th{{color:#c6d3da;width:45%;font-weight:600}} td{{color:var(--text)}}
  .recipe{{margin-top:24px}} .recipe-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:20px}} .match{{font-size:52px;color:var(--accent);font-weight:800;line-height:1}} .match small{{font-size:17px}} .route{{color:var(--warn);font-weight:700;border-left:3px solid var(--warn);padding-left:11px}} .correction{{background:#0d171f;border-radius:10px;padding:10px 13px}}
.blocks{{display:grid;gap:12px;margin-top:18px}} .block{{display:flex;gap:14px;background:var(--panel2);border:1px solid #2a3c49;border-radius:14px;padding:16px}} .block-index{{display:grid;place-items:center;min-width:42px;height:42px;border-radius:11px;background:#0b131a;color:var(--accent);font-weight:800}} .block-body{{flex:1}} .block-body p{{margin-bottom:0}}
.warning{{border-left:4px solid var(--warn)}} a{{color:var(--accent2);word-break:break-all}} footer{{margin-top:28px;color:#7f929f;text-align:center}} @media(max-width:760px){{.grid{{grid-template-columns:1fr}}header{{display:block}}.meta{{text-align:left;margin-top:12px}}}}
</style>
</head>
<body><main class="wrap">
<header><div><div class="eyebrow">Unofficial Tone Recipe</div><h1>ToneMatch TMP</h1><p>{_rt('subtitle', language)}</p></div><div class="meta">{_rt('firmware', language)} {html.escape(result['target_firmware'])}<br>{html.escape(result['model_guide'])}</div></header>
<div class="grid">
  <section class="card"><h2>{_rt('source', language)}</h2><table><tr><th>{_rt('file', language)}</th><td>{html.escape(source['file_name'])}</td></tr><tr><th>{_rt('range', language)}</th><td>{source['start_seconds']:.1f}s – {source['end_seconds']:.1f}s</td></tr><tr><th>{_rt('url', language)}</th><td>{reference_link or _rt('none', language)}</td></tr><tr><th>{_rt('input', language)}</th><td>{html.escape(result['input_profile']['pickup_label'])}</td></tr><tr><th>{_rt('output', language)}</th><td>{html.escape(result['input_profile']['output_mode_label'])}</td></tr><tr><th>{_rt('isolation', language)}</th><td>{html.escape(isolation_text)}</td></tr></table></section>
  <section class="card"><h2>{_rt('fingerprint', language)}</h2>{feature_bars}</section>
</div>
{reference_compare_html}
{''.join(recipes_html)}
<section class="card recipe"><div class="rank">{tr('ui.voicing_tab', language)}</div><h2>{tr('ui.voicing_chord', language)}</h2><p>{tr('ui.voicing_intro', language)}</p><table><thead><tr><th>{tr('ui.voicing_time', language)}</th><th>{tr('ui.voicing_chord', language)}</th><th>{tr('ui.voicing_notes', language)}</th><th>{tr('ui.voicing_profile', language)}</th><th>{tr('ui.playable_shapes', language)}</th></tr></thead><tbody>{voicing_body}</tbody></table><p class="correction">{tr('ui.voicing_limit', language)}</p></section>
<div class="grid">
  <section class="card warning"><h2>{_rt('warnings', language)}</h2><ul>{warnings}</ul></section>
  <section class="card"><h2>{_rt('steps', language)}</h2><ol>{steps}</ol></section>
</div>
<section class="card"><h2>{_rt('diagnostics', language)}</h2><table>{diagnostics}</table></section>
<footer>{_rt('footer', language)}</footer>
</main></body></html>"""
    Path(path).write_text(document, encoding="utf-8")
