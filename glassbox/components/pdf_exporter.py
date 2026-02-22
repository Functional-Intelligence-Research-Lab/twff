"""
pdf_exporter.py — Glass Box PDF Export (Dual-engine)

PRIMARY:  WeasyPrint — full CSS, annotation colours, paginated A4
FALLBACK: ReportLab  — pure Python, no native libs, works on Windows

Both engines produce:
  - Annotated document with colour-coded highlights
  - Appendix A: AI Usage Report (stats + interaction log)

Usage:
    exporter = PDFExporter(process_log=log)
    pdf_bytes = exporter.export(html_content, title, author, institution)
    # engine_name() returns "WeasyPrint" | "ReportLab" | "none"
"""
from __future__ import annotations

import datetime
import html as _html_mod
import io
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from components.process_log import ProcessLog

# Annotation colour palette — shared by both engines
ANN_COLOURS = {
    "ann-paraphrase": {"hex": "#3b82f6", "label": "AI Paraphrase",
                       "desc": "Text rewritten by an AI assistant"},
    "ann-generated":  {"hex": "#10b981", "label": "AI Generated",
                       "desc": "Text drafted entirely by an AI assistant"},
    "ann-external":   {"hex": "#f59e0b", "label": "External Source",
                       "desc": "Text pasted from an external source"},
    "ann-completion": {"hex": "#8b5cf6", "label": "AI Completion",
                       "desc": "Inline tab-completion accepted"},
}

# ── Engine detection

def _weasyprint_ok() -> bool:
    try:
        from ctypes.util import find_library
        if not (
            (find_library("gobject-2.0-0") or find_library("gobject-2.0")) and
            (find_library("pango-1.0-0")   or find_library("pango-1.0"))   and
            (find_library("cairo-2")       or find_library("cairo"))
        ):
            return False
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False


def _reportlab_ok() -> bool:
    try:
        import reportlab  # noqa: F401
        return True
    except ImportError:
        return False


def _pdf_export_ok() -> bool:
    """Check if ANY PDF engine (WeasyPrint or ReportLab) is available."""
    return _weasyprint_ok() or _reportlab_ok()


# ── WeasyPrint CSS

