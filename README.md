# Tracked Writing File Format (TWFF)

<div align="center">
  <img src="image.png" width="40%" alt="Visualization of a sample TWFF process log" />
  <br/><br/>
  <strong>An open standard for Verifiable Effort in writing.</strong><br/>
  Moving past probabilistic AI detection toward deterministic process transparency.
  <br/><br/>
  <a href="https://demo.firl.nl/">Live Demo</a> ·
  <a href="https://firl.nl/research/blog/Manifesto/">Read the Manifesto</a> ·
  <a href="./spec/v0.1/README.md">Spec v0.1</a> ·
  <a href="./glassbox/README.md">Glass Box</a>
</div>

---

## What is TWFF?

TWFF is a ZIP-based container format that stores a written document alongside a deterministic audit trail of how it was produced including AI interactions, paste events,  revision history, and timing metadata.

The goal is **Verifiable Effort**: a cryptographic record of the writing process that an author can voluntarily share to declare thier AI usage.

> Unlike probabilistic AI detectors that guess authorship from final text, TWFF is the Glass Box alternative that does not detect; but records.

---

## Why a Container Format?

Packaging content and metadata together (modelled on EPUB) enables a range of disclosure granularities:

| Use Case | Components Shared | What It Enables |
|---|---|---|
| Research & Analytics | JSON log only | Privacy-preserving studies of AI usage patterns |
| Verification & Audit | Full container | Cryptographic proof of work |
| Visualization | Content + JSON | Rich, annotated views of the writing process |
| Archival | Full container + assets | Complete record of the creative process |

---

## Design Principles

| Principle | Description |
|---|---|
| **Local-First** | All telemetry is generated and stored on the creator's machine. No third-party servers are involved unless the user chooses to share. |
| **Deterministic** | Events are recorded in real time, providing a complete, non-probabilistic audit trail. |
| **Privacy-Preserving** | Content is stored separately from process metadata. Users control what to share and with whom. |
| **Extensible** | The container format accommodates additional assets, transcripts, and cryptographic signatures. |
| **Open Standard** | TWFF is free to implement. No proprietary lock-in. |

---

## Repository Structure

```text
twff/
├── spec/                        ← The open standard
│   ├── SPEC.md                  ← Normative specification
│   ├── process-log.schema.json  ← JSON Schema for process-log.json
│   ├── manifest.schema.json     ← JSON Schema for manifest.xml
│   └── v0.1/                    ← Version-pinned release
│       ├── README.md
│       ├── schema.json
│       └── examples/            ← Reference .twff containers
│           ├── basic/           ← Minimal valid container
│           └── full/            ← Complete container with all optional fields
│
├── glassbox/                    ← Reference implementation
│   ├── README.md
│   ├── app.py
│   ├── requirements.txt
│   ├── components/
│   │   ├── editor.py            ← NiceGUI WYSIWYG (UI only)
│   │   ├── layout.py            ← Application shell
│   │   └── process_log.py       ← TWFF session recording (framework-agnostic)
│   └── css/
│       └── theme.css
│
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
└── LICENSE
```

**Why are `spec/` and `glassbox/` separated?**

Glass Box is one implementation of the standard. They version independently. Future implementations ie. browser extensions, LMS plugins, CLI tools, will use `process_log.py` directly without importing any UI code.

---

## Specification Overview

→ Full specification: [`spec/SPEC.md`](./spec/SPEC.md)
→ Version-pinned release: [`spec/v0.1/README.md`](./spec/v0.1/README.md)

### Container Structure

```
document.twff  (ZIP archive)
├── content/
│   ├── document.xhtml           # Primary written work (XHTML required)
│   ├── images/
│   └── assets/
│       └── references.bib
├── meta/
│   ├── process-log.json         # Core event log (REQUIRED)
│   ├── manifest.xml             # Container manifest (RECOMMENDED)
│   └── chat-transcript.json     # Full AI conversation history (OPTIONAL)
└── META-INF/
    └── signatures.xml           # Integrity verification (OPTIONAL)
```

### Process Log — Minimal Example

