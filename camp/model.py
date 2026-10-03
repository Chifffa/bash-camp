"""The types the modules in this package hand to each other. Imports nothing from the package."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, TypedDict


if TYPE_CHECKING:
    from pathlib import Path


class CampError(Exception):
    """A user-facing failure: printed without a traceback, exits with status 1."""


class JournalEntry(TypedDict, total=False):
    """One change install made outside $CAMP_HOME, and what uninstall needs to take it back.

    Attributes:
        kind: what was done, which decides how it is undone:
            "created"  a path that did not exist - removed;
            "symlink"  a config or font link - removed if still ours, the backup restored;
            "file"     a placed secret - removed if unchanged, the backup restored;
            "rc_line"  the line in ~/.bashrc - dropped, the file restored byte for byte.
        path: the path changed.
        keep: the nearest ancestor that existed before. Uninstall prunes the empty directories
            install had to create on the way, up to this one and never past it.
        target: "symlink" only - where the link points.
        backup: "symlink" and "file" - where the displaced original went, or None.
        digest: "file" only - the placed content, so uninstall can tell it was not changed since.
        created_digest: "rc_line" only - the file's content when install created it, or None when
            it existed before.
        added_newline: "rc_line" only - whether install had to end the file's last line first.
    """

    kind: str
    path: str
    keep: str
    target: str
    backup: str | None
    digest: str | None
    created_digest: str | None
    added_newline: bool


@dataclasses.dataclass(frozen=True)
class SecretEntry:
    """One entry of secrets/manifest.json.

    Attributes:
        source: path of the file or directory, relative to secrets/.
        target: where install copies it, under the home directory; None for an env file.
        load: "env" for a file exported into every shell instead of placed, else None.
        mode: permissions of the placed files (directories always get 0700).
        local_only: never shipped to remote hosts; skipped wherever it is absent.
    """

    source: str
    target: Path | None
    load: str | None
    mode: int
    local_only: bool
