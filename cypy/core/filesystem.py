import json
import os
import tempfile


def atomic_replace(path, writer):
    """Write a sibling temporary file and atomically replace the destination."""
    destination = os.path.abspath(os.fspath(path))
    directory = os.path.dirname(destination)
    os.makedirs(directory, exist_ok=True)

    suffix = os.path.splitext(destination)[1]
    fd, temp_path = tempfile.mkstemp(prefix=".cypy-", suffix=suffix, dir=directory)
    os.close(fd)

    try:
        writer(temp_path)
        os.replace(temp_path, destination)
    finally:
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass


def atomic_write_text(path, content, encoding="utf-8"):
    def write(temp_path):
        with open(temp_path, "w", encoding=encoding, newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

    atomic_replace(path, write)


def atomic_write_json(path, payload):
    atomic_write_text(
        path,
        json.dumps(payload, indent=4, ensure_ascii=False) + "\n",
    )
