"""
layout.py — Glass Box application layout

Composed of four independent sections: header, legend, editor area, footer.
Legend is driven by ANNOTATION_TYPES — one source of truth.
"""
from components.editor import Editor
from components.process_log import ANNOTATION_TYPES
from nicegui import ui


def create_layout():
    editor = Editor()

    _create_header(editor)
    _create_legend()
    _create_editor_area(editor)
    _create_footer(editor)


# Sections

def _create_header(editor: Editor):
    with ui.header().classes("gb-header w-full px-4"):
        with ui.row().classes("w-full items-center justify-between"):
            # Brand
            with ui.row().classes("items-center gap-2"):
                ui.image("backend/image.png").classes("h-5 w-5 object-contain")
                with ui.column().classes("gap-0"):
                    ui.label("Glass Box").classes("gb-brand-name")
                    ui.label("by FIRL").classes("gb-brand-sub")

            # Session indicator — live event counter
            with ui.row().classes("items-center gap-3"):
                ui.label("●").classes("gb-recording-dot")
                ui.label().bind_text_from(
                    editor.process_log, "events",
                    lambda evts: f"{len(evts)} events"
                ).classes("gb-event-count")

            # Header actions
            with ui.row().classes("items-center gap-1"):
                ui.button(
                    "Export .twff",
                    icon="download",
                    on_click=editor.export_twff,
                ).props("flat dense").classes("gb-btn-primary")


def _create_legend():
    """Legend driven by ANNOTATION_TYPES registry"""
    with ui.row().classes("gb-legend w-full px-4 py-2"):
        ui.label("Process log:").classes("gb-legend-title")
        for ann in ANNOTATION_TYPES.values():
            with ui.row().classes("items-center gap-1"):
                ui.label("").classes(f"gb-legend-swatch {ann['css_class']}-swatch")
                ui.label(ann["label"]).classes("gb-legend-label")


def _create_editor_area(editor: Editor):
    with ui.column().classes("w-full flex-1 min-h-0 overflow-hidden"):
        with ui.column().classes("h-full min-h-0 w-full"):
            editor.create()


def _create_footer(editor: Editor):
    with ui.footer().classes("gb-footer w-full px-4"):
        with ui.row().classes("w-full items-center justify-between"):
            # Status
            with ui.row().classes("items-center gap-2"):
                ui.icon("check_circle", size="12px").classes("text-green-500")
                ui.label("Recording").classes("gb-footer-text")
                ui.label("·").classes("gb-footer-sep")
                ui.label("Local-first · No cloud").classes("gb-footer-text")

            # Word / char counts
            with ui.row().classes("items-center gap-3"):
                ui.label().bind_text_from(
                    editor, "word_count",
                    lambda w: f"{w:,} words"
                ).classes("gb-footer-text")
                ui.label().bind_text_from(
                    editor, "char_count",
                    lambda c: f"{c:,} chars"
                ).classes("gb-footer-text")

            # Session ID (truncated) for transparency
            with ui.row().classes("items-center gap-1"):
                ui.label("Session:").classes("gb-footer-text")
                from components.editor import (
                    Editor as _E,  # avoid circular at module level
                )

                # We access through editor instance
                ui.label(editor.process_log.session_id[:8] + "…").classes("gb-footer-mono")
