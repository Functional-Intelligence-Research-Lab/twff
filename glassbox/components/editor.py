"""
editor.py — Glass Box Editor (NiceGUI / Quasar)

Features:
  - Paste-at-cursor (not append)
  - Quote & cite selection dialog
  - Model selector dropdown (Ollama)
  - Ollama paraphrase / generate / ghost completion
  - Ghost completion (Tab to accept, Esc to dismiss)
  - Command palette hooks
  - Export TWFF + Export PDF
  - Graceful fallback when Ollama is not running
"""
from __future__ import annotations

import asyncio
import os
import sys

import bleach
from components.ollama_client import OllamaClient
from components.pdf_exporter import PDFExporter, _pdf_export_ok
from components.process_log import ANNOTATION_TYPES, ProcessLog
from nicegui import ui


class Editor:
    def __init__(self):
        #  State
        self.content:      str = ""
        self.word_count:   int = 0
        self.char_count:   int = 0
        self.editor_ref        = None

        #  AI ─
        self.ollama        = OllamaClient()
        self.ghost_enabled = True
        self._ghost_timer  = None   # debounce handle

        #  TWFF ─
        self.process_log   = ProcessLog()

        #  Export meta (set via dialog) ─
        self._doc_title   = "Untitled Document"
        self._doc_author  = ""
        self._doc_institution = ""

        #  Preview refs ─
        self.preview_container     = None
        self.preview_html_element  = None

        #  Ollama status label ref (set after header is built)
        self._status_label = None
        self._model_select = None

        #  PDF export availability
        self._weasyprint_available = False
        self._export_pdf_button = None

    #  Helpers ─

    #  Initialise Ollama (called by layout after UI is ready) ─

    async def init_ollama(self) -> None:
        status = await self.ollama.discover()
        if self._status_label:
            if status.available:
                txt = f"● {status.active_model}"
                self._status_label.set_text(txt)
                self._status_label.classes(remove="ollama-offline", add="ollama-online")
                # Populate model selector
                if self._model_select and status.models:
                    self._model_select.options = status.models
                    self._model_select.value   = status.active_model
                    self._model_select.update()
            else:
                self._status_label.set_text("● Ollama offline")
                self._status_label.classes(remove="ollama-online", add="ollama-offline")

    #  Build UI ─

    def create(self) -> None:
        with ui.column().classes("editor-container w-full h-full flex flex-col"):
            self._build_editor()

        self._attach_paste_at_cursor()
        self._attach_selection_capture()
        self._attach_ghost_keyhandler()

        ui.timer(30.0, self._on_checkpoint)

    def build_model_selector(self) -> None:
        """
        Build the Ollama status indicator + model dropdown.
        Called from layout.py after the header row is created.
        """
        with ui.row().classes("items-center gap-2"):
            self._status_label = ui.label("● connecting…").classes(
                "ollama-status ollama-offline"
            )
            self._model_select = ui.select(
                options=[],
                value=None,
                on_change=self._on_model_change,
            ).classes("model-select").props("dense borderless")
            self._model_select.set_visibility(False)  # hide until models load

        # Trigger Ollama discovery after the UI event loop tick
        ui.timer(0.1, self.init_ollama, once=True)

    #  Editor element ─

    def _build_editor(self) -> None:
        toolbar = (
            ':toolbar="['
            "['bold','italic','underline','subscript','superscript'],"
            "['h1','h2','h3'],"
            "['unordered','ordered'],"
            "['blockquote','code'],"
            "['ann-paraphrase','ann-generated','ann-external'],"
            "['export-twff','export-pdf'],"
            ']"'
        )

        self.editor_ref = ui.editor(
            placeholder="Start writing here. Your process is being recorded.",
            value=self._initial_content(),
            on_change=self._on_content_change,
        ).props(toolbar).classes("w-full h-full border-0")

        # Annotation slots
        for ann_key in ("ai_paraphrase", "ai_generated", "external_paste"):
            ann = ANNOTATION_TYPES[ann_key]
            suffix = ann_key.split("_")[1]
            with self.editor_ref.add_slot(f"ann-{suffix}"):
                ui.button(
                    ann["label"],
                    on_click=lambda a=ann: self._run_annotation_ai(a),
                ).props("flat dense").classes("ann-toolbar-btn")

        with self.editor_ref.add_slot("export-twff"):
            ui.button("Export .twff", on_click=self.export_twff).props(
                "flat dense"
            ).classes("ann-toolbar-btn export-btn-twff")

        with self.editor_ref.add_slot("export-pdf"):
            self._export_pdf_button = ui.button(
                "Export PDF", on_click=self.export_pdf
            ).props("flat dense").classes("ann-toolbar-btn export-btn-pdf")
            
            # Check if ANY PDF engine (WeasyPrint or ReportLab) is available
            self._weasyprint_available = _pdf_export_ok()
            if not self._weasyprint_available:
                self._export_pdf_button.enabled = False
                self._export_pdf_button.props(add="disable")
                self._export_pdf_button.tooltip = (
                    "PDF export unavailable. See console: "
                    "python glassbox/setup_weasyprint.py --check"
                )

    # ═
    # PASTE AT CURSOR (not append)
    # ═

    def _attach_paste_at_cursor(self) -> None:
        """
        Intercept paste events. Insert content at cursor position (not end).
        Wraps pasted content in ann-external span and emits gb_paste event.
        """
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
                    let text = cd.getData('text/plain') || '';
                    let html = cd.getData('text/html') || '';

                    // Strip html to plain for logging preview
                    const preview = text.substring(0, 100);

                    // Build annotated span
                    const span = document.createElement('span');
                    span.className = 'ann-external';
                    span.setAttribute('data-tooltip',
                        'Pasted from external source — ' + new Date().toISOString());
                    span.textContent = text;  // use plain text to avoid XSS

                    // Insert at cursor
                    const sel = window.getSelection();
                    if (sel && sel.rangeCount) {
                        const range = sel.getRangeAt(0);
                        range.deleteContents();
                        range.insertNode(span);
                        // Move cursor after inserted span
                        range.setStartAfter(span);
                        range.setEndAfter(span);
                        sel.removeAllRanges();
                        sel.addRange(range);
                    } else {
                        ed.appendChild(span);
                    }

                    // Emit for Python to log
                    window.emitEvent('gb_paste', {
                        length:  text.length,
                        preview: preview
                    });
                });
            }, 700);
        })();
        """)

        def _handle_paste(e) -> None:
            data    = e.args
            length  = data.get("length", 0)
            preview = data.get("preview", "")
            pos     = self.char_count
            self.process_log.log_paste(
                char_count=length,
                position_start=pos,
                position_end=pos + length,
                source="external",
                preview=preview,
            )
            # Sync content state
            ui.run_javascript(
                "window.emitEvent('gb_content_sync', "
                "{html: document.querySelector('.q-editor__content').innerHTML});"
            )
            ui.notify("External paste logged", type="positive", position="top-right")

        ui.on("gb_paste", _handle_paste)

        def _handle_sync(e) -> None:
            html = e.args.get("html", "")
            self._on_content_change({"value": html})

        ui.on("gb_content_sync", _handle_sync)


    # SELECTION CAPTURE (for quote & cite, paraphrase)

    def _attach_selection_capture(self) -> None:
        """Store the current text selection in Python when user selects text."""
        ui.run_javascript("""
        (function() {
            setTimeout(function() {
                const ed = document.querySelector(
                    '.q-editor__content[contenteditable="true"]'
                );
                if (!ed) return;

                document.addEventListener('mouseup', function() {
                    const sel = window.getSelection();
                    if (sel && sel.toString().trim().length > 0) {
                        window.emitEvent('gb_selection', {
                            text: sel.toString().trim()
                        });
                    }
                });
            }, 700);
        })();
        """)

        def _handle_selection(e) -> None:
            self._selected_text = e.args.get("text", "")

        self._selected_text = ""
        ui.on("gb_selection", _handle_selection)

    # ═
    # GHOST COMPLETION (Tab to accept)
    # ═

    def _attach_ghost_keyhandler(self) -> None:
        """
        Listen for Tab key in the editor to trigger / accept ghost completion.
        Escape dismisses the current ghost.
        """
        ui.run_javascript("""
        (function() {
            setTimeout(function() {
                const ed = document.querySelector(
                    '.q-editor__content[contenteditable="true"]'
                );
                if (!ed) return;

                let ghostNode = null;

                function dismissGhost() {
                    if (ghostNode && ghostNode.parentNode) {
                        ghostNode.parentNode.removeChild(ghostNode);
                    }
                    ghostNode = null;
                }

                window._gbInsertGhost = function(text) {
                    dismissGhost();
                    const sel = window.getSelection();
                    if (!sel || !sel.rangeCount) return;
                    const range = sel.getRangeAt(0);
                    ghostNode = document.createElement('span');
                    ghostNode.id = 'gb-ghost';
                    ghostNode.textContent = text;
                    range.insertNode(ghostNode);
                };

                window._gbAcceptGhost = function() {
                    if (!ghostNode) return;
                    // Replace ghost span with plain text node
                    const text = ghostNode.textContent;
                    const parent = ghostNode.parentNode;
                    const textNode = document.createTextNode(text);
                    parent.replaceChild(textNode, ghostNode);
                    ghostNode = null;
                    // Move cursor after accepted text
                    const sel = window.getSelection();
                    const range = document.createRange();
                    range.setStartAfter(textNode);
                    range.collapse(true);
                    sel.removeAllRanges();
                    sel.addRange(range);
                    // Notify Python of acceptance
                    window.emitEvent('gb_ghost_accepted', {text: text});
                    // Sync content
                    window.emitEvent('gb_content_sync',
                        {html: ed.innerHTML});
                };

                ed.addEventListener('keydown', function(e) {
                    if (e.key === 'Tab') {
                        e.preventDefault();
                        if (ghostNode) {
                            window._gbAcceptGhost();
                        } else {
                            // Request new ghost completion
                            window.emitEvent('gb_ghost_request', {
                                context: ed.innerText
                            });
                        }
                    }
                    if (e.key === 'Escape') {
                        dismissGhost();
                    }
                    // Dismiss ghost on any other typing
                    if (e.key !== 'Tab' && e.key !== 'Escape'
                            && !e.ctrlKey && !e.metaKey) {
                        dismissGhost();
                    }
                });
            }, 700);
        })();
        """)

        async def _handle_ghost_request(e) -> None:
            if not self.ghost_enabled:
                return
            context = e.args.get("context", "")
            if len(context.strip()) < 10:
                return
            try:
                if self.ollama.status.available:
                    suggestion = await self.ollama.ghost_completion(context)
                else:
                    suggestion = OllamaClient.fallback_completion(context)
                if suggestion:
                    ui.run_javascript(
                        f"window._gbInsertGhost({repr(suggestion)});"
                    )
            except Exception:
                pass  # Ghost completion is best-effort, never block UI

        async def _handle_ghost_accepted(e) -> None:
            text = e.args.get("text", "")
            if text:
                pos = self.char_count
                self.process_log.log_ai_interaction(
                    interaction_type="completion",
                    model=self.ollama.status.active_model or "rule-based",
                    output_length=len(text),
                    position_start=pos,
                    position_end=pos + len(text),
                    output_preview=text[:50],
                )

        ui.on("gb_ghost_request",  _handle_ghost_request)
        ui.on("gb_ghost_accepted", _handle_ghost_accepted)

    # ═
    # AI TOOLBAR ACTIONS
    # ═

    async def _run_annotation_ai(self, ann: dict) -> None:
        """
        For paraphrase/generate: use Ollama if available, else insert demo fixture.
        For external paste: demo fixture.
        """
        if ann["log_type"] == "ai_interaction":
            if self.ollama.status.available:
                await self._ai_insert(ann)
            else:
                self._demo_insert(ann)
                ui.notify(
                    "Ollama offline — inserted demo text. "
                    "Install from ollama.com for real AI.",
                    type="warning", position="top-right",
                )
        else:
            self._demo_insert(ann)

    async def _ai_insert(self, ann: dict) -> None:
        """Call Ollama and insert annotated result at cursor."""
        notification = ui.notification(
            f"Running {ann['label']}…", spinner=True,
            timeout=None, position="top-right"
        )
        try:
            context = self._strip_html(self.content)[-800:]
            if ann["interaction"] == "paraphrase":
                # Paraphrase the selection if any, else last paragraph
                source = self._selected_text or self._last_paragraph(context)
                result = await self.ollama.paraphrase(source)
            else:
                result = await self.ollama.draft_continuation(context)

            model  = self.ollama.status.active_model or "rule-based"
            ts     = self.process_log.events[-1]["timestamp"] if self.process_log.events else ""
            tooltip = (
                f"{ann['label']} — {model} — "
                f"{ts[:10] if ts else 'now'}"
            )
            self._insert_annotated_at_cursor(result, ann, tooltip)
            pos = self.char_count
            self.process_log.log_ai_interaction(
                interaction_type=ann["interaction"],
                model=model,
                output_length=len(result),
                position_start=pos,
                position_end=pos + len(result),
                output_preview=result[:50],
            )
            ui.notify(f"{ann['label']} complete", type="positive", position="top-right")
        except Exception as exc:
            ui.notify(f"AI error: {exc}", type="negative", position="top-right")
        finally:
            notification.dismiss()

    def _demo_insert(self, ann: dict) -> None:
        fixtures = {
            "ai_paraphrase": "This sentence was rewritten by an AI assistant to improve clarity and flow.",
            "ai_generated":  "This paragraph was drafted entirely by an AI assistant as a demonstration.",
            "external_paste": "This content was pasted from an external source.",
        }
        text = fixtures.get(
            next((k for k, v in ANNOTATION_TYPES.items() if v == ann), ""),
            "Sample annotated content."
        )
        tooltip = f"{ann['label']} — demo"
        self._insert_annotated_at_cursor(text, ann, tooltip)
        pos = self.char_count
        if ann["log_type"] == "ai_interaction":
            self.process_log.log_ai_interaction(
                interaction_type=ann["interaction"],
                model="demo-glass-box",
                output_length=len(text),
                position_start=pos,
                position_end=pos + len(text),
                output_preview=text[:50],
            )

    #  Insert at cursor (not append)

    def _insert_annotated_at_cursor(self, text: str, ann: dict, tooltip: str) -> None:
        """Insert annotated span at current cursor position via JS."""
        css    = ann["css_class"]
        safe_text    = text.replace("'", "\\'").replace("\n", " ")
        safe_tooltip = tooltip.replace("'", "\\'")
        ui.run_javascript(f"""
        (function() {{
            const ed = document.querySelector(
                '.q-editor__content[contenteditable="true"]'
            );
            if (!ed) return;

            const span = document.createElement('span');
            span.className = '{css}';
            span.setAttribute('data-tooltip', '{safe_tooltip}');
            span.textContent = '{safe_text}';

            const sel = window.getSelection();
            if (sel && sel.rangeCount) {{
                const range = sel.getRangeAt(0);
                range.collapse(false);  // collapse to end of selection
                range.insertNode(span);
                range.setStartAfter(span);
                range.collapse(true);
                sel.removeAllRanges();
                sel.addRange(range);
            }} else {{
                ed.appendChild(document.createElement('p')).appendChild(span);
            }}
            // Sync back to Python
            window.emitEvent('gb_content_sync', {{html: ed.innerHTML}});
        }})();
        """)

    # ═
    # COMMAND PALETTE HOOKS
    # ═

    async def cmd_paraphrase_selection(self) -> None:
        ann = ANNOTATION_TYPES["ai_paraphrase"]
        await self._run_annotation_ai(ann)

    async def cmd_continue_writing(self) -> None:
        ann = ANNOTATION_TYPES["ai_generated"]
        await self._run_annotation_ai(ann)

    async def cmd_quote_and_cite(self) -> None:
        """Show a dialog: quote the selection + AI citation suggestion."""
        selection = self._selected_text
        if not selection:
            ui.notify("Select some text first", type="warning", position="top-right")
            return

        with ui.dialog() as dlg, ui.card().classes("post-export-dialog"):
            ui.label("Quote & Cite").classes("dialog-title")
            ui.label(f'Selected: "{selection[:80]}…"').classes("dialog-meta")

            result_label = ui.label("Analysing…").classes("text-sm text-gray-600")
            cite_label   = ui.label("").classes("text-sm mt-2")

            async def _analyse():
                try:
                    if self.ollama.status.available:
                        res = await self.ollama.quote_and_cite(
                            selection, self._strip_html(self.content)
                        )
                        result_label.set_text(f'Quoted: {res.get("quoted", selection)}')
                        needs = res.get("needs_citation", True)
                        suggestion = res.get("suggestion", "")
                        cite_label.set_text(
                            f'{"⚠ Likely needs citation. " if needs else "✓ Looks original. "}'
                            f'{suggestion}'
                        )
                    else:
                        result_label.set_text(f'"{selection}"')
                        cite_label.set_text(
                            "Ollama offline — install for AI citation suggestions."
                        )
                except Exception as exc:
                    result_label.set_text(f"Error: {exc}")

            ui.timer(0.1, _analyse, once=True)

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Insert quoted", on_click=lambda: (
                    self._insert_annotated_at_cursor(
                        f'"{selection}"',
                        ANNOTATION_TYPES["external_paste"],
                        "Quoted passage",
                    ),
                    dlg.close(),
                )).props("flat").classes("gb-btn-primary text-xs")
                ui.button("Close", on_click=dlg.close).props("flat")

        dlg.open()

    def cmd_show_word_count(self) -> None:
        with ui.dialog() as dlg, ui.card().classes("post-export-dialog"):
            ui.label("Document Stats").classes("dialog-title")
            with ui.column().classes("gap-1"):
                ui.label(f"Words:      {self.word_count:,}").classes("dialog-meta")
                ui.label(f"Characters: {self.char_count:,}").classes("dialog-meta")
                ai_count = sum(
                    1 for e in self.process_log.events if e["type"] == "ai_interaction"
                )
                ui.label(f"AI events:  {ai_count}").classes("dialog-meta")
                ui.label(
                    f"Session:    {self.process_log.session_id[:8]}…"
                ).classes("dialog-meta")
            with ui.row().classes("justify-end w-full"):
                ui.button("Close", on_click=dlg.close).props("flat")
        dlg.open()

    def cmd_toggle_ghost(self) -> None:
        self.ghost_enabled = not self.ghost_enabled
        state = "on" if self.ghost_enabled else "off"
        ui.notify(f"Ghost completion {state}", position="top-right")

    def cmd_clear_annotations(self) -> None:
        """Strip all annotation spans from the editor content."""
        ui.run_javascript("""
        (function() {
            const ed = document.querySelector(
                '.q-editor__content[contenteditable="true"]'
            );
            if (!ed) return;
            const spans = ed.querySelectorAll(
                '.ann-paraphrase,.ann-generated,.ann-external,.ann-completion'
            );
            spans.forEach(span => {
                const text = document.createTextNode(span.textContent);
                span.parentNode.replaceChild(text, span);
            });
            window.emitEvent('gb_content_sync', {html: ed.innerHTML});
        })();
        """)
        ui.notify("Annotations cleared", position="top-right")

    # ═
    # EXPORT
    # ═

    def export_twff(self) -> None:
        xhtml      = self._wrap_xhtml(self.editor_ref.value or "")
        twff_bytes = self.process_log.export(xhtml)
        ui.download(twff_bytes, "document.twff")
        ui.notify("TWFF exported", type="positive", position="top-right")
        self._show_export_dialog()

    def export_pdf(self) -> None:
        """Export PDF with annotation highlights and AI usage appendix."""
        self._show_pdf_meta_dialog()

    def _show_pdf_meta_dialog(self) -> None:
        with ui.dialog() as dlg, ui.card().classes("post-export-dialog"):
            ui.label("Export as PDF").classes("dialog-title")
            ui.label("Academic template — A4 with AI usage appendix").classes("dialog-meta")

            title_input  = ui.input("Title", value=self._doc_title).classes("w-full")
            author_input = ui.input("Author (optional)", value=self._doc_author).classes("w-full")
            inst_input   = ui.input("Institution (optional)", value=self._doc_institution).classes("w-full")

            status = ui.label("").classes("text-xs text-gray-500 mt-2")

            async def _do_export() -> None:
                self._doc_title       = title_input.value or "Untitled"
                self._doc_author      = author_input.value or ""
                self._doc_institution = inst_input.value or ""
                status.set_text("Generating PDF…")
                dlg.close()
                try:
                    from components.pdf_exporter import PDFExporter
                    exporter  = PDFExporter(process_log=self.process_log)
                    pdf_bytes = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: exporter.export(
                            html_content=self.editor_ref.value or "",
                            title=self._doc_title,
                            author=self._doc_author,
                            institution=self._doc_institution,
                        )
                    )
                    filename = self._doc_title.replace(" ", "_")[:40] + ".pdf"
                    ui.download(pdf_bytes, filename)
                    ui.notify("PDF exported", type="positive", position="top-right")
                except RuntimeError as exc:
                    ui.notify(str(exc), type="negative", position="top-right")

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Export", on_click=_do_export).classes("gb-btn-primary text-xs")
                ui.button("Cancel", on_click=dlg.close).props("flat")

        dlg.open()

    def _show_export_dialog(self) -> None:
        with ui.dialog() as dlg, ui.card().classes("post-export-dialog"):
            ui.label("Session exported").classes("dialog-title")
            ui.label(
                f"Session {self.process_log.session_id[:8]}… — "
                f"{len(self.process_log.events)} events recorded"
            ).classes("dialog-meta")
            ui.html("""
                <iframe scrolling="no"
                    style="overflow:hidden;width:100%;height:168px;border:none;"
                    data-tally-src="https://tally.so/embed/jaQNE9?hideTitle=1&transparentBackground=1&dynamicHeight=1"
                    loading="lazy" frameborder="0" title="FIRL Newsletter"></iframe>
            """, sanitize=False)
            ui.run_javascript(
                "if (typeof Tally !== 'undefined') { Tally.loadEmbeds(); }"
            )
            with ui.row().classes("w-full justify-end mt-2"):
                ui.button("Close", on_click=dlg.close).props("flat")
        dlg.open()

    # ═
    # MODEL SELECTOR
    # ═

    def _on_model_change(self, e) -> None:
        model = e.value
        if model:
            self.ollama.set_model(model)
            ui.notify(f"Model: {model}", position="top-right", timeout=2000)

    # ═
    # CONTENT CHANGE / STATS
    # ═

    def _on_content_change(self, e) -> None:
        if hasattr(e, "value"):
            self.content = e.value
        elif isinstance(e, dict):
            self.content = e.get("value", "")
        plain            = self._strip_html(self.content)
        self.word_count  = len(plain.split())
        self.char_count  = len(plain)

    def _on_checkpoint(self) -> None:
        self.process_log.log_checkpoint(
            char_count=self.char_count,
            word_count=self.word_count,
            cursor_position=self.char_count,
        )

    # ═
    # HELPERS
    # ═

    @staticmethod
    def _strip_html(html: str) -> str:
        return bleach.clean(html, tags=[], strip=True)

    @staticmethod
    def _last_paragraph(text: str) -> str:
        """Return the last non-empty paragraph of plain text."""
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        return paragraphs[-1] if paragraphs else text[-500:]

    @staticmethod
    def _wrap_xhtml(body_html: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            "<head><title>Glass Box Document</title></head>\n"
            f"<body>\n{body_html}\n</body>\n"
            "</html>"
        )

    @staticmethod
    def _initial_content() -> str:
        return """
<h1>Welcome to Glass Box</h1>
<p>This editor records your writing process as a TWFF session. Every edit, paste,
and AI interaction is logged locally — nothing leaves your machine until you export.</p>
<p>Press <code>Ctrl+K</code> to open the command palette. Press <code>Tab</code>
to accept a ghost completion suggestion. Use the toolbar to paraphrase or generate
text with AI.</p>
<blockquote><p>Verifiable Effort — not probabilistic detection.</p></blockquote>
"""
