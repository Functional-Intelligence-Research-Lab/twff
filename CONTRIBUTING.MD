# Contributing

TWFF is an open standard. We welcome contributions from researchers, developers, and educators.

How to Contribute

1. Discuss: Open an issue to propose changes or additions to the spec.
2. Implement: Build tools, libraries, or integrations.
3. Test: Use TWFF in your own research or classroom.
4. Feedback: Share your experience and suggest improvements.


## Repo structure

```text
twff/
├── README.md                 
├── LICENSE                   # GNU v2 License
├── spec/
│   ├── v1.0/
│   │   ├── README.md          # Version-specific spec
│   │   ├── schema.json        # JSON Schema
│   │   └── examples/
│   │       ├── basic/
│   │       │   ├── document.xhtml
│   │       │   ├── process-log.json
│   │       │   └── sample.twff
│   │       └── full/
│   │           ├── document.xhtml
│   │           ├── process-log.json
│   │           ├── chat-transcript.json
│   │           └── full.twff
├── implementations/
│   ├── python/                # Reference implementation
│   │   ├── README.md
│   │   ├── src/
│   │   └── tests/
│   └── js/                    # {Java|Type}Script libraries (future)
├── tools/
│   ├── visualizer/             # Web-based TWFF viewer
│   └── validator/              # TWFF validation tool
└── docs/
    ├── integration-guide.md    # LMS integration
    ├── research-usage.md       # Guide for researchers
    └── visualization.md        # How to build viewers
```