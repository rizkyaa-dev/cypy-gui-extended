import os
import stat
from dataclasses import dataclass

from cypy.core.errors import ArchiveSafetyError


@dataclass(frozen=True)
class ArchiveExtractionPolicy:
    max_members: int = 5000
    max_total_size: int = 2 * 1024 * 1024 * 1024
    max_member_size: int = 256 * 1024 * 1024
    max_compression_ratio: float = 200.0


def is_safe_archive_member(destination, member_name):
    normalized_name = str(member_name or "").replace("\\", "/")

    if not normalized_name or os.path.isabs(normalized_name):
        return False

    destination_root = os.path.abspath(destination)
    target_path = os.path.abspath(os.path.join(destination_root, normalized_name))

    try:
        return os.path.commonpath([destination_root, target_path]) == destination_root
    except ValueError:
        return False


def safe_extract_all(archive, destination, policy=None):
    policy = policy or ArchiveExtractionPolicy()
    members = archive.infolist()

    if len(members) > policy.max_members:
        raise ArchiveSafetyError(
            f"Archive contains too many entries: {len(members)} > {policy.max_members}"
        )

    total_size = 0
    destinations = set()
    for member in members:
        member_name = getattr(member, "filename", None)
        if not is_safe_archive_member(destination, member_name):
            raise ArchiveSafetyError(f"Unsafe archive path: {member_name}")

        if _is_symlink(member):
            raise ArchiveSafetyError(f"Archive links are not allowed: {member_name}")

        target = os.path.normcase(
            os.path.abspath(os.path.join(destination, str(member_name).replace("\\", "/")))
        )
        if target in destinations:
            raise ArchiveSafetyError(f"Duplicate archive path: {member_name}")
        destinations.add(target)

        size = max(0, int(getattr(member, "file_size", 0) or 0))
        compressed_size = max(0, int(getattr(member, "compress_size", 0) or 0))
        if size > policy.max_member_size:
            raise ArchiveSafetyError(f"Archive member is too large: {member_name}")
        total_size += size
        if total_size > policy.max_total_size:
            raise ArchiveSafetyError("Archive expands beyond the configured size limit.")
        if (
            size > 1024 * 1024
            and compressed_size > 0
            and size / compressed_size > policy.max_compression_ratio
        ):
            raise ArchiveSafetyError(
                f"Suspicious compression ratio for archive member: {member_name}"
            )

    for member in members:
        archive.extract(member, destination)


def _is_symlink(member):
    is_symlink = getattr(member, "is_symlink", None)
    if callable(is_symlink):
        try:
            if is_symlink():
                return True
        except (AttributeError, OSError, TypeError):
            return True

    external_attr = getattr(member, "external_attr", 0) or 0
    unix_mode = int(external_attr) >> 16
    return bool(unix_mode and stat.S_ISLNK(unix_mode))
