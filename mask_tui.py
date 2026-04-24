#!/usr/bin/env python3
"""TUI for mask.py — interactive file browser and menu-driven interface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Button, Checkbox, DirectoryTree, Footer, Header,
    Input, Label, Select, Static,
)

from mask import generate_tiling_mask, apply_mask_to_image


# ── Data ──────────────────────────────────────────────────────────────────────

@dataclass
class MaskParams:
    mode: str = "a"
    input_path: str = ""
    output_path: str = ""
    mask_file: str = ""
    grid: str = "square"
    shape: str = "circle"
    size: float = 40.0
    spacing: float = 90.0
    width: Optional[int] = None
    height: Optional[int] = None
    offset_x: float = 0.0
    offset_y: float = 0.0
    tri_orientation: str = "alternating"
    tri_rotation: float = 0.0
    mask_only: bool = False


# ── File Browser Modal ────────────────────────────────────────────────────────

class FileBrowserModal(ModalScreen):
    """Modal file browser. Dismisses with the selected path string or None."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    CSS = """
    FileBrowserModal { align: center middle; }
    #dialog {
        width: 70%;
        height: 75%;
        border: thick $primary;
        background: $surface;
        padding: 1;
        layout: vertical;
    }
    #dialog Label { height: 1; margin-bottom: 1; }
    #browser-path { margin-bottom: 1; }
    #tree { height: 1fr; border: round $primary-darken-2; }
    #browser-btns { height: auto; align: right middle; margin-top: 1; }
    """

    def __init__(self, start_path: str = ".") -> None:
        super().__init__()
        resolved = Path(start_path).resolve()
        self._start = str(resolved if resolved.is_dir() else resolved.parent)

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Select a file:")
            yield Input(id="browser-path", value=self._start)
            yield DirectoryTree(self._start, id="tree")
            with Horizontal(id="browser-btns"):
                yield Button("Confirm", id="confirm", variant="primary")
                yield Button("Cancel", id="cancel-btn")

    @on(DirectoryTree.FileSelected, "#tree")
    def _file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.query_one("#browser-path", Input).value = str(event.path)

    @on(Button.Pressed, "#confirm")
    def _confirm(self) -> None:
        path = self.query_one("#browser-path", Input).value.strip()
        self.dismiss(path or None)

    @on(Button.Pressed, "#cancel-btn")
    def _cancel_btn(self) -> None:
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


# ── Preview widget ────────────────────────────────────────────────────────────

def _mask_to_blocks(mask_img: Image.Image, cols: int, rows: int) -> Text:
    """Render a grayscale PIL mask as Unicode half-block characters."""
    img = mask_img.resize((cols, rows * 2), Image.LANCZOS)
    px = np.array(img)
    text = Text(no_wrap=True, overflow="fold")
    for r in range(rows):
        top = px[r * 2]
        bot = px[r * 2 + 1]
        for c in range(cols):
            t = top[c] > 127
            b = bot[c] > 127
            if t and b:
                text.append("█")
            elif t:
                text.append("▀")
            elif b:
                text.append("▄")
            else:
                text.append(" ")
        text.append("\n")
    return text


class PreviewWidget(Widget):
    """Live mask preview rendered as Unicode half-block characters."""

    DEFAULT_CSS = """
    PreviewWidget { width: 1fr; height: 1fr; }
    PreviewWidget Static { width: 1fr; height: 1fr; }
    """

    def compose(self) -> ComposeResult:
        yield Static("Adjust parameters to see a live preview.", id="preview-static")

    def on_mount(self) -> None:
        self._pending = None
        self._pending_params: Optional[MaskParams] = None

    def _static(self) -> Static:
        return self.query_one("#preview-static", Static)

    def schedule_refresh(self, params: MaskParams) -> None:
        if self._pending is not None:
            self._pending.stop()
        self._pending_params = params
        self._pending = self.set_timer(0.3, self._do_refresh)

    def _do_refresh(self) -> None:
        self._pending = None
        p = self._pending_params
        if p is None:
            return
        try:
            src_w = p.width or 400
            src_h = p.height or 250
            preview_w = 200
            scale = preview_w / max(src_w, 1)
            preview_h = max(1, round(src_h * scale))
            mask_img = generate_tiling_mask(
                width=preview_w,
                height=preview_h,
                grid_type=p.grid,
                shape=p.shape,
                size=max(1.0, p.size * scale),
                spacing=max(2.0, p.spacing * scale),
                offset=(0, 0),
                tri_orientation=p.tri_orientation,
                tri_rotation_deg=p.tri_rotation,
            )
            sz = self.size
            cols = max(10, sz.width - 2) if sz.width > 0 else 40
            rows = max(5, sz.height - 2) if sz.height > 0 else 20
            self._static().update(_mask_to_blocks(mask_img, cols, rows))
        except Exception:
            pass  # keep last valid render on bad params


# ── Main app ──────────────────────────────────────────────────────────────────

class MaskApp(App):
    TITLE = "Mask Generator"
    BINDINGS = [("ctrl+q", "quit", "Quit")]

    CSS = """
    Screen { layout: vertical; }

    #layout { layout: horizontal; height: 1fr; }

    #form {
        width: 44;
        border-right: solid $primary-darken-2;
        background: $surface;
    }

    #preview-panel {
        width: 1fr;
        background: $panel;
        padding: 0 1;
        layout: vertical;
    }

    #preview-title {
        text-align: center;
        color: $text-muted;
        height: 1;
        margin: 1 0;
    }

    .row {
        height: auto;
        margin: 0 1 1 1;
        layout: horizontal;
    }

    .lbl {
        width: 10;
        padding-top: 1;
        text-align: right;
        color: $text-muted;
    }

    .ctrl { width: 1fr; }

    .section {
        background: $primary-darken-3;
        color: $text;
        padding: 0 1;
        margin: 1 0 0 0;
        height: 1;
    }

    #lbl-error {
        color: $error;
        margin: 0 1;
        height: auto;
        display: none;
    }

    #lbl-error.show { display: block; }

    .hidden { display: none; }

    #btn-run { margin: 1 1; width: 1fr; }

    .browse { width: 3; min-width: 3; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._p = MaskParams()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="layout"):
            with VerticalScroll(id="form"):
                # Mode selector
                with Horizontal(classes="row"):
                    yield Label("Mode", classes="lbl")
                    yield Select(
                        [("Mode A — generated tiling", "a"),
                         ("Mode B — external mask", "b")],
                        value="a", id="sel-mode", classes="ctrl",
                    )

                # Input / output paths
                with Horizontal(classes="row"):
                    yield Label("Input", classes="lbl")
                    yield Input(placeholder="source image path",
                                id="inp-input", classes="ctrl")
                    yield Button("…", id="btn-browse-input", classes="browse")
                with Horizontal(classes="row"):
                    yield Label("Output", classes="lbl")
                    yield Input(placeholder="output.png",
                                id="inp-output", classes="ctrl")
                    yield Button("…", id="btn-browse-output", classes="browse")

                # ─ Mode A fields ─────────────────────────────────────────────
                yield Label("─── Mode A ────────────────────",
                            id="hdr-a", classes="section")

                with Horizontal(classes="row", id="row-grid"):
                    yield Label("Grid", classes="lbl")
                    yield Select(
                        [("Square", "square"), ("Triangular", "triangular")],
                        value="square", id="sel-grid", classes="ctrl",
                    )
                with Horizontal(classes="row", id="row-shape"):
                    yield Label("Shape", classes="lbl")
                    yield Select(
                        [("Circle", "circle"), ("Square", "square"),
                         ("Triangle", "triangle"), ("Hexagon", "hexagon"),
                         ("Star 5pt", "star5")],
                        value="circle", id="sel-shape", classes="ctrl",
                    )
                with Horizontal(classes="row", id="row-size"):
                    yield Label("Size", classes="lbl")
                    yield Input(value="40", id="inp-size", classes="ctrl")
                with Horizontal(classes="row", id="row-spacing"):
                    yield Label("Spacing", classes="lbl")
                    yield Input(value="90", id="inp-spacing", classes="ctrl")
                with Horizontal(classes="row", id="row-width"):
                    yield Label("Width", classes="lbl")
                    yield Input(placeholder="auto", id="inp-width",
                                classes="ctrl", disabled=True)
                    yield Checkbox("auto", value=True, id="chk-w-auto")
                with Horizontal(classes="row", id="row-height"):
                    yield Label("Height", classes="lbl")
                    yield Input(placeholder="auto", id="inp-height",
                                classes="ctrl", disabled=True)
                    yield Checkbox("auto", value=True, id="chk-h-auto")
                with Horizontal(classes="row", id="row-offset"):
                    yield Label("Offset X Y", classes="lbl")
                    yield Input(value="0", id="inp-ox", classes="ctrl")
                    yield Input(value="0", id="inp-oy", classes="ctrl")

                # Triangle-only (hidden until shape=triangle)
                with Horizontal(classes="row hidden", id="row-tri-orient"):
                    yield Label("Tri orient", classes="lbl")
                    yield Select(
                        [("Alternating", "alternating"), ("Fixed", "fixed")],
                        value="alternating", id="sel-tri-orient", classes="ctrl",
                    )
                with Horizontal(classes="row hidden", id="row-tri-rot"):
                    yield Label("Tri rot°", classes="lbl")
                    yield Input(value="0", id="inp-tri-rot", classes="ctrl")

                # ─ Mode B fields (hidden until mode=b) ───────────────────────
                yield Label("─── Mode B ────────────────────",
                            id="hdr-b", classes="section hidden")
                with Horizontal(classes="row hidden", id="row-mask-file"):
                    yield Label("Mask file", classes="lbl")
                    yield Input(placeholder="b&w mask.png",
                                id="inp-mask-file", classes="ctrl")
                    yield Button("…", id="btn-browse-mask", classes="browse")

                # ─ Common ────────────────────────────────────────────────────
                yield Label("───────────────────────────────", classes="section")
                with Horizontal(classes="row"):
                    yield Label("", classes="lbl")
                    yield Checkbox("Mask Only", id="chk-mask-only")

                yield Label("", id="lbl-error")
                yield Button("Run", id="btn-run", variant="primary")

            with Vertical(id="preview-panel"):
                yield Label("Live Preview", id="preview-title")
                yield PreviewWidget(id="preview")

        yield Footer()

    def on_mount(self) -> None:
        self._preview().schedule_refresh(self._p)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _preview(self) -> PreviewWidget:
        return self.query_one("#preview", PreviewWidget)

    def _refresh(self) -> None:
        self._preview().schedule_refresh(self._p)

    def _error(self, msg: str) -> None:
        lbl = self.query_one("#lbl-error", Label)
        lbl.update(msg)
        if msg:
            lbl.add_class("show")
        else:
            lbl.remove_class("show")

    # ── Mode switch ───────────────────────────────────────────────────────────

    @on(Select.Changed, "#sel-mode")
    def _mode(self, e: Select.Changed) -> None:
        if e.value is Select.BLANK:
            return
        self._p.mode = str(e.value)
        is_b = self._p.mode == "b"
        a_ids = ["hdr-a", "row-grid", "row-shape", "row-size",
                 "row-spacing", "row-width", "row-height", "row-offset"]
        b_ids = ["hdr-b", "row-mask-file"]
        for wid in a_ids:
            w = self.query_one(f"#{wid}")
            w.add_class("hidden") if is_b else w.remove_class("hidden")
        # Triangle rows follow shape, not mode — leave them alone
        for wid in b_ids:
            w = self.query_one(f"#{wid}")
            w.remove_class("hidden") if is_b else w.add_class("hidden")
        self._refresh()

    # ── Shape → show/hide triangle fields ────────────────────────────────────

    @on(Select.Changed, "#sel-shape")
    def _shape(self, e: Select.Changed) -> None:
        if e.value is Select.BLANK:
            return
        self._p.shape = str(e.value)
        is_tri = self._p.shape == "triangle"
        for wid in ["row-tri-orient", "row-tri-rot"]:
            w = self.query_one(f"#{wid}")
            w.remove_class("hidden") if is_tri else w.add_class("hidden")
        self._refresh()

    # ── Field watchers → params ───────────────────────────────────────────────

    @on(Select.Changed, "#sel-grid")
    def _grid(self, e: Select.Changed) -> None:
        if e.value is not Select.BLANK:
            self._p.grid = str(e.value)
            self._refresh()

    @on(Input.Changed, "#inp-size")
    def _size(self, e: Input.Changed) -> None:
        try:
            self._p.size = float(e.value)
            self._refresh()
        except ValueError:
            pass

    @on(Input.Changed, "#inp-spacing")
    def _spacing(self, e: Input.Changed) -> None:
        try:
            self._p.spacing = float(e.value)
            self._refresh()
        except ValueError:
            pass

    @on(Input.Changed, "#inp-width")
    def _width(self, e: Input.Changed) -> None:
        try:
            self._p.width = int(e.value) if e.value.strip() else None
            self._refresh()
        except ValueError:
            pass

    @on(Input.Changed, "#inp-height")
    def _height(self, e: Input.Changed) -> None:
        try:
            self._p.height = int(e.value) if e.value.strip() else None
            self._refresh()
        except ValueError:
            pass

    @on(Input.Changed, "#inp-ox")
    def _ox(self, e: Input.Changed) -> None:
        try:
            self._p.offset_x = float(e.value)
            self._refresh()
        except ValueError:
            pass

    @on(Input.Changed, "#inp-oy")
    def _oy(self, e: Input.Changed) -> None:
        try:
            self._p.offset_y = float(e.value)
            self._refresh()
        except ValueError:
            pass

    @on(Select.Changed, "#sel-tri-orient")
    def _tri_orient(self, e: Select.Changed) -> None:
        if e.value is not Select.BLANK:
            self._p.tri_orientation = str(e.value)
            self._refresh()

    @on(Input.Changed, "#inp-tri-rot")
    def _tri_rot(self, e: Input.Changed) -> None:
        try:
            self._p.tri_rotation = float(e.value)
            self._refresh()
        except ValueError:
            pass

    @on(Input.Changed, "#inp-input")
    def _inp_input(self, e: Input.Changed) -> None:
        self._p.input_path = e.value

    @on(Input.Changed, "#inp-output")
    def _inp_output(self, e: Input.Changed) -> None:
        self._p.output_path = e.value

    @on(Input.Changed, "#inp-mask-file")
    def _inp_mask(self, e: Input.Changed) -> None:
        self._p.mask_file = e.value

    @on(Checkbox.Changed, "#chk-mask-only")
    def _mask_only(self, e: Checkbox.Changed) -> None:
        self._p.mask_only = e.value

    @on(Checkbox.Changed, "#chk-w-auto")
    def _w_auto(self, e: Checkbox.Changed) -> None:
        inp = self.query_one("#inp-width", Input)
        inp.disabled = e.value
        if e.value:
            inp.value = ""
            self._p.width = None
        self._refresh()

    @on(Checkbox.Changed, "#chk-h-auto")
    def _h_auto(self, e: Checkbox.Changed) -> None:
        inp = self.query_one("#inp-height", Input)
        inp.disabled = e.value
        if e.value:
            inp.value = ""
            self._p.height = None
        self._refresh()

    # ── Browse buttons ────────────────────────────────────────────────────────

    def _browse(self, target_id: str) -> None:
        current = self.query_one(f"#{target_id}", Input).value or "."
        p = Path(current)
        start = str(p.parent if p.exists() else Path(".").resolve())

        def _cb(path: Optional[str]) -> None:
            if path:
                self.query_one(f"#{target_id}", Input).value = path

        self.push_screen(FileBrowserModal(start), _cb)

    @on(Button.Pressed, "#btn-browse-input")
    def _browse_input(self) -> None:
        self._browse("inp-input")

    @on(Button.Pressed, "#btn-browse-output")
    def _browse_output(self) -> None:
        self._browse("inp-output")

    @on(Button.Pressed, "#btn-browse-mask")
    def _browse_mask(self) -> None:
        self._browse("inp-mask-file")

    # ── Run ───────────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-run")
    def _run(self) -> None:
        p = self._p
        self._error("")
        if not p.output_path.strip():
            self._error("Output path is required.")
            return
        try:
            if p.mode == "b":
                self._exec_mode_b(p)
            else:
                self._exec_mode_a(p)
        except Exception as exc:
            self._error(str(exc))
            self.notify(str(exc), severity="error")

    def _exec_mode_a(self, p: MaskParams) -> None:
        if p.width is None or p.height is None:
            if not p.input_path.strip() and not p.mask_only:
                raise ValueError("Provide Width/Height, or an input image.")
            if p.input_path.strip():
                with Image.open(p.input_path) as probe:
                    iw, ih = probe.size
                width = p.width if p.width is not None else iw
                height = p.height if p.height is not None else ih
            else:
                raise ValueError(
                    "Width and Height are required when Mask Only is "
                    "checked and no input image is set."
                )
        else:
            width, height = p.width, p.height

        mask_img = generate_tiling_mask(
            width=width, height=height,
            grid_type=p.grid, shape=p.shape,
            size=p.size, spacing=p.spacing,
            offset=(p.offset_x, p.offset_y),
            tri_orientation=p.tri_orientation,
            tri_rotation_deg=p.tri_rotation,
        )

        if p.mask_only:
            mask_img.save(p.output_path, format="PNG")
            self.notify(f"Mask saved → {p.output_path}")
            return

        if not p.input_path.strip():
            raise ValueError("Input image is required (or enable Mask Only).")

        source = Image.open(p.input_path)
        result = apply_mask_to_image(source, mask_img)
        result.save(p.output_path, format="PNG")
        self.notify(f"Saved → {p.output_path}")

    def _exec_mode_b(self, p: MaskParams) -> None:
        if not p.input_path.strip():
            raise ValueError("Input image is required for Mode B.")
        if not p.mask_file.strip():
            raise ValueError("Mask file is required for Mode B.")
        source = Image.open(p.input_path)
        mask_raw = Image.open(p.mask_file).convert("L")
        inverted = 255 - np.array(mask_raw)
        mask_img = Image.fromarray(inverted, mode="L")
        result = apply_mask_to_image(source, mask_img)
        result.save(p.output_path, format="PNG")
        self.notify(f"Saved → {p.output_path}")


if __name__ == "__main__":
    MaskApp().run()