_CSS = """
@page { size: A4; margin: 2.5cm 2.8cm 2.8cm 2.8cm;
  @bottom-center { content: counter(page); font-family: sans-serif; font-size: 9pt; color:#888; } }
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:'Times New Roman',serif; font-size:11.5pt; line-height:1.75; color:#1a1917; }
h1 { font-family:sans-serif; font-size:18pt; font-weight:700; border-bottom:2pt solid #3b82f6;
     padding-bottom:4pt; margin-bottom:6pt; page-break-after:avoid; }
h2 { font-family:sans-serif; font-size:13pt; font-weight:700; margin-top:18pt; margin-bottom:4pt; page-break-after:avoid; }
h3 { font-family:sans-serif; font-size:11pt; font-weight:700; margin-top:12pt; margin-bottom:3pt; }
p  { margin-bottom:8pt; }
blockquote { border-left:3pt solid #bfdbfe; background:#eff6ff; margin:12pt 0; padding:6pt 12pt; font-style:italic; color:#374151; }
pre { font-family:monospace; font-size:9pt; background:#f4f3ef; border:0.5pt solid #d1d5db;
      border-left:3pt solid #3b82f6; padding:8pt 10pt; margin:10pt 0; white-space:pre-wrap; page-break-inside:avoid; }
code { font-family:monospace; font-size:9pt; background:#eff6ff; border:0.5pt solid #bfdbfe; color:#1e40af; padding:1pt 3pt; }
table { border-collapse:collapse; width:100%; margin:10pt 0; page-break-inside:avoid; }
th,td { border:0.5pt solid #d1d5db; padding:5pt 8pt; text-align:left; font-size:10.5pt; }
th { background:#eff6ff; font-family:sans-serif; font-weight:700; font-size:9pt;
     text-transform:uppercase; letter-spacing:.06em; color:#1e40af; }
.ann-paraphrase { background:rgba(59,130,246,.12); border-left:2.5pt solid #3b82f6; padding:0 3pt 0 4pt; }
.ann-generated  { background:rgba(16,185,129,.12); border-left:2.5pt solid #10b981; padding:0 3pt 0 4pt; }
.ann-external   { background:rgba(245,158,11,.14); border-left:2.5pt solid #f59e0b; padding:0 3pt 0 4pt; }
.ann-completion { background:rgba(139,92,246,.10); border-bottom:1.5pt dashed #8b5cf6; padding:0 2pt; }
.page-break { page-break-before:always; }
.app-h { font-family:sans-serif; font-size:14pt; font-weight:700; border-bottom:1pt solid #e5e7eb;
          padding-bottom:6pt; margin-bottom:16pt; }
.app-sub { font-family:sans-serif; font-size:10pt; font-weight:700; text-transform:uppercase;
            letter-spacing:.1em; color:#6b7280; margin-bottom:8pt; margin-top:16pt; }
.stat-row { display:flex; gap:12pt; margin-bottom:12pt; }
.stat-card { flex:1; border:0.5pt solid #e5e7eb; padding:8pt 10pt; background:#f9f8f5; }
.stat-n { font-family:sans-serif; font-size:18pt; font-weight:700; color:#3b82f6; line-height:1; }
.stat-l { font-family:sans-serif; font-size:8pt; text-transform:uppercase; letter-spacing:.08em; color:#6b7280; }
.legend-row { display:flex; align-items:center; gap:8pt; margin-bottom:5pt; font-size:10pt; }
.swatch { width:10pt; height:10pt; border-radius:50%; flex-shrink:0; }
.inline-legend { display:flex; gap:12pt; padding:6pt 10pt; background:#f9f8f5;
                  border:0.5pt solid #e5e7eb; margin-bottom:18pt;
                  font-family:sans-serif; font-size:8.5pt; color:#4b5563; }
.doc-meta { margin-bottom:24pt; padding-bottom:12pt; border-bottom:0.5pt solid #e5e7eb;
             font-family:sans-serif; font-size:9pt; color:#6b7280; }
.doc-meta div { margin-bottom:2pt; }
.app-footer { margin-top:24pt; padding-top:8pt; border-top:0.5pt solid #e5e7eb;
               font-size:8.5pt; color:#9ca3af; font-style:italic; }
.engine-note { text-align:right; font-size:7.5pt; color:#9ca3af; margin-top:4pt; }
"""


