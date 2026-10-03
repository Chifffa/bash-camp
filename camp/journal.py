"""The record of every change install makes outside $CAMP_HOME, and how each one is undone.

Every such change goes through here BEFORE it is made, with whatever it displaced moved into
$CAMP_HOME/backups. Inside $CAMP_HOME nothing is journaled: uninstall deletes the directory as a
whole.
"""

from __future__ import annotations

import json
import shutil
import warnings
from pathlib import Path
from typing import Any

from .model import CampError, JournalEntry
from .ops import (
    digest,
    display,
    drop_lines_containing,
    exists,
    first_existing_ancestor,
    home_relative,
    prune_empty_dirs,
    remove_path,
    rewrite_file,
)
from .paths import CAMP_BACKUPS, CAMP_HOME, CAMP_JOURNAL, CAMP_STATE, HOME, RC_MARKER


class Journal:
    """Every change install made outside $CAMP_HOME, with what it displaced.

    Each install starts a journal of its own: an earlier installation is uninstalled first, so
    the journal always describes the state before bash-camp. The file is rewritten after every
    change: an interrupted install can still be uninstalled cleanly, and an interrupted uninstall
    resumed, because an entry is forgotten as soon as it is reverted.
    """

    VERSION = 1

    def __init__(self, data: dict[str, Any]) -> None:
        """Wrap journal data read from disk or freshly made.

        :param data: the whole journal file: version, home, camp_home, camp_home_keep, entries.
        """
        self.data = data

    @classmethod
    def load(cls) -> Journal | None:
        """Read the journal of the installation in $CAMP_HOME.

        :return: the journal, or None when bash-camp is not installed there.
        :raises CampError: if the installation belongs to a different home directory.
        """
        if not CAMP_JOURNAL.is_file():
            return None

        journal = cls(json.loads(CAMP_JOURNAL.read_text()))
        recorded_home = journal.data.get("home")
        if recorded_home != str(HOME):
            # The same $CAMP_HOME seen from a container that bind-mounts it under a different
            # $HOME: replaying it here would act on the wrong home.
            raise CampError(
                f"{CAMP_HOME} was installed for the home directory {recorded_home}, not {HOME}."
                " Run `camp pitch` or `camp strike` from that environment instead."
            )

        return journal

    @classmethod
    def create(cls, camp_home_keep: Path, entries: list[JournalEntry]) -> Journal:
        """Start the journal of an install.

        :param camp_home_keep: the nearest ancestor of $CAMP_HOME that existed before, so that
            uninstall can prune what was created to hold it.
        :param entries: entries taken over from the installation this one replaces; empty on a
            first install.
        :return: the new journal, already on disk.
        """
        journal = cls(
            {
                "version": cls.VERSION,
                "home": str(HOME),
                "camp_home": str(CAMP_HOME),
                "camp_home_keep": str(camp_home_keep),
                "entries": list(entries),
            }
        )
        journal.save()
        return journal

    @property
    def entries(self) -> list[JournalEntry]:
        """The entries, oldest first; uninstall reverts them newest first.

        :return: the live list - changing it changes the journal.
        """
        return self.data["entries"]

    def save(self) -> None:
        """Write the journal to $CAMP_HOME/state/journal.json, atomically."""
        CAMP_STATE.mkdir(parents=True, exist_ok=True)
        rewrite_file(CAMP_JOURNAL, f"{json.dumps(self.data, indent=2)}\n")

    def find(self, path: Path) -> JournalEntry | None:
        """Look up the entry of a path.

        :param path: the path, as it was recorded.
        :return: its entry, or None when nothing was recorded for it.
        """
        key = str(path)
        return next((entry for entry in self.entries if entry["path"] == key), None)

    def add(self, kind: str, path: Path, **fields: Any) -> JournalEntry:
        """Record a path before anything is created for it.

        "keep" is computed here, which is why callers add the entry BEFORE creating parent
        directories.

        :param kind: the entry kind; see `JournalEntry`.
        :param path: the path about to be changed.
        :param fields: the kind's own fields.
        :return: the new entry, already on disk.
        """
        entry = JournalEntry(
            kind=kind, path=str(path), keep=str(first_existing_ancestor(path)), **fields
        )
        self.entries.append(entry)
        self.save()
        return entry

    def update(self, entry: JournalEntry, **fields: Any) -> None:
        """Change fields of an entry once the change it records is made, and save.

        :param entry: an entry of this journal.
        :param fields: the fields to set.
        """
        entry.update(fields)  # type: ignore[typeddict-item]
        self.save()

    def claim(self, path: Path) -> bool:
        """Record a path that bash-camp creates, now or at run time.

        A path that exists and is not in the journal predates bash-camp and is never claimed.

        :param path: the path.
        :return: whether the path is ours to remove on uninstall - already in the journal, taken
            over from the installation this one replaced, or not existing yet.
        """
        if self.find(path) is not None:
            return True

        if exists(path):
            return False

        self.add("created", path)
        return True

    @staticmethod
    def displace(path: Path) -> Path:
        """Move a pre-existing entry out of the way, into $CAMP_HOME/backups.

        :param path: the entry to move.
        :return: where it went.
        :raises CampError: if an earlier backup already sits there.
        """
        backup = CAMP_BACKUPS / home_relative(path)
        if exists(backup):
            raise CampError(f"Backup slot {backup} is already taken; refusing to overwrite it.")

        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(backup))
        print(f"  Backed up {display(path)} -> {display(backup)}.")
        return backup

    def revert(self, entry: JournalEntry) -> None:
        """Undo one entry, prune the directories it made necessary, and forget it.

        :param entry: an entry of this journal.
        """
        path = Path(entry["path"])
        kind = entry["kind"]
        label = display(path)

        if kind == "created":
            remove_path(path, label=label)

        elif kind in ("symlink", "file"):
            if is_ours(entry):
                remove_path(path, label=label)
            elif exists(path):
                print(f"  Kept {label}: it was changed after install.")
            _restore_backup(entry)

        elif kind == "rc_line":
            drop_lines_containing(path, RC_MARKER)
            if path.is_file():
                text = path.read_text()
                if entry.get("added_newline") and text.endswith("\n"):
                    rewrite_file(path, text[:-1])
                if entry.get("created_digest") and digest(path) == entry["created_digest"]:
                    remove_path(path, label=label)

        else:
            warnings.warn(f"Unknown journal entry kind {kind!r} for {path}; skipped.", stacklevel=2)

        prune_empty_dirs(path.parent, Path(entry["keep"]))
        self._hand_over_dirs(entry)
        self.entries.remove(entry)
        self.save()

    def _hand_over_dirs(self, entry: JournalEntry) -> None:
        """Make the directories an entry had to create the next entry's to prune, where one sits.

        Uninstall reverts newest first, so by then nothing is left in them. `camp resupply` takes a
        secret back out of that order, and a later one may still sit in a directory it created.

        :param entry: the entry being reverted.
        """
        keep = Path(entry["keep"])
        created = {parent for parent in Path(entry["path"]).parents if keep in parent.parents}
        for other in self.entries:
            if Path(other["keep"]) in created:
                other["keep"] = str(keep)


def is_ours(entry: JournalEntry) -> bool:
    """Whether the path of a "symlink" or "file" entry still holds what install put there.

    :param entry: a "symlink" or "file" entry.
    :return: False when it is gone or was changed since.
    """
    path = Path(entry["path"])
    if entry["kind"] == "symlink":
        return path.is_symlink() and str(path.readlink()) == entry["target"]
    return exists(path) and not path.is_symlink() and digest(path) == entry["digest"]


def _restore_backup(entry: JournalEntry) -> None:
    """Move a displaced original back, or next to the path if that is taken.

    :param entry: a "symlink" or "file" entry; one without a backup is left alone.
    """
    if not entry.get("backup"):
        return

    backup = Path(entry["backup"])
    if not exists(backup):
        return

    path = Path(entry["path"])
    if exists(path):
        path = path.with_name(f"{path.name}.pre-camp")
        print(f"  The original goes next to the changed file, as {display(path)}.")

    shutil.move(str(backup), str(path))
    print(f"  Restored {display(path)}.")
