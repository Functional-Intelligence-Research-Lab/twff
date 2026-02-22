"""
app.py — Glass Box entry point

Wires static files, fonts, and the layout. No business logic here.
"""
import os
import sys

# Ensure components are importable
sys.path.insert(0, os.path.dirname(__file__))

from components.layout import create_layout
from nicegui import app, ui

# Serve static CSS
app.add_static_files("/css", os.path.join(os.path.dirname(__file__), "css"))


@ui.page("/")
async def main():
    # ── Fonts
    ui.add_head_html("""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@phosphor-icons/web@2.1.1/src/regular/style.css"/>
    """)

    # Viewport
    ui.add_head_html(
        "<meta name='viewport' content='width=device-width, initial-scale=1, maximum-scale=1'>"
    )

    # TODO: Tally (newsletter embed)
    ui.add_head_html('<script async src="https://tally.so/embed.js"></script>')

    # Theme CSS
    # TODO:  theme switching and buddle separate CSS files
    with open(os.path.join(os.path.dirname(__file__), "css", "theme.css")) as f:
        ui.add_css(f.read())

    # NiceGUI content area reset
    ui.add_css("""
        .nicegui-content {
            height: 100vh !important;
            width: 100vw !important;
            padding: 0 !important;
            margin: 0 !important;
            background: transparent !important;
            overflow: hidden !important;
        }
    """)

    create_layout()


if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.getenv("PORT", 8080))
    ui.run(
        title="Glass Box — TWFF",
        favicon=os.path.join(os.path.dirname(__file__), "glassbox_logo.png"),
        dark=False,
        reload=False, # ? switch to True for development, but it causes issues with multiprocessing on Windows
        host="0.0.0.0",
        port=port,
    )
