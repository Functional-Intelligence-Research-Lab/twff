"""
editor.py — Glass Box WYSIWYG Editor component (NiceGUI / Quasar)

UI responsibilities only. All TWFF session recording is delegated to ProcessLog.
"""
import re

import bleach
from components.process_log import ANNOTATION_TYPES, ProcessLog
from nicegui import ui


class Editor:
    def __init__(self):
        # State
        self.content: str = ""
        self.word_count: int = 0
        self.char_count: int = 0
        self.editor_ref = None

        # TWFF session
        self.process_log = ProcessLog()  # ephemeral anon user_id auto-generated

        # Preview / layout refs (set by layout.py)
        self.preview_container = None
        self.preview_html_element = None

    # Public: build UI

    def create(self):
        """Render the editor column."""
        with ui.column().classes("editor-container w-full h-full flex flex-col"):
            self._build_editor()

        self._attach_paste_interception()

        # Checkpoint every 30s (less noisy than 10s)
        ui.timer(30.0, self._on_checkpoint)

    # ── Editor construction

    def _build_editor(self):
        toolbar_config = (
            ':toolbar="['
            "['bold', 'italic', 'underline', 'subscript', 'superscript'],"
            "['h1', 'h2', 'h3'],"
            "['unordered', 'ordered'],"
            "['blockquote', 'code'],"
            "['ann-paraphrase', 'ann-generated', 'ann-external'],"
            "['export'],"
            ']"'
        )

        self.editor_ref = ui.editor(
            placeholder="Start writing here. Your process is being recorded.",
            value=self._initial_content(),
            on_change=self._on_content_change,
        ).props(toolbar_config).classes("w-full h-full border-0")

        # Annotation toolbar slots — driven by ANNOTATION_TYPES registry
        for ann_key in ("ai_paraphrase", "ai_generated", "external_paste"):
            ann = ANNOTATION_TYPES[ann_key]
            with self.editor_ref.add_slot(f"ann-{ann_key.split('_')[1]}"):
                ui.button(
                    ann["label"],
                    on_click=lambda a=ann: self._insert_annotation_demo(a),
                ).props("flat dense").classes("ann-toolbar-btn")

        with self.editor_ref.add_slot("export"):
            ui.button("Export .twff", on_click=self.export_twff).props(
                "flat dense"
            ).classes("ann-toolbar-btn export-btn")

    # Paste interception

    def _attach_paste_interception(self):
        ui.run_javascript("""
            (function() {
                setTimeout(function() {
                    const ed = document.querySelector(
                        '.q-editor__content[contenteditable="true"]'
                    );
                    if (!ed) return;
                    ed.addEventListener('paste', function(e) {
                        e.preventDefault();
                        const cd = e.clipboardData || window.clipboardData;
                        const text = cd.getData('text/html') || cd.getData('text/plain');
                        if (text && text.length > 0) {
                            window.emitEvent('gb_paste', {
                                length: text.length,
                                content: text,
                                preview: text.substring(0, 100)
                            });
                        }
                    });
                }, 600);
            })();
        """)

        def _handle_paste(e):
            data = e.args
            text = data.get("content", "")
            length = data.get("length", 0)
            preview = data.get("preview", "")
            self._insert_annotated(
                text,
                ANNOTATION_TYPES["external_paste"],
                "Pasted from external source",
            )
            # Log via ProcessLog
            pos = len(self.content)
            self.process_log.log_paste(
                char_count=length,
                position_start=pos,
                position_end=pos + length,
                source="external",
                preview=preview,
            )
            ui.notify("External paste logged", type="positive", position="top-right")

        ui.on("gb_paste", _handle_paste)

    # Annotation insertion

    def _insert_annotated(self, text: str, ann: dict, tooltip: str):
        """Wrap text in an annotation span and append to editor."""
        css = ann["css_class"]
        span = f'<p><span class="{css}" data-tooltip="{tooltip}">{text}</span></p>'
        new_content = (self.editor_ref.value or "") + span
        self.editor_ref.value = new_content
        self._on_content_change({"value": new_content})
        ui.timer(0.1, self._move_cursor_to_end, once=True)

    def _insert_annotation_demo(self, ann: dict):
        """Demo insertion — simulates an AI or external event with fixture text."""
        fixtures = {
            "ann-paraphrase": "This sentence was rewritten by an AI assistant to improve clarity and flow.",
            "ann-generated":  "This paragraph was drafted entirely by an AI assistant as a demonstration of the logging system.",
            "ann-external":   "This content was pasted from an external source such as a website or document.",
        }
        css = ann["css_class"]
        text = fixtures.get(css, "Sample annotated content.")
        tooltip = f"{ann['label']} — {ann['description']}"
        self._insert_annotated(text, ann, tooltip)

        pos = len(self.content)
        if ann["log_type"] == "ai_interaction":
            self.process_log.log_ai_interaction(
                interaction_type=ann["interaction"],
                model="demo-glass-box",
                output_length=len(text),
                position_start=pos,
                position_end=pos + len(text),
                output_preview=text[:50],
            )
        else:
            self.process_log.log_paste(
                char_count=len(text),
                position_start=pos,
                position_end=pos + len(text),
            )
        ui.notify(f"{ann['label']} logged", type="positive", position="top-right")

    # Export

    def export_twff(self):
        xhtml = self._wrap_xhtml(self.editor_ref.value or "")
        twff_bytes = self.process_log.export(xhtml)
        ui.download(twff_bytes, "document.twff")
        ui.notify("TWFF container exported", type="positive", position="top-right")
        self._show_post_export_dialog()

    def _show_post_export_dialog(self):
        with ui.dialog() as dialog, ui.card().classes("post-export-dialog"):
            ui.label("Session exported").classes("dialog-title")
            ui.label(
                f"Session {self.process_log.session_id[:8]}… — "
                f"{len(self.process_log.events)} events recorded"
            ).classes("dialog-meta")
            ui.html("""
                <iframe scrolling="no"
                    style="overflow:hidden;width:100%;height:168px;border:none;"
                    data-tally-src="https://tally.so/embed/jaQNE9?hideTitle=1&transparentBackground=1&dynamicHeight=1"
                    loading="lazy" frameborder="0"
                    title="FIRL Newsletter"></iframe>
            """, sanitize=False)
            ui.run_javascript("""
                if (typeof Tally !== 'undefined') { Tally.loadEmbeds(); }
            """)
            with ui.row().classes("w-full justify-end mt-2"):
                ui.button("Close", on_click=dialog.close).props("flat")
        dialog.open()

    # Content change handler

    def _on_content_change(self, e):
        if hasattr(e, "value"):
            self.content = e.value
        elif isinstance(e, dict):
            self.content = e.get("value", "")

        plain = self._strip_html(self.content)
        words = plain.split()
        self.word_count = len(words)
        self.char_count = len(plain)

    def _on_checkpoint(self):
        self.process_log.log_checkpoint(
            char_count=self.char_count,
            word_count=self.word_count,
            cursor_position=len(self.content),
        )

    # Preview

    def update_preview(self):
        if not (self.preview_container and self.editor_ref):
            return
        allowed_tags = [
            "h1","h2","h3","p","br","ul","ol","li","blockquote","pre","code",
            "strong","em","u","s","a","img","div","span",
        ]
        allowed_attrs = {
            "a":    ["href", "title", "target"],
            "img":  ["src", "alt", "width", "height"],
            "div":  ["class"],
            "span": ["class", "data-tooltip"],
        }
        sanitized = bleach.clean(
            self.editor_ref.value or "",
            tags=allowed_tags,
            attributes=allowed_attrs,
            strip=True,
        )
        if self.preview_html_element is not None:
            self.preview_html_element.set_content(sanitized)
        else:
            self.preview_container.clear()
            with self.preview_container:
                self.preview_html_element = ui.html(sanitized, sanitize=False)

    # Helpers

    def _move_cursor_to_end(self):
        ui.run_javascript("""
            (function() {
                const ed = document.querySelector(
                    '.q-editor__content[contenteditable="true"]'
                );
                if (!ed) return;
                const r = document.createRange();
                const s = window.getSelection();
                r.selectNodeContents(ed);
                r.collapse(false);
                s.removeAllRanges();
                s.addRange(r);
                ed.focus();
            })();
        """)

    @staticmethod
    def _strip_html(html: str) -> str:
        # Use bleach (already imported) rather than raw regex
        return bleach.clean(html, tags=[], strip=True)

    @staticmethod
    def _wrap_xhtml(body_html: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            "<head>\n"
            "  <title>Glass Box Document</title>\n"
            "</head>\n"
            f"<body>\n{body_html}\n</body>\n"
            "</html>"
        )

    @staticmethod
    def _initial_content() -> str:
        return """
<h1>Welcome to Glass Box</h1>
<p>This editor records your writing process as a TWFF (Tracked Writing File Format)
session. Every edit, paste, and AI interaction is logged locally — nothing leaves
your browser until you choose to export.</p>
<p>Use the toolbar to simulate AI paraphrase, generation, or external paste events.
When you export, a <code>.twff</code> container is produced containing your document
and a cryptographically-signed process log.</p>
<blockquote>
  <p>Verifiable Effort — not probabilistic detection.</p>
</blockquote>
"""