```json
{
  "version": "0.1.0",
  "session_id": "3f2a1b4c-...",
  "user_id": "anon-7f3a2c1b9d4e",
  "start_time": "2026-02-16T09:00:00Z",
  "end_time": "2026-02-16T11:30:00Z",
  "content_source": "content/document.xhtml",
  "events": [
    { "timestamp": "2026-02-16T09:00:01Z", "type": "session_start", "meta": {} },
    {
      "timestamp": "2026-02-16T09:01:15Z",
      "type": "edit",
      "meta": { "position_start": 0, "position_end": 280, "source": "human" }
    },
    {
      "timestamp": "2026-02-16T09:10:45Z",
      "type": "ai_interaction",
      "meta": {
        "interaction_type": "paraphrase",
        "model": "gpt-4o",
        "output_preview": "subsequently, the implementation...",
        "output_length": 320,
        "position_start": 575,
        "position_end": 895,
        "acceptance": "partially_accepted"
      }
    },
    { "timestamp": "2026-02-16T11:30:00Z", "type": "session_end", "meta": {} }
  ]
}
```

### Event Types

| Type | Description | Key `meta` Fields |
|---|---|---|
| `session_start` | Beginning of a writing session | — |
| `session_end` | End of session | — |
| `edit` | Human typing or deletion | `position_start`, `position_end`, `source` |
| `paste` | Text pasted from clipboard | `char_count`, `source`, `position_start`, `position_end` |
| `ai_interaction` | AI assistant invoked | `interaction_type`, `model`, `output_preview`, `output_length`, `acceptance` |
| `chat_interaction` | Multi-turn AI conversation | `message_count`, `message_preview`, `source_file` |
| `focus_change` | User navigated away from editor | `duration_ms` |
| `checkpoint` | Periodic auto-save snapshot | `char_count_total`, `word_count_total`, `position` |

### `acceptance` Values

| Value | Description |
|---|---|
| `fully_accepted` | Output used as-is |
| `partially_accepted` | Some output used, some discarded or edited |
| `modified` | Output used but significantly rewritten |
| `rejected` | Output discarded entirely |

---

## Integrity & Privacy

### Hash Chain (v0.1)

The `process-log.json` includes a `_integrity` block containing a SHA-256 hash of the events array concatenated with the `session_id` as salt. Any post-hoc modification to the log is detectable.

### What TWFF Does Not Store

- Individual keystroke content (only aggregated character counts per edit block)
- Raw prompts or full AI responses (only metadata previews, truncated to 100 characters)
- Personally identifiable information beyond a user-generated, rotatable anonymous ID
- Screen recordings, mouse movements, or biometric data

### User Control

All data is generated and stored locally. The user decides:
- Whether to share the container at all
- Whether to share only the JSON log (for research) or the full container (for verification)
- Whether to rotate their anonymous user ID between sessions

---

## Roadmap

| Phase | Deliverables | Target |
|---|---|---|
| **v0.1 Core** | Schema, Python reference implementation, basic visualizer | Q1 2026 |
| **v1.0 Tools** | Browser extension (Google Docs + Overleaf), visualizer v2, chat transcript support | Q2 2026 |
| **v1.2 Integration** | Canvas plugin, Moodle plugin, validator service | Q3 2026 |
| **v1.5 Future** | Cryptographic signing (RSA key pairs), decentralized storage, multi-author support | Q4 2026+ |

### Current Status

- [x] Specification v0.1 (schema, event types, container structure)
- [x] Reference implementation — Glass Box editor (Python / NiceGUI)
- [x] SHA-256 hash chain (integrity verification)
- [ ] properly define how the process-log.json interacts with the signatures.xml.
- [ ] Schema Enforcement: add script spec/validate_examples.py.
- [ ] Browser extension (Google Docs / Overleaf)
- [ ] TWFF visualizer (standalone)
- [ ] LMS integration (Canvas, Moodle)
- [ ] Validator service

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). All contributions are welcome — specification feedback, implementation ports, tooling, and documentation.

## Code of Conduct

See [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).

## License

[Apache](./LICENSE)

---

<div align="center">
  <strong>FIRL — Functional Intelligence Research Lab</strong><br/>
  <a href="https://firl.nl">firl.nl</a> ·
  <a href="https://linkedin.com/company/firl-nl">LinkedIn</a> ·
  <a href="https://github.com/Functional-Intelligence-Research-Lab">GitHub</a>
</div>
