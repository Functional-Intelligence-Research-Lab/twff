# TWFF — Tracked Writing File Format

Open standard for **Verifiable Effort** in writing.
Moving past probabilistic AI detection toward deterministic process transparency.

→ **Read the Manifesto:** [firl.nl/research/blog/Manifesto](https://firl.nl/research/blog/Manifesto/)
→ **Try the demo:** [demo.firl.nl](https://demo.firl.nl)

---

## Repository Structure

```text
twff/
├── spec/               ← The open standard (spec, schema, examples)
│   ├── SPEC.md
│   └── schema/
│       ├── process-log.schema.json
│       └── manifest.schema.json
│
├── glassbox/           ← Reference implementation (the "Glass Box" editor)
│   ├── backend/
│   │   ├── app.py
│   │   ├── css/
│   │   │   └── theme.css
│   │   └── components/
│   │       ├── app.py          ← Entry point
│   │       ├── editor.py       ← NiceGUI WYSIWYG (UI only)
│   │       ├── layout.py       ← App shell
│   │       └── process_log.py  ← TWFF logging (framework-agnostic)
│   └── docs/
│
└── README.md           ← This file
```

### Why separate `spec/` and `glassbox/`?

The **spec** is an open standard — it has its own versioning, governance, and
contributor lifecycle. The **glassbox** is one implementation of that standard.
They should be able to version independently. Future implementations (browser
extension, LMS plugin, CLI) will import `process_log.py` without touching any NiceGUI code.

---

## Quick Start (Glass Box)

```bash
cd glassbox
pip install -r requirements.txt
python app.py
# → http://localhost:8080
```

---

## ANNOTATION_TYPES — Single Source of Truth

All annotation colours, CSS class names, log event types, and legend labels
are driven by a single registry in `glassbox/backend/components/process_log.py`:

```python
ANNOTATION_TYPES = {
    "ai_paraphrase":  { "css_class": "ann-paraphrase", "label": "AI Paraphrase", ... },
    "ai_generated":   { "css_class": "ann-generated",  "label": "AI Generated",  ... },
    "external_paste": { "css_class": "ann-external",   "label": "External Source", ... },
    "ai_completion":  { "css_class": "ann-completion", "label": "AI Completion", ... },
}
```

Adding a new annotation type = one dict entry. CSS, legend, and log all update automatically.

---

## License

Apache — [see LICENSE](./LICENSE)

**FIRL — Functional Intelligence Research Lab**
[firl.nl](https://firl.nl) · [LinkedIn](https://linkedin.com/company/firl-nl) · [GitHub](https://github.com/Functional-Intelligence-Research-Lab)
