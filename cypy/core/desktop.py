def create_shortcut_if_first_run():
    """Create a Windows desktop shortcut on first run for frozen builds."""
    import os
    import subprocess
    import sys

    if sys.platform != "win32":
        return

    if not getattr(sys, "frozen", False):
        return

    base_path = os.path.dirname(sys.executable)
    cache_dir = os.path.join(base_path, "cypy_cache")
    os.makedirs(cache_dir, exist_ok=True)

    flag_file = os.path.join(cache_dir, ".shortcut_created")
    if os.path.exists(flag_file):
        return

    try:
        exe_path = sys.executable
        working_dir = base_path
        ps_cmd = (
            "$WshShell = New-Object -ComObject WScript.Shell; "
            "$Shortcut = $WshShell.CreateShortcut(([Environment]::GetFolderPath('Desktop') + '\\cypy.lnk')); "
            f"$Shortcut.TargetPath = '{exe_path}'; "
            f"$Shortcut.WorkingDirectory = '{working_dir}'; "
            f"$Shortcut.IconLocation = '{exe_path}'; "
            "$Shortcut.Save()"
        )

        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            creationflags=0x08000000,
            check=True,
        )

        with open(flag_file, "w") as handle:
            handle.write("created")

        print("[Utils] Desktop shortcut successfully created.")
    except Exception as exc:
        print(f"[Utils] Failed to create desktop shortcut: {exc}")
