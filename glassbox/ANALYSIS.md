# Glass Box / TWFF — Critical MVP Analysis
*Internal document for FIRL team*

---

## Repository Structure: Current vs. Proposed

### Current (monolithic)
```
backend/
├── app.py
├── css/theme.css
└── components/
    ├── editor.py
    └── layout.py
```

### Proposed (TWFF monorepo)
```
twff/
├── spec/                        # The open standard
│   ├── SPEC.md
│   ├── schema/
│   │   ├── process-log.schema.json
│   │   └── manifest.schema.json
│   └── examples/
├── glassbox/                    # The reference implementation
│   ├── backend/
│   │   ├── app.py
│   │   ├── css/
│   │   │   ├── theme.css        # Axion-vibe theme
│   │   │   └── annotations.css  # Annotation-specific styles (separated)
│   │   └── components/
│   │       ├── editor.py
│   │       ├── layout.py
│   │       └── process_log.py   # Extracted: TWFF logging (should be its own module)
│   └── docs/
└── README.md
```

**Why this matters:** The spec and the app are currently tangled. The README is the spec.
That makes it hard to version them independently and confuses contributors — is this a
standard or a product? It's both, and they need different governance.

---

## Code-Level Critique

### `editor.py` — What's working
- Session UUID and ISO 8601 timestamps: correct per spec
- `_log_event()` is clean and spec-compliant
- ZIP container structure matches TWFF spec exactly
- Paste interception via JS `clipboardData` is the right approach
- `bleach` sanitization on preview output: good security practice
- Scroll sync JS: non-trivial, works

### `editor.py` — Problems

**1. TWFF logging is embedded in the UI class.**
`Editor` does too much: it's a UI component, a TWFF session recorder, a file exporter,
and an event bus. The `_log_event`, `_log_checkpoint`, and `export_twff` methods belong
in a separate `ProcessLog` class. This is critical because the browser extension and
LMS plugin (both on the roadmap) will need the same logging logic without the NiceGUI UI.

```python
# Current — coupled
class Editor:
    def _log_event(self, ...): ...     # should be ProcessLog
    def export_twff(self): ...         # should be ProcessLog.export()
```

**2. `user_id` is hardcoded as `'anonymous-user'`.**
The spec says it should be user-generated and rotatable. Even the demo should generate
a random ephemeral ID. This is a 1-line fix but signals the spec hasn't been dogfooded.

**3. `_strip_html` uses a raw regex.**
`re.sub(clean, '', html)` on `<.*?>` will break on nested tags and multiline HTML.
Use `bleach.clean(html, tags=[], strip=True)` which is already imported.

**4. The scroll sync `_attach_scroll_sync` queries `[role="region"]` for the preview.**
This is fragile — it matches any ARIA region on the page. If NiceGUI adds any other
region element (dialog, notification), the scroll sync breaks silently.

**5. `simulate_ai_*` methods are demo scaffolding committed as production code.**
They insert hardcoded strings with hardcoded dates ("2026-02-19"). These are fine for
the demo but shouldn't live in the main `Editor` class. Move to `demo_fixtures.py`.

**6. `editor_ref.value` mutation for content insertion.**
When `_insert_with_span` does `self.editor_ref.value = new_content`, it triggers
`on_change` which calls `_handle_content_change`, which may trigger `update_preview`,
creating a call chain that isn't guarded. Under fast input this could stack.

**7. The newsletter dialog is inside `export_twff`.**
Side effect inside a file export function. This should be a separate `post_export_hook`
or event so it can be toggled off in non-demo deployments.

### `layout.py` — Problems

**1. Commented-out splitter code is 60+ lines in production.**
The `# Editor Container with Splitter` block is dead code. It's in production and
adds cognitive load. If the splitter feature is deferred, delete it; if it's planned,
move it to a feature branch.

**2. Legend is a static hardcoded row, not driven by data.**
The annotation colors (blue/green/yellow) are defined in three places: `layout.py` (legend),
`theme.css` (`.ai-paraphrase`, `.ai-generated`, `.external-source`), and `editor.py`
(the span class strings). One source of truth needed — a `ANNOTATION_TYPES` dict that
drives all three.

