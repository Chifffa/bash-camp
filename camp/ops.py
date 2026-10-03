"""The file and process primitives every step is written in.

Two habits run through all of them. A dangling symlink counts as existing, because a link install
left behind is still ours to remove. And a file is rewritten atomically through its symlink, never
replaced, so a ~/.bashrc managed elsewhere stays managed.
"""

from __future__ import annotations

import hashlib
import io
import shutil
import subprocess
from pathlib import Path

from .paths import HOME


# Shell command executor shorthand.
sh = subprocess.check_call


def display(path: Path) -> str:
    """Render a path for log lines, with ~ for the home directory.

    :param path: an absolute path.
    :return: the path, `~/...` when it is under the home directory.
    """
    try:
        return f"~/{path.relative_to(HOME)}"
    except ValueError:
        return str(path)


def home_relative(path: Path) -> Path:
    """Where a path goes inside a mirror of the filesystem, such as $CAMP_HOME/backups.

    :param path: an absolute path.
    :return: the path relative to the home directory, or under `_root/` outside it.
    """
    try:
        return path.relative_to(HOME)
    except ValueError:
        return Path("_root") / path.relative_to(path.anchor)


def first_existing_ancestor(path: Path) -> Path:
    """The nearest ancestor of a path that exists.

    :param path: an absolute path, existing or not.
    :return: the ancestor; the filesystem root at worst.
    """
    for parent in path.parents:
        if parent.exists():
            return parent
    return Path(path.anchor)


def exists(path: Path) -> bool:
    """exists() that also counts dangling symlinks.

    :param path: the path.
    :return: whether anything, a dangling symlink included, sits at the path.
    """
    return path.is_symlink() or path.exists()


def digest(path: Path) -> str:
    """Content hash of a file, or of a directory tree including its file names.

    :param path: a file or a directory.
    :return: the SHA-256, hex-encoded.
    """
    sha = hashlib.sha256()
    if path.is_dir():
        for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
            sha.update(str(file_path.relative_to(path)).encode())
            sha.update(b"\0")
            sha.update(file_path.read_bytes())
    else:
        sha.update(path.read_bytes())
    return sha.hexdigest()


def restrict_tree(root: Path, *, file_mode: int) -> None:
    """Make a directory tree private: directories 0700, files the given mode.

    :param root: the top of the tree.
    :param file_mode: permissions of every file in it; symlinks are left alone.
    """
    root.chmod(0o700)
    for path in root.rglob("*"):
        if path.is_symlink():
            continue
        path.chmod(0o700 if path.is_dir() else file_mode)


def make_private_dirs(path: Path) -> None:
    """Create a directory and its parents, giving every directory created 0700.

    Path.mkdir(parents=True) applies the mode to the last directory only.

    :param path: the directory; an existing one is fine.
    """
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)


def remove_path(path: Path, *, label: str | None = None) -> None:
    """Delete a file, symlink or directory tree.

    :param path: filesystem entry to delete; a missing one is fine.
    :param label: human-readable name for the log line; nothing is logged without one.
    """
    # is_symlink() first: a dangling symlink reports exists() as False.
    if not exists(path):
        return

    if path.is_symlink() or not path.is_dir():
        path.unlink()
    else:
        shutil.rmtree(path)

    if label:
        print(f"  Removed {label}.")


def prune_empty_dirs(start: Path, keep: Path) -> None:
    """Remove empty directories from start upwards, stopping at keep.

    :param start: the deepest directory to try.
    :param keep: the first directory not to remove; nothing above it is touched either.
    """
    current = start
    while current != keep and keep in current.parents:
        try:
            current.rmdir()
        except OSError:
            return
        print(f"  Removed empty {display(current)}.")
        current = current.parent


def rewrite_file(path: Path, text: str) -> None:
    """Atomically replace a file's content, keeping its mode and following symlinks.

    Following a symlinked ~/.bashrc matters: replacing the link with a regular file would silently
    detach it from whatever manages it.

    :param path: the file, or a symlink to it; a missing one is created.
    :param text: the new content.
    """
    real_path = path.resolve()
    tmp_path = real_path.with_name(f"{real_path.name}.camp-tmp")
    tmp_path.write_text(text)
    if real_path.exists():
        shutil.copymode(real_path, tmp_path)
    tmp_path.replace(real_path)


def drop_lines_containing(path: Path, needle: str, *, quiet: bool = False) -> None:
    """Remove every line of a file that contains the given substring.

    Substring rather than exact matching on purpose: the lines this package writes embed the
    $CAMP_HOME path, so an exact match stops working the moment it changes and would leave the
    stale line behind forever. Matching on the tag catches every variant it ever wrote.

    :param path: path to the file; a missing one is fine.
    :param needle: substring identifying the lines to remove.
    :param quiet: do not log the dropped lines.
    """
    if not path.is_file():
        return

    builder = io.StringIO()
    dropped: list[str] = []
    with path.open() as fin:
        for file_line in fin:
            if needle in file_line:
                dropped.append(file_line.strip())
            else:
                builder.write(file_line)

    if not dropped:
        return

    rewrite_file(path, builder.getvalue())

    if not quiet:
        for line in dropped:
            print(f"  Dropped {line!r} from {display(path)}.")
