"""
command_palette.py — Glass Box Command Palette (Ctrl+K / Cmd+K)
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from nicegui import ui

if TYPE_CHECKING:
    from components.editor import Editor

def _cmd(label: str, icon: str, group: str, shortcut: str = "") -> dict:
    return {"label": label, "icon": icon, "group": group, "shortcut": shortcut}

ALL_COMMANDS: list[dict] = [
    _cmd("Paraphrase selection",     "auto_fix_high",        "AI",     "Alt+P"),
    _cmd("Continue writing",         "arrow_forward",        "AI",     "Alt+C"),
    _cmd("Quote & cite selection",   "format_quote",         "AI",     "Alt+Q"),
    _cmd("Improve clarity",          "spellcheck",           "AI"),
    _cmd("Export as .twff",          "folder_zip",           "Export", "Ctrl+S"),
    _cmd("Export as PDF",            "picture_as_pdf",       "Export"),
    _cmd("Word count",               "format_list_numbered", "View"),
    _cmd("Toggle ghost completion",  "auto_awesome",         "View",   "Tab"),
    _cmd("Clear annotations",        "clear_all",            "Edit"),
]

class CommandPalette:
    def __init__(self, editor: "Editor"):
        self._editor = editor
        self._dialog = None
        self._input  = None
        self._results_container = None
        self._filtered = list(ALL_COMMANDS)

    def build(self) -> None:
        with ui.dialog().props("seamless position='top'") as self._dialog:
            with ui.card().classes("cp-card"):
                with ui.row().classes("cp-search-row items-center w-full gap-2"):
                    ui.icon("search", size="18px").classes("cp-search-icon")
                    self._input = (
                        ui.input(placeholder="Type a command…", on_change=self._on_query)
                        .classes("cp-search-input flex-1")
                        .props("borderless autofocus")
                    )
                ui.separator().classes("my-0")
                self._results_container = ui.column().classes("cp-results w-full")
                self._render_results()
        ui.keyboard(on_key=self._on_key)

    def open(self) -> None:
        if not self._dialog:
            return
        self._filtered = list(ALL_COMMANDS)
        if self._input:
            self._input.set_value("")
        self._render_results()
        self._dialog.open()

    def close(self) -> None:
        if self._dialog:
            self._dialog.close()

    def _on_query(self, e) -> None:
        q = (e.value or "").lower()
        self._filtered = (
            [c for c in ALL_COMMANDS if q in c["label"].lower()] if q
            else list(ALL_COMMANDS)
        )
        self._render_results()

    def _render_results(self) -> None:
        self._results_container.clear()
        if not self._filtered:
            with self._results_container:
                ui.label("No commands found").classes("cp-empty")
            return
        groups: dict[str, list[dict]] = {}
        for cmd in self._filtered:
            groups.setdefault(cmd["group"], []).append(cmd)
        with self._results_container:
            for group_name, cmds in groups.items():
                ui.label(group_name).classes("cp-group-label")
                for cmd in cmds:
                    self._render_row(cmd)

    def _render_row(self, cmd: dict) -> None:
        def _execute(c=cmd):
            self.close()
            self._dispatch(c["label"])
        with ui.row().classes("cp-cmd-row items-center w-full cursor-pointer").on("click", _execute):
            ui.icon(cmd["icon"], size="16px").classes("cp-cmd-icon")
            ui.label(cmd["label"]).classes("cp-cmd-label flex-1")
            if cmd.get("shortcut"):
                ui.label(cmd["shortcut"]).classes("cp-cmd-shortcut")

    def _dispatch(self, label: str) -> None:
        ed = self._editor
        routes: dict[str, Callable] = {
            "Paraphrase selection":    ed.cmd_paraphrase_selection,
            "Continue writing":        ed.cmd_continue_writing,
            "Quote & cite selection":  ed.cmd_quote_and_cite,
            "Improve clarity":         ed.cmd_paraphrase_selection,
            "Export as .twff":         ed.export_twff,
            "Export as PDF":           ed.export_pdf,
            "Word count":              ed.cmd_show_word_count,
            "Toggle ghost completion": ed.cmd_toggle_ghost,
            "Clear annotations":       ed.cmd_clear_annotations,
        }
        fn = routes.get(label)
        if fn:
            ui.timer(0.05, fn, once=True)
        else:
            ui.notify(f"'{label}' — coming soon", type="info", position="top-right")

    def _on_key(self, e) -> None:
        if e.action.keydown:
            if e.key == "k" and (e.modifiers.ctrl or e.modifiers.meta):
                self.open()
            elif e.key == "Escape":
                self.close()
