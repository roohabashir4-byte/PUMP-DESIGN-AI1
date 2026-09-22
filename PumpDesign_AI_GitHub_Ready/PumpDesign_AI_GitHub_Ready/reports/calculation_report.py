"""Professional calculation-report generation for PumpDesign AI.

The report is a presentation layer only. It never recalculates engineering
values and never invents missing criteria. Numerical results come from the
stored deterministic workflow result; references come from the RAG state.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .references import reference_label


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _html_escape(value: Any) -> str:
    import html
    return html.escape(_fmt(value))


def _calculation_rows(calculations: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for i, calc in enumerate(calculations, 1):
        refs = calc.get("references") or []
        ref_text = "; ".join(_fmt(x) for x in refs) if refs else "No calculation-specific reference ID supplied"
        inputs = calc.get("inputs") or calc.get("substituted_values") or {}
        assumptions = calc.get("assumptions") or []
        blocks.append(f"""
        <section class="calc">
          <h3>{i}. {_html_escape(calc.get('name', 'Calculation'))}</h3>
          <table>
            <tr><th>Status</th><td>{_html_escape(calc.get('status'))}</td></tr>
            <tr><th>Formula</th><td><code>{_html_escape(calc.get('formula'))}</code></td></tr>
            <tr><th>Substituted values / inputs</th><td><pre>{_html_escape(inputs)}</pre></td></tr>
            <tr><th>Result</th><td><strong>{_html_escape(calc.get('value', calc.get('result')))} {_html_escape(calc.get('unit'))}</strong></td></tr>
            <tr><th>Method</th><td>{_html_escape(calc.get('method'))}</td></tr>
            <tr><th>Assumptions</th><td>{_html_escape(assumptions if assumptions else 'None stated')}</td></tr>
            <tr><th>References</th><td>{_html_escape(ref_text)}</td></tr>
            <tr><th>Notes</th><td>{_html_escape(calc.get('message') or calc.get('notes'))}</td></tr>
          </table>
        </section>""")
    return "\n".join(blocks) or '<p>No deterministic calculations were returned.</p>'


def _pipe_section(pipe_sizing: dict[str, Any]) -> str:
    if not pipe_sizing:
        return "<p>No pipe-sizing results were returned.</p>"
    blocks = []
    for side, data in pipe_sizing.items():
        if not isinstance(data, dict):
            continue
        selected = data.get("selected")
        candidate_rows = []
        for c in data.get("candidates", [])[:30]:
            candidate_rows.append(
                "<tr>" + "".join(f"<td>{_html_escape(c.get(k))}</td>" for k in ["size", "standard", "schedule_or_sdr", "inside_diameter_m", "velocity_mps", "head_loss_m", "velocity_status", "hydraulic_status"]) + "</tr>"
            )
        selected_html = _html_escape(selected or "Not selected")
        table = """
        <table class="small"><tr><th>Size</th><th>Standard</th><th>Schedule/SDR</th><th>ID (m)</th><th>Velocity (m/s)</th><th>Head loss (m)</th><th>Velocity status</th><th>Hydraulic status</th></tr>
        %s</table>""" % "".join(candidate_rows) if candidate_rows else "<p>No candidate list returned.</p>"
        blocks.append(f"<h3>{_html_escape(side.title())} pipe</h3><p><strong>Selection:</strong> {selected_html}</p><p>{_html_escape(data.get('selection_message') or data.get('message'))}</p>{table}")
    return "\n".join(blocks)


def build_report_payload(*, design_id: str, application: str, inputs: dict[str, Any], result: dict[str, Any], rag_context: dict[str, Any] | None = None, project: dict[str, Any] | None = None) -> dict[str, Any]:
    rag = rag_context or {}
    criteria = rag.get("criteria") or []
    references = rag.get("references") or []
    return {
        "report_id": f"RPT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "design_id": design_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "application": application,
        "project": project or {k: inputs.get(k) for k in ["project_name", "location", "jurisdiction", "building_type"] if inputs.get(k) is not None},
        "inputs": inputs,
        "result": result,
        "criteria": criteria,
        "references": references,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    result = payload.get("result") or {}
    lines = [
        f"# PumpDesign AI — Engineering Calculation Report",
        "",
        f"**Report ID:** {payload.get('report_id', '—')}  ",
        f"**Design ID:** {payload.get('design_id', '—')}  ",
        f"**Application:** {payload.get('application', '—')}  ",
        f"**Generated:** {payload.get('generated_at', '—')}",
        "",
        "## 1. Project / Design Basis",
        "",
    ]
    for key, value in (payload.get("project") or {}).items():
        lines.append(f"- **{key.replace('_',' ').title()}:** {_fmt(value)}")
    lines += ["", "## 2. Calculation Summary", "", f"**Design status:** {result.get('status', '—')}", ""]
    for c in result.get("calculations", []):
        lines += [f"### {c.get('name','Calculation')}", f"- **Status:** {c.get('status','—')}", f"- **Formula:** `{c.get('formula') or '—'}`", f"- **Inputs:** `{_fmt(c.get('inputs') or {})}`", f"- **Result:** **{_fmt(c.get('value', c.get('result')))} {c.get('unit') or ''}**", f"- **Method:** {_fmt(c.get('method'))}", f"- **Assumptions:** {_fmt(c.get('assumptions') or [])}", f"- **References:** {_fmt(c.get('references') or [])}", ""]
    lines += ["## 3. Pipe Sizing", "", f"```json\n{json.dumps(result.get('pipe_sizing') or {}, indent=2, default=str)}\n```", "", "## 4. Validation", ""]
    for v in result.get("validation", []):
        lines.append(f"- **{v.get('name','Validation')}:** {v.get('status','—')} — {_fmt(v.get('message'))}")
    if not result.get("validation"):
        lines.append("No validation results were returned.")
    lines += ["", "## 5. Engineering Criteria Retrieved", ""]
    for c in payload.get("criteria", []):
        lines.append(f"- **{c.get('parameter', c.get('criterion_id'))}:** {_fmt(c.get('value', c.get('min_value')))} {c.get('unit') or ''} — source `{c.get('source_reference_id','—')}`")
    lines += ["", "## 6. References", ""]
    for r in payload.get("references", []):
        lines.append(f"- {reference_label(r)}")
    lines += ["", "## 7. Engineering Limitations / Unresolved Items", "", "This report presents the deterministic results returned by PumpDesign AI. Missing project data, unavailable criteria, omitted minor losses, manufacturer-specific pump data, or unresolved validations remain explicitly unresolved and are not replaced with fabricated assumptions.", ""]
    return "\n".join(lines)


def render_html(payload: dict[str, Any]) -> str:
    result = payload.get("result") or {}
    project = payload.get("project") or {}
    refs = payload.get("references") or []
    criteria = payload.get("criteria") or []
    validation_rows = "".join(
        f"<tr><td>{_html_escape(v.get('name'))}</td><td>{_html_escape(v.get('status'))}</td><td>{_html_escape(v.get('severity'))}</td><td>{_html_escape(v.get('message'))}</td></tr>"
        for v in result.get("validation", [])
    ) or '<tr><td colspan="4">No validation results returned.</td></tr>'
    criterion_rows = "".join(
        f"<tr><td>{_html_escape(c.get('parameter'))}</td><td>{_html_escape(c.get('value', c.get('min_value')))}</td><td>{_html_escape(c.get('unit'))}</td><td>{_html_escape(c.get('source_reference_id'))}</td><td>{_html_escape(c.get('section'))}</td><td>{_html_escape(c.get('page'))}</td></tr>"
        for c in criteria
    ) or '<tr><td colspan="6">No criteria returned.</td></tr>'
    ref_rows = "".join(f"<li>{_html_escape(reference_label(r))}</li>" for r in refs) or "<li>No references returned.</li>"
    project_rows = "".join(f"<tr><th>{_html_escape(k.replace('_',' ').title())}</th><td>{_html_escape(v)}</td></tr>" for k,v in project.items())
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>PumpDesign AI Calculation Report</title><style>
body{{font-family:Arial,sans-serif;margin:34px;color:#222;line-height:1.4}} h1{{margin-bottom:4px}} h2{{border-bottom:1px solid #aaa;padding-bottom:5px;margin-top:28px}} h3{{margin-bottom:8px}} table{{border-collapse:collapse;width:100%;margin:8px 0 18px}} th,td{{border:1px solid #bbb;padding:7px;vertical-align:top;text-align:left}} th{{background:#eee}} .small{{font-size:12px}} .calc{{page-break-inside:avoid}} pre{{white-space:pre-wrap;margin:0}} code{{white-space:pre-wrap}} .status{{font-size:18px;font-weight:bold}} .footer{{margin-top:40px;font-size:11px;color:#666}}
</style></head><body>
<h1>💧 PumpDesign AI</h1><div>Engineering Calculation Report</div><p><strong>Report ID:</strong> {_html_escape(payload.get('report_id'))}<br><strong>Design ID:</strong> {_html_escape(payload.get('design_id'))}<br><strong>Application:</strong> {_html_escape(payload.get('application'))}<br><strong>Generated:</strong> {_html_escape(payload.get('generated_at'))}</p>
<h2>1. Project / Design Basis</h2><table>{project_rows}</table><h3>Design status</h3><div class='status'>{_html_escape(result.get('status'))}</div>
<h2>2. Detailed Calculations</h2>{_calculation_rows(result.get('calculations') or [])}
<h2>3. Pipe Sizing</h2>{_pipe_section(result.get('pipe_sizing') or {})}
<h2>4. Validation</h2><table><tr><th>Check</th><th>Status</th><th>Severity</th><th>Message</th></tr>{validation_rows}</table>
<h2>5. Engineering Criteria Retrieved from RAG</h2><table><tr><th>Parameter</th><th>Value</th><th>Unit</th><th>Source ID</th><th>Section</th><th>Page</th></tr>{criterion_rows}</table>
<h2>6. References</h2><ul>{ref_rows}</ul>
<h2>7. Engineering Limitations / Unresolved Items</h2><p>This report presents the deterministic results returned by PumpDesign AI. Missing project data, unavailable criteria, omitted minor losses, manufacturer-specific pump data, or unresolved validations remain explicitly unresolved and are not replaced with fabricated assumptions.</p>
<div class='footer'>PumpDesign AI — calculation presentation layer. Numerical values are reported from deterministic engineering workflows and are not independently recalculated by the report generator.</div></body></html>"""


