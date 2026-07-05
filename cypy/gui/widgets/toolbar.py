import tkinter as tk
from tkinter import ttk


class MainToolBar(ttk.Frame):
    def __init__(
        self,
        parent,
        language_var,
        status_var,
        page_var,
        on_open_files,
        on_previous,
        on_next,
        on_translate,
    ):
        super().__init__(parent, style="Toolbar.TFrame", padding=(10, 8))
        self.columnconfigure(3, weight=1)

        self.open_button = ttk.Button(
            self,
            text="Open Files",
            command=on_open_files,
            style="Toolbar.TButton",
        )
        self.open_button.grid(row=0, column=0, padx=(0, 8), sticky="w")

        languages = (
            "Indonesian",
            "English",
            "Japanese",
            "Korean",
            "Chinese (Simplified)",
            "Chinese (Traditional)",
            "Spanish",
            "Portuguese",
            "Thai",
            "Vietnamese",
        )
        self.language = ttk.Combobox(
            self,
            textvariable=language_var,
            values=languages,
            width=22,
            state="normal",
            style="Toolbar.TCombobox",
        )
        self.language.grid(row=0, column=1, padx=(0, 8), sticky="w")

        ttk.Separator(self, orient=tk.VERTICAL).grid(
            row=0,
            column=2,
            sticky="ns",
            padx=(2, 12),
        )
        ttk.Label(
            self,
            textvariable=status_var,
            style="ToolbarStatus.TLabel",
            anchor=tk.CENTER,
        ).grid(row=0, column=3, sticky="ew")

        self.previous_button = ttk.Button(
            self,
            text="<",
            width=3,
            command=on_previous,
            style="Toolbar.TButton",
        )
        self.previous_button.grid(row=0, column=4, padx=(8, 4))
        ttk.Label(
            self,
            textvariable=page_var,
            width=8,
            anchor=tk.CENTER,
            style="Toolbar.TLabel",
        ).grid(row=0, column=5, padx=2)
        self.next_button = ttk.Button(
            self,
            text=">",
            width=3,
            command=on_next,
            style="Toolbar.TButton",
        )
        self.next_button.grid(row=0, column=6, padx=(4, 10))

        self.translate_button = ttk.Button(
            self,
            text="Translate",
            command=on_translate,
            style="Accent.TButton",
        )
        self.translate_button.grid(row=0, column=7, sticky="e")
        self.set_page_state(False, False, False)

    def set_page_state(self, can_previous, can_next, can_translate):
        self.previous_button.configure(
            state=tk.NORMAL if can_previous else tk.DISABLED
        )
        self.next_button.configure(state=tk.NORMAL if can_next else tk.DISABLED)
        self.translate_button.configure(
            state=tk.NORMAL if can_translate else tk.DISABLED
        )

    def set_processing(self, processing):
        self.open_button.configure(state=tk.DISABLED if processing else tk.NORMAL)
        self.translate_button.configure(
            state=tk.DISABLED if processing else tk.NORMAL
        )

