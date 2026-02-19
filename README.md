# Tracked Writing File Format (TWFF) Specification v0.1

<div align="center"><img src="image.png" width=50% alt="figure1:visualization of sample TWFF declaration" /></div>


[demo](https://demo.firl.nl/)

## Overview

TWFF is a ZIP-based container format that stores the final written work, all other required resources for processing and the metadata of how the work was created.

The goal is to enable Verifiable Effort; a cryptographic proof of labor that an author can voluntarily disclose to verify the authenticity of their work.

Unlike probabilistic AI detectors that guess authorship from final text, TWFF provides a deterministic audit trail of the composition process. It is the Glass Box counterpart to the black-box detection industry.

> For the sake of simplicity GenAI/LLMs will be referenced as 'AI' in this version of the README

## Why a Container Format?

By packaging content and metadata together (similar to EPUB), TWFF enables:

| Use Case     | Components Shared     |What It Enables|
| ------------- | ------------- |-------------|
| Research & Analytics |JSON log only | Privacy-preserving studies of AI usage patterns |
| Verification & Audit | Full container | Cryptographic proof of work |
| Visualization | Content + JSON | Rich, annotated views of the writing process|
| Archival | Full container + assets | Complete record of the creative process|

<!-- ## The Glass Box Container

AI detection is probabilistic. It relies on statistical patterns to "guess" human authorship, leading to high false-positive rates and a lack of auditability.

TWFF is a deterministic container that separates content from process. Like EPUB, it packages:

- **The final work** (XHTML, plain text, images, etc.)
- **The process log** (JSON metadata of composition events)
- **Optional assets** (references, citations, chat transcripts)

This separation allows:
- **Full transparency:** Share the complete container for verification.
- **Privacy-preserving sharing:** User can Share only the JSON metadata for research.
- **Rich visualization:** Render the final work with inline annotations from the process log. -->

## Design Philosophy

| Principle     | Description     |
| ------------- | ------------- |
| Local-First |All telemetry is generated and stored on the creator's machine. No third-party servers are involved unless the user chooses to share. |
| Deterministic | Events are recorded in real time, providing a complete, non‑probabilistic audit trail.|
|Privacy-Preserving| The final content is stored separately from process metadata. Users control what to share.|
| Extensible | The container format allows for additional assets, transcripts, and signatures.|
|Open Standard | TWFF is free to implement, with no proprietary lock-in.|

## Container Structure

A TWFF file is a ZIP archive with the following recommended structure:

```text
document.twff
├── content/
│   ├── document.xhtml          # The final written work (XHTML recommended)
│   ├── images/                  # Embedded images (if any)
│   │   └── figure1.png
│   └── assets/                   # Other supporting files
│       ├── references.bib
|       └── style
├── meta/
│   ├── process-log.json         # Core event log (REQUIRED)
│   ├── chat-transcript.json      # Optional: full AI chat history
│   └── manifest.xml              # Container manifest
└── META-INF/
    └── signatures.xml             # Integrity verification (optional)
```

### File Naming Convention

| File    | Convention     | Required? |
| ------------- | ------------- |------------- |
Primary content | `content/document.xhtml` | Yes |
Process log | `meta/process-log.json` | Yes |
Manifest | `meta/manifest.xml` | Recommended |
Signatures | `META-INF/signatures.xml` | Optional |
Chat transcript | `meta/chat-transcript.json` | Optional |
Images | `content/images/*` | As needed |

### Content Format

TWFF recommends XHTML for the primary content because:

- It is XML-based and strict, making parsing and validation reliable.
- It supports embedded semantic markup (e.g., <span> with @data-* attributes).
- It is human-readable and widely supported.
- It can be easily transformed into other formats (pdf, Docx, HTML)

## Process Log Schema (process-log.json)

The process log (meta/process-log.json) captures how the document was constructed. It does not duplicate content; it references positions within the content file using character offsets (or XPath + text offsets for XML-savvy implementations).

### Schema Overview

| Field     | Type    | Description |
| ------------- | ------------- |-------------|
| `version` |string | Schema version (e.g., "0.1.0") |
| `session_id` | string |UUID for the writing session |
|`user_id` |string| Anonymous user identifier (user-generated, can be rotated)|
|`start_time`|string| ISO 8601 timestamp of session start|
|`end_time`|string| ISO 8601 timestamp of session end|
|`content_source`|string| Path to primary content file (e.g., "content/document.xhtml")|
|`events`|array| Array of event objects|

### Event Object

| Field     | Type    | Description |
| ------------- | ------------- |-------------|
| `timestamp` |string | ISO 8601 timestamp|
| `type` | string |Event type (see Event Types Reference) |
|`meta` |object| Type-specific metadata|

### Example

```json
{
  "version": "0.1.0",
  "session_id": "uuid-session-12345",
  "user_id": "anon-hash-6789",
  "start_time": "2026-02-16T09:00:00Z",
  "end_time": "2026-02-16T11:30:00Z",
  "content_source": "content/document.xhtml",
  "events": [
    {
      "timestamp": "2026-02-16T09:00:01Z",
      "type": "session_start",
      "meta": {}
    },
    {
      "timestamp": "2026-02-16T09:01:15Z",
      "type": "edit",
      "meta": {
        
        "position_start": 0,
        "position_end": 15,
        "source": "human"
      }
    },
    {
      "timestamp": "2026-02-16T09:05:20Z",
      "type": "paste",
      "meta": {
        "char_count": 450,
        "source": "external",
        "position_start": 125,
        "position_end": 575
      }
    },
    {
      "timestamp": "2026-02-16T09:10:45Z",
      "type": "ai_interaction",
      "meta": {
        "interaction_type": "paraphrase",
        "model": "integrated-llm-v1",
        "input_preview": "make this more formal",  // optional prompt preview,
        "output_preview": "subsequently, the implementation...", // first 50 chars
        "output_length": 320,
        "position_start": 575,
        "position_end": 895,
        "acceptance": "fully_accepted"
      }
    },
    {
      "timestamp": "2026-02-16T09:15:30Z",
      "type": "chat_interaction",
      "meta": {
        "message_count": 3,
        "message_preview": "can you help me outline...", // first message preview
        "source_file": "meta/chat-transcript.json"
      }
    },
    {
      "timestamp": "2026-02-16T11:30:00Z",
      "type": "session_end",
      "meta": {}
    }
  ]
}
```

### Event Types Reference

| Field     | Type    | Description |
| ------------- | ------------- |-------------|
|`session_start`| Beginning of a writing session |(none)|
|`session_end` |End of session| (none)|
|`edit` |Human typing or deletion| `position_start`, p`osition_end`, `source` ("human")
|`paste` |Text pasted from external source| `char_count`, `source` ("external" or "ai"), `position_start`, `position_end`|
|`ai_interaction` |AI assistant invoked |`interaction_type`, `model`, `input_preview`, `output_preview`, `output_length`, `position_start`, `position_end`, `acceptance`|
|`chat_interaction`| Multi-turn chat with AI| `message_count`, `message_preview`, `source_file` (link to full transcript)|
|`focus_change` |User switcd away from editor|`duration_ms`|
|`checkpoint` |Auto-save snapshot| `char_count_total`, `position` (cursr position)|

#### `interaction_type` Values (for `ai_interaction`)

|Value |Description|
| ------------- | ------------- |
|`brainstorm` | AI generated ideas or outline |
|`draft` |AI wrote thye full pasage|
| `paraphrase`| AI rewrote existing text|
|`summarize` |AI summarized content|
|`expand` | AI expanded a short phrase|
|`continue` | AI continued from cursor|

#### `acceptance` Values

|Value |Description |
| ------------- | ------------- |
|`fully_accepted`| All output used as-is|
|`partially_accepted`| Some output used, some edited|
|`rejected`| Output discarded (optional)|
|`modified`| Output used but significantly edited|

## Optional Components

### Chat Transcript Schema (chat-transcript.json)

For complete transparency, the container may include the full chat history with AI assistants.

```json
{
  "session_id": "uuid-session-12345",
  "messages": [
    {
      "timestamp": "2026-02-16T09:10:45Z",
      "role": "user",
      "content": "make this paragraph more formal: 'so yeah, the thing about AI is it's pretty cool but also kinda scary'"
    },
    {
      "timestamp": "2026-02-16T09:11:02Z",
      "role": "assistant",
      "model": "integrated-llm-v1",
      "content": "The advent of artificial intelligence presents a duality: remarkable potential tempered by significant societal considerations."
    },
    {
      "timestamp": "2026-02-16T09:11:15Z",
      "role": "user",
      "content": "that works, insert it"
    }
  ]
}
```

### Manifest (meta/manifest.xml)

The manifest lists all files in the container and their media types, similar to EPUB's package.opf.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest>
  <item id="content" href="content/document.xhtml" media-type="application/xhtml+xml"/>
  <item id="log" href="meta/process-log.json" media-type="application/json"/>
  <item id="chat" href="meta/chat-transcript.json" media-type="application/json"/>
  <item id="img1" href="content/images/figure1.png" media-type="image/png"/>
</manifest>
```

### Integrity & Signing

To prevent tampering, TWFF supports cryptographic signing of the container.

#### Simple Hash Chain (POC for V0.1)

Include a `signature` field at the top level of `process-log.json` that is a SHA-256 hash of the entire events array concatenated with a session-specific salt. This detects any modification to the log.

#### Digital Signatures (Future)

For public verification, the container can include detached signatures using a user-controlled key pair. The META-INF/signatures.xml file would contain:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<signatures>
  <signature file="meta/process-log.json" algorithm="SHA256withRSA">
    base64-encoded-signature-here
  </signature>
</signatures>
```

## Privacy Guarantees

TWFF is designed with privacy as a first-class concern.

### What TWFF Explicitly Does NOT Store

- Individual keystroke content (only aggregated character counts per edit block)
- Raw prompts or full AI responses (only metadata and optional previews)
- Personally identifiable information beyond an anonymized user ID
- Screen recordings or mouse movements

### User Control

All data is generated locally on the user's machine.

- The user decides when and with whom to share the container.
- The user can share only the JSON log (for research) or the full container (for verification).
- The anonymous user ID is user-generated and can be rotated at any time.

### Generating Visualizations

### POC Algorithm

1. Parse the XHTML content into a DOM tree.
2. For each event with position_start and position_end, locate the corresponding text node and character range.
3. Wrap the range with a `<span>` element and add appropriate CSS classes and data-* attributes.
4. Render the annotated XHTML with a legend and tooltips.

### Example output

See figure 1

```html
<p>
    The rapid advancement of artificial intelligence has transformed many aspects of our daily lives.
    <span class="ai-paraphrase" data-tooltip="Paraphrased by ChatGPT on 2023-10-15">From personalized recommendations on streaming platforms to autonomous vehicles</span>,
    AI systems are becoming increasingly integrated into society.
</p>
<style>
.ai-paraphrase {
    background-color: #e8f4fd;
    border-left: 3px solid #3498db;
    padding: 2px 4px;
    position: relative;
}

.ai-paraphrase::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: 100%;
    left: 0;
    background: rgba(0,0,0,0.8);
    color: white;
    padding: 5px 10px;
    border-radius: 4px;
    font-size: 0.8em;
    white-space: nowrap;
    opacity: 0;
    transition: opacity 0.3s;
}

.ai-paraphrase:hover::after {
    opacity: 1;
}
</style>
```

## Browser Extension (TODO)

A browser extension for Google Docs and Overleaf will generate TWFF containers by monitoring edits and capturing AI interactions.

## LMS Integration (TODO)

Plugins for Canvas, Moodle, and other LMS platforms will accept TWFF submissions and display annotated views to instructors.

## Roadmap

|Phase |Components |Timeline|
| ---| ---|--- |
|v0.1 Core | Schema definition, reference implementation (Python), basic visualizer| Q1 2026 |
|v1.0 Tools| Browser extension (Google Docs), improved visualizer, chat transcript | support Q2 2026|
|v1.2 Integration| Canvas plugin, Moodle plugin, validator service| Q3 2026|
|v1.5 Future | Cryptographic signatures, decentralized storage, multi-author support| Q4 2026+|

### TODO

- [x] Schema v1.0 definition

- [ ] Reference implementation (Python / NiceGUI)

- [ ] Browser extension for Google Docs / Overleaf

- [ ] TWFF visualizer

- [ ] LMS integration (Canvas, Moodle)
