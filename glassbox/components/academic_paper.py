"""
templates/academic_paper.py — Glass Box Academic Paper Template

Provides the initial HTML content for an academic paper scaffold.
Designed for: undergraduate/postgraduate essays, research papers, reports.

Usage in editor.py:
    from templates.academic_paper import ACADEMIC_PAPER_TEMPLATE
    self.editor_ref.value = ACADEMIC_PAPER_TEMPLATE
"""

ACADEMIC_PAPER_TEMPLATE = """
<h1>[Your Paper Title Here]</h1>

<p style="text-align:center;color:#6b7280;font-size:0.9em;">
  Author · Institution · Course Code · Date
</p>

<h2>Abstract</h2>
<p>
  A brief summary of your paper: the research question, methodology, key findings,
  and conclusions. Typically 150–250 words. Write this last.
</p>

<h2>1. Introduction</h2>
<p>
  Introduce the topic and establish its significance. State your thesis or research
  question clearly. Outline the structure of the paper.
</p>

<h2>2. Background / Literature Review</h2>
<p>
  Summarise the existing scholarship relevant to your topic. Identify gaps or
  tensions in the literature that your paper addresses. Cite sources appropriately.
</p>

<h2>3. Methodology</h2>
<p>
  Describe how you gathered and analysed your evidence or data. Justify your choices.
  This section may be omitted for purely argumentative essays.
</p>

<h2>4. Analysis / Discussion</h2>
<p>
  Present your argument or findings. Structure this section with sub-headings if
  the paper is long. Support each claim with evidence.
</p>

<h3>4.1 [First Argument or Finding]</h3>
<p>Develop your first main point here.</p>

<h3>4.2 [Second Argument or Finding]</h3>
<p>Develop your second main point here.</p>

<h2>5. Conclusion</h2>
<p>
  Restate your thesis in light of the analysis. Summarise what your paper has
  established. Suggest implications or directions for future research.
</p>

<h2>References</h2>
<p>
  List all cited sources here in your required citation style (APA, MLA, Chicago,
  Harvard, etc.). Glass Box records which passages were AI-assisted — you remain
  responsible for all citations.
</p>

<blockquote>
  <p>
    <strong>Glass Box note:</strong> This document is being recorded as a TWFF session.
    AI-assisted passages will be highlighted in the exported PDF. Export via
    <em>Export PDF</em> to produce an annotated copy with an AI usage appendix.
  </p>
</blockquote>
"""

# ── Template metadata ──────────────────────────────────────────────────────
TEMPLATE_META = {
    "id":          "academic_paper",
    "label":       "Academic Paper",
    "description": "Essay / research paper scaffold with standard sections",
    "icon":        "school",
    "default_title": "Untitled Paper",
}
