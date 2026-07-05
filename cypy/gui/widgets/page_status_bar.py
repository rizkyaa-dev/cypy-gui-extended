import tkinter as tk
from tkinter import ttk


class PageStatusBar(ttk.Frame):
    def __init__(self, parent, on_remove):
        super().__init__(parent, style="StatusBar.TFrame", padding=(10, 8))
        self.columnconfigure(2, weight=1)

        self.page_id = tk.StringVar(value="ID: -")
        self.filename = tk.StringVar(value="Open image files to begin")
        self.state = tk.StringVar(value="No page")
        self.message = tk.StringVar(value="")

        ttk.Label(
            self,
            textvariable=self.page_id,
            style="PageId.TLabel",
            width=9,
            anchor=tk.CENTER,
        ).grid(row=0, column=0, padx=(0, 8), sticky="ns")
        ttk.Label(
            self,
            textvariable=self.filename,
            style="Filename.TLabel",
            width=28,
            anchor=tk.W,
        ).grid(row=0, column=1, padx=(0, 8), sticky="w")
        ttk.Label(
            self,
            textvariable=self.message,
            style="Message.TLabel",
            anchor=tk.W,
        ).grid(row=0, column=2, padx=(0, 10), sticky="ew")

        self.progress = ttk.Progressbar(
            self,
            orient=tk.HORIZONTAL,
            mode="determinate",
            maximum=100,
            length=120,
            style="Page.Horizontal.TProgressbar",
        )
        self.progress.grid(row=0, column=3, padx=(0, 10))
        ttk.Label(
            self,
            textvariable=self.state,
            style="State.TLabel",
            width=11,
            anchor=tk.CENTER,
        ).grid(row=0, column=4, padx=(0, 8))
        self.remove_button = ttk.Button(
            self,
            text="Remove Page",
            command=on_remove,
            style="Danger.TButton",
        )
        self.remove_button.grid(row=0, column=5)
        self.remove_button.configure(state=tk.DISABLED)

    def set_page(self, job, index, removable=True):
        self.page_id.set(f"ID: {index + 1}")
        self.filename.set(job.filename)
        self.state.set(job.status.value.title())
        self.message.set(job.message)
        self.progress.configure(value=job.progress)
        self.remove_button.configure(
            state=tk.NORMAL if removable else tk.DISABLED
        )

    def set_message(self, message):
        self.message.set(str(message))

    def clear(self):
        self.page_id.set("ID: -")
        self.filename.set("Open image files to begin")
        self.state.set("No page")
        self.message.set("")
        self.progress.configure(value=0)
        self.remove_button.configure(state=tk.DISABLED)
