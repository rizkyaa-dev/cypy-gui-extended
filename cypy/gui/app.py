import tkinter as tk
from tkinter import messagebox

from cypy.gui.resources import apply_window_icon, configure_process_identity


def main():
    configure_process_identity()
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Unable to start the desktop GUI: {exc}")
        return 1

    try:
        from cypy.gui.main_window import MainWindow
        from cypy.gui.theme import apply_dark_theme

        apply_window_icon(root)
        apply_dark_theme(root)
        MainWindow(root)
        root.mainloop()
    except Exception as exc:
        messagebox.showerror("cypy-extended", str(exc), parent=root)
        root.destroy()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
