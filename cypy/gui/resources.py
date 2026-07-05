import ctypes
import sys
import tkinter as tk
from pathlib import Path


APP_USER_MODEL_ID = "rizkyaa.cypy.extended"


def asset_path(filename):
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base_dir = Path(__file__).resolve().parents[2]
    return base_dir / "assets" / filename


def configure_process_identity():
    """Set a stable Windows taskbar identity before creating the root window."""
    if sys.platform != "win32":
        return False
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            APP_USER_MODEL_ID
        )
    except (AttributeError, OSError):
        return False
    return True


def apply_window_icon(root, icon_path=None, image_factory=None):
    path = Path(icon_path) if icon_path else asset_path("favicon.png")
    if not path.is_file():
        return False

    factory = image_factory or tk.PhotoImage
    try:
        icon = factory(file=str(path))
        root.iconphoto(True, icon)
    except (OSError, tk.TclError):
        return False

    # Tk only keeps the Tcl image name; retain the Python object explicitly.
    root._cypy_window_icon = icon
    return True
