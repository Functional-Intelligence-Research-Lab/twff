"""
layout.py — Glass Box application layout

Header: brand | recording indicator | Ollama status + model selector | export buttons
Legend: annotation key (driven by ANNOTATION_TYPES)
Editor: full-height editor area
Footer: status | word/char counts | session ID | Ctrl+K hint
"""
from __future__ import annotations

from components.command_palette import CommandPalette
from components.editor import Editor
from components.process_log import ANNOTATION_TYPES
from nicegui import ui


def create_layout() -> None:
    editor  = Editor()
    palette = CommandPalette(editor)

    _create_header(editor, palette)
    _create_legend()
    _create_editor_area(editor)
    _create_footer(editor)

    # Command palette dialog (must be built after page elements exist)
    palette.build()


#  Sections

def _create_header(editor: Editor, palette: CommandPalette) -> None:
    with ui.header().classes("gb-header w-full"):
        with ui.row().classes("w-full items-center justify-between h-full px-3"):

            #  Left: brand
            with ui.row().classes("items-center gap-2"):
                ui.image("image.png").classes("h-5 w-5 object-contain")
                with ui.column().classes("gap-0 leading-none"):
                    ui.label("Glass Box").classes("gb-brand-name")
                    ui.label("by FIRL").classes("gb-brand-sub")

            #  Centre: recording pulse + event count
            with ui.row().classes("items-center gap-2"):
                ui.label("●").classes("gb-recording-dot")
                ui.label().bind_text_from(
                    editor.process_log, "events",
                    lambda evts: f"{len(evts)} events"
                ).classes("gb-event-count")

            #  Right: Ollama status / model selector + exports
            with ui.row().classes("items-center gap-2"):
                # Ollama status + model dropdown (built by editor)
                editor.build_model_selector()

                ui.separator().props("vertical").classes("h-5 opacity-20")

                # Command palette trigger button
                ui.button(
                    icon="terminal",
                    on_click=palette.open,
                ).props("flat dense").classes("gb-icon-btn").tooltip("Command palette  Ctrl+K")

                ui.separator().props("vertical").classes("h-5 opacity-20")

                ui.button(
                    "Export .twff",
                    icon="folder_zip",
                    on_click=editor.export_twff,
                ).props("flat dense").classes("gb-btn-secondary")

                ui.button(
                    "PDF",
                    icon="picture_as_pdf",
                    on_click=editor.export_pdf,
                ).props("flat dense").classes("gb-btn-primary")


def _create_legend() -> None:
    """Legend driven by ANNOTATION_TYPES — one source of truth."""
    with ui.row().classes("gb-legend w-full"):
        ui.label("Process log:").classes("gb-legend-title")

        for ann in ANNOTATION_TYPES.values():
            with ui.row().classes("items-center gap-1"):
                ui.element("span").classes(
                    f"gb-legend-swatch {ann['css_class']}-swatch"
                )
                ui.label(ann["label"]).classes("gb-legend-label")

        # Spacer
        ui.element("div").classes("flex-1")

        # Ghost completion indicator
        ui.label("Tab = ghost completion").classes("gb-legend-hint")


def _create_editor_area(editor: Editor) -> None:
    with ui.column().classes("w-full flex-1 min-h-0 overflow-hidden"):
        editor.create()


def _create_footer(editor: Editor) -> None:
    with ui.footer().classes("gb-footer w-full"):
        with ui.row().classes("w-full items-center justify-between h-full px-3"):

            # Left: status
            with ui.row().classes("items-center gap-2"):
                ui.icon("circle", size="10px").classes("text-green-500")
                ui.label("Recording · Local-first").classes("gb-footer-text")

            # Centre: stats
            with ui.row().classes("items-center gap-3"):
                ui.label().bind_text_from(
                    editor, "word_count", lambda w: f"{w:,} words"
                ).classes("gb-footer-text")
                ui.label("·").classes("gb-footer-sep")
                ui.label().bind_text_from(
                    editor, "char_count", lambda c: f"{c:,} chars"
                ).classes("gb-footer-text")

            # Right: session + shortcut hint
            with ui.row().classes("items-center gap-3"):
                ui.label(
                    editor.process_log.session_id[:8] + "…"
                ).classes("gb-footer-mono")
                ui.label("Ctrl+K").classes("gb-kbd-hint")