@dataclass
class PDFExporter:
    process_log: "ProcessLog"

    # ── Public ─

    def export(self, html_content: str, title: str = "Document",
               author: str = "", institution: str = "") -> bytes:
        if _weasyprint_ok():
            return self._weasy(html_content, title, author, institution)
        if _reportlab_ok():
            return self._reportlab(html_content, title, author, institution)
        raise RuntimeError(
            "No PDF engine found.\n"
            "  pip install reportlab          ← pure Python, works everywhere\n"
            "  python setup_weasyprint.py --setup  ← for full CSS rendering"
        )

    def engine_name(self) -> str:
        if _weasyprint_ok():   return "WeasyPrint"
        if _reportlab_ok():    return "ReportLab"
        return "none"

    # ── WeasyPrint

    def _weasy(self, content, title, author, institution) -> bytes:
        from weasyprint import CSS, HTML
        body = self._build_html(content, title, author, institution, engine="WeasyPrint")
        return HTML(string=body).write_pdf(stylesheets=[CSS(string=_CSS)])

    def _build_html(self, content, title, author, institution, engine="") -> str:
        esc = _html_mod.escape
        now = datetime.datetime.utcnow().strftime("%B %d, %Y")
        meta_fields = [f"<div><strong>Title:</strong> {esc(title)}</div>"]
        if author:      meta_fields.append(f"<div><strong>Author:</strong> {esc(author)}</div>")
        if institution: meta_fields.append(f"<div><strong>Institution:</strong> {esc(institution)}</div>")
        meta_fields.append(f"<div><strong>Date:</strong> {now}</div>")
        meta_fields.append(f"<div><strong>Session:</strong> {self.process_log.session_id[:8]}…</div>")

        legend_items = "".join(
            f'<span><span style="background:{c["hex"]};display:inline-block;'
            f'width:8pt;height:8pt;border-radius:50%;margin-right:4pt"></span>{c["label"]}</span>'
            for c in ANN_COLOURS.values()
        )

        stats = self._stats()
        ai_events = [e for e in self.process_log.events if e["type"] == "ai_interaction"]
        ai_rows = "".join(
            f"<tr><td>{e['timestamp'][11:19]}</td>"
            f"<td>{e.get('meta',{}).get('interaction_type','—')}</td>"
            f"<td>{e.get('meta',{}).get('model','—')}</td>"
            f"<td>{e.get('meta',{}).get('output_length','—')} ch</td>"
            f"<td>{e.get('meta',{}).get('acceptance','—')}</td></tr>"
            for e in ai_events
        ) or "<tr><td colspan='5'>No AI interactions recorded</td></tr>"

        ann_legend = "".join(
            f'<div class="legend-row"><span class="swatch" style="background:{c["hex"]}"></span>'
            f'<strong>{c["label"]}</strong> — {c["desc"]}</div>'
            for c in ANN_COLOURS.values()
        )

        return f"""<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"/><title>{esc(title)}</title></head>
<body>
<div class="doc-meta">{"".join(meta_fields)}</div>
<div class="inline-legend">{legend_items}</div>
<div class="document-body">{content}</div>
<div class="page-break"></div>
<div class="app-h">Appendix A — AI Usage Report</div>
<div class="app-sub">Session Summary</div>
<div class="stat-row">
  <div class="stat-card"><div class="stat-n">{stats["ai"]}</div><div class="stat-l">AI Interactions</div></div>
  <div class="stat-card"><div class="stat-n">{stats["paste"]}</div><div class="stat-l">External Pastes</div></div>
  <div class="stat-card"><div class="stat-n">{stats["edits"]}</div><div class="stat-l">Human Edits</div></div>
  <div class="stat-card"><div class="stat-n">{stats["mins"]}m</div><div class="stat-l">Writing Time</div></div>
</div>
<p style="font-size:9pt;color:#6b7280">Session: {self.process_log.session_id[:8]}… · {self.process_log.start_time} UTC</p>
<div class="app-sub">AI Interaction Log</div>
<table class="event-table">
  <thead><tr><th>Time</th><th>Type</th><th>Model</th><th>Output</th><th>Acceptance</th></tr></thead>
  <tbody>{ai_rows}</tbody>
</table>
<div class="app-sub">Annotation Key</div>
{ann_legend}
<div class="app-footer">Generated by Glass Box · {engine} engine · firl.nl · TWFF v0.1</div>
</body></html>"""

    # ── ReportLab ─

    def _reportlab(self, content, title, author, institution) -> bytes:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            HRFlowable,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buf  = io.BytesIO()
        doc  = SimpleDocTemplate(buf, pagesize=A4,
                                 leftMargin=2.8*cm, rightMargin=2.8*cm,
                                 topMargin=2.5*cm,  bottomMargin=2.8*cm,
                                 title=title, author=author)
        base = getSampleStyleSheet()

        def s(name, **kw):
            return ParagraphStyle(name, parent=base["Normal"], **kw)

        normal = s("n",  fontName="Times-Roman",    fontSize=11.5, leading=20, spaceAfter=6)
        h1s    = s("h1", fontName="Helvetica-Bold", fontSize=18,   leading=22, spaceAfter=8)
        h2s    = s("h2", fontName="Helvetica-Bold", fontSize=13,   leading=17, spaceBefore=14, spaceAfter=4)
        h3s    = s("h3", fontName="Helvetica-Bold", fontSize=11,   leading=15, spaceBefore=10, spaceAfter=3)
        meta   = s("m",  fontName="Helvetica",      fontSize=9,    leading=13,
                   textColor=colors.HexColor("#6b7280"), spaceAfter=3)
        bq     = s("bq", fontName="Times-Italic",   fontSize=11,   leading=18,
                   leftIndent=18, textColor=colors.HexColor("#374151"),
                   backColor=colors.HexColor("#eff6ff"), spaceAfter=10, borderPadding=6)
        ap_h   = s("ah", fontName="Helvetica-Bold", fontSize=14,   leading=18, spaceAfter=12)
        ap_sub = s("as", fontName="Helvetica-Bold", fontSize=9,    leading=12,
                   textColor=colors.HexColor("#6b7280"), spaceAfter=6, spaceBefore=14,
                   textTransform="uppercase")
        small  = s("sm", fontName="Times-Italic",   fontSize=8.5,  leading=12,
                   textColor=colors.HexColor("#9ca3af"), spaceBefore=20)
        code_s = s("co", fontName="Courier",        fontSize=9,    leading=13,
                   textColor=colors.HexColor("#6b7280"), spaceAfter=3)

        story = []
        now = datetime.datetime.utcnow().strftime("%B %d, %Y")

        # Meta block
        story.append(Paragraph(f"<b>Title:</b> {_html_mod.escape(title)}", meta))
        if author:      story.append(Paragraph(f"<b>Author:</b> {_html_mod.escape(author)}", meta))
        if institution: story.append(Paragraph(f"<b>Institution:</b> {_html_mod.escape(institution)}", meta))
        story.append(Paragraph(f"<b>Date:</b> {now}", meta))
        story.append(Paragraph(f"<b>Session:</b> {self.process_log.session_id[:8]}…", meta))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")))
        story.append(Spacer(1, 12))

        # Annotation legend bar
        legend_cells = [
            Paragraph(
                f'<font color="{c["hex"]}">■</font> {c["label"]}',
                s(f"lg_{k}", fontSize=8.5)
            )
            for k, c in ANN_COLOURS.items()
        ]
        lt = Table([legend_cells])
        lt.setStyle(TableStyle([
            ("BACKGROUND",  (0,0),(-1,-1), colors.HexColor("#f9f8f5")),
            ("BOX",         (0,0),(-1,-1), 0.5, colors.HexColor("#e5e7eb")),
            ("TOPPADDING",  (0,0),(-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING", (0,0),(-1,-1), 8),
        ]))
        story.append(lt)
        story.append(Spacer(1, 14))

        # Document content
        story.extend(self._html_to_rl(content, normal, h1s, h2s, h3s, bq))

        # Appendix
        story.append(PageBreak())
        stats = self._stats()
        story.append(Paragraph("Appendix A — AI Usage Report", ap_h))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb")))
        story.append(Spacer(1, 8))
        story.append(Paragraph("Session Summary", ap_sub))

        def _stat(num, lbl):
            t = Table([[
                Paragraph(f'<font color="#3b82f6" size="14"><b>{num}</b></font>', base["Normal"]),
            ],[
                Paragraph(f'<font color="#6b7280" size="7">{lbl.upper()}</font>', base["Normal"]),
            ]])
            t.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER")]))
            return t

        sc = Table([[
            _stat(stats["ai"],    "AI Interactions"),
            _stat(stats["paste"], "External Pastes"),
            _stat(stats["edits"], "Human Edits"),
            _stat(f'{stats["mins"]}m', "Writing Time"),
        ]])
        sc.setStyle(TableStyle([
            ("BOX",        (0,0),(-1,-1),0.5, colors.HexColor("#e5e7eb")),
            ("INNERGRID",  (0,0),(-1,-1),0.5, colors.HexColor("#e5e7eb")),
            ("BACKGROUND", (0,0),(-1,-1), colors.HexColor("#f9f8f5")),
            ("TOPPADDING", (0,0),(-1,-1), 8), ("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),10),
        ]))
        story.append(sc)
        story.append(Spacer(1,8))
        story.append(Paragraph(
            f"{self.process_log.session_id[:8]}… · {self.process_log.start_time} UTC", code_s))

        story.append(Paragraph("AI Interaction Log", ap_sub))
        ai_events = [e for e in self.process_log.events if e["type"] == "ai_interaction"]
        if ai_events:
            hdr = [Paragraph(f"<b>{t}</b>", base["Normal"])
                   for t in ("Time","Type","Model","Output","Acceptance")]
            rows = [hdr] + [
                [Paragraph(str(x), base["Normal"]) for x in [
                    e["timestamp"][11:19],
                    e.get("meta",{}).get("interaction_type","—"),
                    e.get("meta",{}).get("model","—"),
                    f"{e.get('meta',{}).get('output_length','—')} ch",
                    e.get("meta",{}).get("acceptance","—"),
                ]]
                for e in ai_events
            ]
            at = Table(rows, colWidths=[1.8*cm,3*cm,4*cm,2*cm,3.5*cm])
            at.setStyle(TableStyle([
                ("FONTNAME",     (0,0),(-1,0),"Helvetica-Bold"),
                ("FONTSIZE",     (0,0),(-1,-1),8),
                ("BACKGROUND",   (0,0),(-1,0), colors.HexColor("#eff6ff")),
                ("TEXTCOLOR",    (0,0),(-1,0), colors.HexColor("#1e40af")),
                ("BOX",          (0,0),(-1,-1),0.5, colors.HexColor("#d1d5db")),
                ("INNERGRID",    (0,0),(-1,-1),0.5, colors.HexColor("#e5e7eb")),
                ("TOPPADDING",   (0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",  (0,0),(-1,-1),5),
            ]))
            story.append(at)
        else:
            story.append(Paragraph("No AI interactions recorded.", normal))

        story.append(Paragraph("Annotation Key", ap_sub))
        for c in ANN_COLOURS.values():
            story.append(Paragraph(
                f'<font color="{c["hex"]}">■</font>  <b>{c["label"]}</b> — {c["desc"]}',
                s("ak", fontSize=10, leading=16, spaceAfter=4)
            ))

        story.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#e5e7eb"), spaceAfter=6, spaceBefore=20))
        story.append(Paragraph(
            "Generated by Glass Box · ReportLab engine · firl.nl · TWFF v0.1", small))

        doc.build(story)
        return buf.getvalue()

    # ── HTML → ReportLab flowables

    def _html_to_rl(self, raw: str, normal, h1, h2, h3, bq):
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, Spacer
        base = getSampleStyleSheet()

        # Replace annotation spans with coloured text
        def repl_span(m):
            cls  = m.group(1)
            text = m.group(2)
            col  = ANN_COLOURS.get(cls, {}).get("hex", "#000000")
            return f'<font color="{col}">{_html_mod.escape(re.sub(r"<[^>]+>","",text))}</font>'

        processed = re.sub(
            r'<span[^>]*class="(ann-[a-z]+)"[^>]*>(.*?)</span>',
            repl_span, raw, flags=re.DOTALL
        )
        processed = re.sub(r'\s+', ' ', processed)

        story    = []
        tag_map  = {
            "h1": h1, "h2": h2, "h3": h3,
            "p": normal, "blockquote": bq, "li": normal,
        }
        blocks   = re.split(
            r'(</?(?:h[123]|p|blockquote|ul|li)>|<br\s*/?>)', processed
        )
        cur_tag  = None
        buf: list[str] = []

        for chunk in blocks:
            m = re.match(r'<(/?)([a-z0-9]+)\s*/?>', chunk, re.I)
            if not m:
                buf.append(chunk)
                continue
            closing, tag = m.group(1) == "/", m.group(2).lower()
            if tag in ("ul",):
                continue  # handled via li
            if not closing:
                cur_tag = tag
                buf = []
            else:
                text = " ".join(buf).strip()
                buf  = []
                if text and cur_tag in tag_map:
                    style = tag_map[cur_tag]
                    try:
                        story.append(Paragraph(text, style))
                    except Exception:
                        clean = re.sub(r'<[^>]+>', '', text)
                        story.append(Paragraph(_html_mod.escape(clean), style))
                cur_tag = None
        return story

    # ── Stats helper ─

    def _stats(self) -> dict:
        evts = self.process_log.events
        try:
            start = self._ts(self.process_log.start_time)
            ends  = [e for e in evts if e["type"] == "session_end"]
            end   = self._ts(ends[-1]["timestamp"]) if ends else datetime.datetime.utcnow()
            mins  = max(1, int((end - start).total_seconds() / 60))
        except Exception:
            mins = 0
        return {
            "ai":    sum(1 for e in evts if e["type"] == "ai_interaction"),
            "paste": sum(1 for e in evts if e["type"] == "paste"),
            "edits": sum(1 for e in evts if e["type"] == "edit"),
            "mins":  mins,
        }

    @staticmethod
    def _ts(ts: str) -> datetime.datetime:
        return datetime.datetime.strptime(ts.rstrip("Z").split(".")[0], "%Y-%m-%dT%H:%M:%S")
