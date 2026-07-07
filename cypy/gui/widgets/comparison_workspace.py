import tkinter as tk
from tkinter import ttk

from cypy.gui.widgets.preview_panel import PreviewPanel


class ComparisonWorkspace(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Workspace.TFrame")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1, uniform="viewer")
        self.columnconfigure(2, weight=1, uniform="viewer")

        self.original = PreviewPanel(self, title="Original")
        self.original.grid(row=0, column=0, sticky="nsew")
        ttk.Separator(self, orient=tk.VERTICAL).grid(
            row=0,
            column=1,
            sticky="ns",
        )
        self.translated = PreviewPanel(self, title="Translated")
        self.translated.grid(row=0, column=2, sticky="nsew")

    def show_page(
        self,
        input_path,
        output_path=None,
        translated_message=None,
        boxes=None,
        text_mask=None,
    ):
        self.original.set_image_path(input_path, boxes=boxes, text_mask=text_mask)
        if output_path:
            self.translated.set_image_path(output_path)
        else:
            self.translated.clear(translated_message or "Not translated yet")

    def clear(self):
        self.original.clear()
        self.translated.clear()
