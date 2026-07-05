from tkinter import ttk


BACKGROUND = "#161616"
SURFACE = "#1f1f1f"
SURFACE_RAISED = "#292929"
VIEWER = "#101010"
BORDER = "#3a3a3a"
TEXT = "#f1f1f1"
TEXT_MUTED = "#a4a4a4"
ACCENT = "#60778f"
ACCENT_ACTIVE = "#718aa3"
DANGER = "#c9474f"
DANGER_ACTIVE = "#dc5961"


def apply_dark_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(background=BACKGROUND)
    root.option_add("*Font", ("Segoe UI", 10))
    root.option_add("*TCombobox*Listbox.background", SURFACE_RAISED)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    style.configure(".", background=BACKGROUND, foreground=TEXT)
    style.configure("App.TFrame", background=BACKGROUND)
    style.configure("Toolbar.TFrame", background="#121212")
    style.configure("Workspace.TFrame", background=VIEWER)
    style.configure("Viewer.TFrame", background=VIEWER)
    style.configure("StatusBar.TFrame", background="#121212")

    style.configure(
        "TLabel",
        background=BACKGROUND,
        foreground=TEXT,
        padding=0,
    )
    style.configure(
        "Toolbar.TLabel",
        background="#121212",
        foreground=TEXT,
    )
    style.configure(
        "ToolbarStatus.TLabel",
        background="#121212",
        foreground=TEXT_MUTED,
    )
    style.configure(
        "ViewerHeader.TLabel",
        background="#121212",
        foreground=TEXT,
        font=("Segoe UI Semibold", 9),
        padding=(8, 5),
    )
    style.configure(
        "PageId.TLabel",
        background="#121212",
        foreground="#ff676d",
        font=("Segoe UI Semibold", 9),
        bordercolor=DANGER,
        borderwidth=1,
        relief="solid",
        padding=(6, 6),
    )
    style.configure(
        "Filename.TLabel",
        background=SURFACE,
        foreground=TEXT,
        padding=(8, 7),
    )
    style.configure(
        "Message.TLabel",
        background=SURFACE,
        foreground=TEXT_MUTED,
        padding=(8, 7),
    )
    style.configure(
        "State.TLabel",
        background="#121212",
        foreground=TEXT_MUTED,
    )

    style.configure(
        "TButton",
        background=SURFACE_RAISED,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=SURFACE_RAISED,
        darkcolor=SURFACE_RAISED,
        padding=(10, 7),
    )
    style.map(
        "TButton",
        background=[("active", "#353535"), ("disabled", "#202020")],
        foreground=[("disabled", "#666666")],
    )
    style.configure("Toolbar.TButton", padding=(10, 7))
    style.configure(
        "Accent.TButton",
        background=ACCENT,
        bordercolor=ACCENT,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        font=("Segoe UI Semibold", 10),
    )
    style.map(
        "Accent.TButton",
        background=[("active", ACCENT_ACTIVE), ("disabled", "#303840")],
        foreground=[("disabled", "#777777")],
    )
    style.configure(
        "Danger.TButton",
        background=DANGER,
        bordercolor=DANGER,
        lightcolor=DANGER,
        darkcolor=DANGER,
    )
    style.map(
        "Danger.TButton",
        background=[("active", DANGER_ACTIVE), ("disabled", "#372326")],
        foreground=[("disabled", "#777777")],
    )

    style.configure(
        "Toolbar.TCombobox",
        fieldbackground=SURFACE_RAISED,
        background=SURFACE_RAISED,
        foreground=TEXT,
        arrowcolor=TEXT_MUTED,
        bordercolor=BORDER,
        lightcolor=SURFACE_RAISED,
        darkcolor=SURFACE_RAISED,
        padding=(7, 5),
    )
    style.map(
        "Toolbar.TCombobox",
        fieldbackground=[("readonly", SURFACE_RAISED)],
        foreground=[("readonly", TEXT)],
        selectbackground=[("readonly", SURFACE_RAISED)],
        selectforeground=[("readonly", TEXT)],
    )
    style.configure("TSeparator", background=BORDER)
    style.configure(
        "Page.Horizontal.TProgressbar",
        troughcolor=SURFACE_RAISED,
        background=ACCENT,
        bordercolor=SURFACE_RAISED,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        thickness=8,
    )