def generate_pdf(payload: dict[str, Any], output_path: str | Path) -> Path:
    """Generate a PDF using reportlab. Raises a clear error if unavailable."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    except ImportError as exc:
        raise RuntimeError("reportlab is required to generate the PDF report.") from exc

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="CalcTitle", parent=styles["Heading3"], spaceBefore=8, spaceAfter=5))
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
    story = [Paragraph("PumpDesign AI", styles["Title"]), Paragraph("Engineering Calculation Report", styles["Heading2"]), Spacer(1, 6)]
    meta = payload
    story.append(Table([["Report ID", _fmt(meta.get("report_id"))], ["Design ID", _fmt(meta.get("design_id"))], ["Application", _fmt(meta.get("application"))], ["Generated", _fmt(meta.get("generated_at"))]], colWidths=[35*mm, 145*mm], style=[("GRID",(0,0),(-1,-1),0.5,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.lightgrey),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story += [Spacer(1,10), Paragraph("1. Project / Design Basis", styles["Heading2"])]
    project_rows = [[str(k).replace("_"," ").title(), _fmt(v)] for k,v in (meta.get("project") or {}).items()]
    if project_rows:
        story.append(Table(project_rows, colWidths=[55*mm,125*mm], style=[("GRID",(0,0),(-1,-1),0.5,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.lightgrey)]))
    result = meta.get("result") or {}
    story += [Spacer(1,8), Paragraph(f"Design status: <b>{_html_escape(result.get('status'))}</b>", styles["BodyText"]), Paragraph("2. Detailed Calculations", styles["Heading2"])]
    for i, calc in enumerate(result.get("calculations") or [], 1):
        story.append(Paragraph(f"{i}. {_html_escape(calc.get('name','Calculation'))}", styles["CalcTitle"]))
        rows = [
            ["Status", _fmt(calc.get("status"))], ["Formula", _fmt(calc.get("formula"))], ["Inputs", _fmt(calc.get("inputs") or {})],
            ["Result", f"{_fmt(calc.get('value', calc.get('result')))} {_fmt(calc.get('unit'))}"], ["Method", _fmt(calc.get("method"))],
            ["Assumptions", _fmt(calc.get("assumptions") or [])], ["References", _fmt(calc.get("references") or [])], ["Notes", _fmt(calc.get("message") or calc.get("notes"))],
        ]
        t = Table(rows, colWidths=[35*mm,145*mm], repeatRows=0)
        t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.4,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.whitesmoke),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),8)]))
        story.append(t)
    story += [Paragraph("3. Pipe Sizing", styles["Heading2"])]
    for side, data in (result.get("pipe_sizing") or {}).items():
        story.append(Paragraph(f"{str(side).title()} pipe — selection: {_html_escape(data.get('selected') or 'Not selected')}", styles["BodyText"]))
        story.append(Paragraph(_html_escape(data.get("selection_message") or data.get("message")), styles["Small"]))
    story += [Paragraph("4. Validation", styles["Heading2"])]
    vals = [["Check","Status","Severity","Message"]] + [[_fmt(v.get("name")),_fmt(v.get("status")),_fmt(v.get("severity")),_fmt(v.get("message"))] for v in result.get("validation", [])]
    if len(vals) == 1: vals.append(["No validation results","—","—","No validation results returned."])
    vt=Table(vals,colWidths=[40*mm,25*mm,25*mm,90*mm],repeatRows=1); vt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.4,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(vt)
    story += [Paragraph("5. Engineering Criteria Retrieved from RAG", styles["Heading2"])]
    cr=[["Parameter","Value","Unit","Source","Section","Page"]]+[[_fmt(c.get("parameter")),_fmt(c.get("value",c.get("min_value"))),_fmt(c.get("unit")),_fmt(c.get("source_reference_id")),_fmt(c.get("section")),_fmt(c.get("page"))] for c in meta.get("criteria",[])]
    if len(cr)==1: cr.append(["No criteria","—","—","—","—","—"])
    ct=Table(cr,colWidths=[38*mm,25*mm,20*mm,30*mm,35*mm,15*mm],repeatRows=1); ct.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.4,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),6.5),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(ct)
    story += [Paragraph("6. References", styles["Heading2"])]
    for ref in meta.get("references", []): story.append(Paragraph("• " + _html_escape(reference_label(ref)), styles["Small"]))
    story += [Paragraph("7. Engineering Limitations / Unresolved Items", styles["Heading2"]), Paragraph("Missing project data, unavailable criteria, omitted minor losses, manufacturer-specific pump data, or unresolved validations remain explicitly unresolved and are not replaced with fabricated assumptions.", styles["BodyText"])]
    doc.build(story)
    return path