**3. `create_layout()` is a single long function.**
Should be split: `create_header()`, `create_legend()`, `create_editor_area()`, `create_footer()`.
Each composable independently, testable independently.

### `theme.css` — What's working
- Crimson Text for body / Atkinson for UI: correct font pairing
- The Quasar override strategy (`!important` bombing) is necessary given NiceGUI constraints
- Editor content as "sheet of paper" with max-width 8.5in and box-shadow: nice
- Responsive toolbar hiding at 768px/480px: thoughtful

### `theme.css` — Problems

**1. Two `:root` blocks.**
Lines 4–43 define one set of tokens (the warm/earth palette). Lines 51–84 define
a completely different set (blue/grey). The first block appears to be from an earlier
design iteration and is never used. It adds ~40 lines of noise and conflates the
warm aesthetic tokens with the current blue-neutral ones.

**2. Annotation styles are defined twice.**
`.ai-paraphrase` appears at line 592 (preview styles) AND line 799 (inline span styles),
with different property values. The first uses `#3498db`, the second uses `#3b82f6`.
They should be one definition in a separate `annotations.css` file.

**3. The `!important` count is ~180+.**
This is a known NiceGUI/Quasar tax but there's unnecessary escalation. Several rules
that don't need `!important` have it because earlier rules did. Audit needed.

**4. `.q-editor__content` has `margin-bottom: 80px` hardcoded.**
This magic number accounts for the footer but breaks if the footer height changes.
Should be a CSS variable `--footer-height: 28px` with a `calc()`.

**5. The `Inter` font referenced in `app.py`'s inline `.prose` styles is never imported.**
The Google Fonts import only loads Crimson Text and Atkinson Hyperlegible. `Inter`
falls back to `Segoe UI / Roboto`. Minor but inconsistent with the font strategy.

**6. Color token naming collides with semantic usage.**
`--primary: #3b82f6` is defined but then `#3b82f6` and `#3498db` appear as hardcoded
hex strings throughout. The token isn't used; the hex values are. Classic.

---

## Product / UX Critique

**The "Glass Box" concept is strong; the UI doesn't communicate it.**
The current interface looks like VS Code or Notion. That's competent but not distinctive.
The *transparency* metaphor — a writing process you can see through — deserves visual
treatment. The annotation highlights (blue/green/yellow) are the most important UI
element in the entire product and they're rendered as generic Bootstrap-ish spans
that most users will ignore.

**The toolbar exposes TWFF internals as toolbar buttons.**
"Paraphrase | Generate | Paste External" as toolbar buttons means users have to
manually declare their AI use. That's backwards. The real value is *automatic*
detection and logging — the paste interception already does this for paste events.
The manual buttons should be secondary, not primary toolbar items.

**Export TWFF is the primary CTA, but it's buried in the header.**
A first-time user has no idea what a `.twff` file is or why they'd want one. The
export needs to be preceded by a moment of explanation — "your writing session is
being recorded, here's what's in the log."

**The demo has no onboarding.**
Users land on a blank(ish) editor. There's no explanation of what's being tracked,
no indication the session has started, no visual feedback that the process log is
growing. The audit trail — the whole point — is invisible until export.

**Opportunity: a live process log panel.**
A collapsible sidebar showing the real-time event log as it grows would be the
killer demo feature. Every paste, every simulated AI interaction would appear as
a line item. Users would understand immediately what they're producing.

---

## What to build next (prioritized)

1. **Extract `ProcessLog` class** — decouples logging from UI, enables reuse
2. **Live event log panel** — makes the product self-explanatory  
3. **Fix the duplicate CSS / two `:root` blocks** — then apply Axion theme
4. **Single `ANNOTATION_TYPES` source of truth** — drives legend, CSS, and editor
5. **Rename repo to `twff` monorepo** — separate `spec/` and `glassbox/` clearly
6. **Remove dead splitter code** — clean repo before new contributors arrive
