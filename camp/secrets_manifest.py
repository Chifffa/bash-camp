"""secrets/manifest.json: which files of the private overlay go where.

secrets/ holds the credentials, keys and env files of the machine the checkout lives on. Validation
is strict on purpose: a typo in a key would otherwise silently leave a credential unplaced, and that
only shows up later as an obscure authentication failure. secrets.schema.json mirrors these rules
for editors; this module is what enforces them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .model import CampError, SecretEntry
from .ops import display, exists
from .paths import CAMP_HOME, HOME, SECRETS_MANIFEST


if TYPE_CHECKING:
    from collections.abc import Iterable


SECRET_ENTRY_KEYS = frozenset(("source", "target", "load", "mode", "local_only", "comment"))


def load_secrets_manifest(secrets_dir: Path) -> list[SecretEntry]:
    """Parse and validate secrets/manifest.json; no manifest means no secrets.

    :param secrets_dir: the secrets/ directory.
    :return: the entries, in manifest order.
    :raises CampError: if the manifest is malformed.
    """
    manifest = secrets_dir / SECRETS_MANIFEST
    if not manifest.is_file():
        return []

    try:
        data = json.loads(manifest.read_text())
    except json.JSONDecodeError as error:
        raise CampError(f"{manifest}: invalid JSON: {error}.") from error

    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise CampError(f'{manifest}: expected an object with a "files" list.')
    # "$schema" and "_..." keys are for editors and humans.
    unknown = [key for key in data if key != "files" and not key.startswith(("$", "_"))]
    if unknown:
        raise CampError(f"{manifest}: unknown top-level keys: {', '.join(unknown)}.")

    entries: list[SecretEntry] = []
    for index, raw in enumerate(data["files"]):
        entry = _parse_entry(raw, where=f"{manifest}: files[{index}]")
        clash = next(
            (seen for seen in entries if entry.target and seen.target == entry.target), None
        )
        if clash is not None and entry.target is not None:
            raise CampError(
                f'{manifest}: files[{index}]: "target" {display(entry.target)} is also used by'
                f" {clash.source}."
            )
        entries.append(entry)
    return entries


def missing_secret_sources(secrets_dir: Path, entries: Iterable[SecretEntry]) -> list[str]:
    """The entries whose source is missing, except the local-only ones, which may be.

    :param secrets_dir: the secrets/ directory the sources are relative to.
    :param entries: the manifest's entries.
    :return: one problem line per missing source.
    """
    return [
        f"{secrets_dir / entry.source} is listed in {SECRETS_MANIFEST} but does not exist."
        for entry in entries
        if not entry.local_only and not exists(secrets_dir / entry.source)
    ]


def _parse_entry(raw: Any, where: str) -> SecretEntry:
    """Validate one entry of the manifest's "files" list.

    :param raw: the entry, as parsed from JSON.
    :param where: the entry's location, for the error messages.
    :return: the validated entry, its target resolved under the home directory.
    :raises CampError: if the entry is malformed.
    """
    if not isinstance(raw, dict):
        raise CampError(f"{where}: expected an object.")
    unknown = sorted(set(raw) - SECRET_ENTRY_KEYS)
    if unknown:
        raise CampError(f"{where}: unknown keys: {', '.join(unknown)}.")

    source = raw.get("source")
    if not isinstance(source, str) or not source:
        raise CampError(f'{where}: "source" must be a non-empty string.')
    if Path(source).is_absolute() or ".." in Path(source).parts or source == SECRETS_MANIFEST:
        raise CampError(f'{where}: "source" must be a path inside secrets/.')

    target, load = raw.get("target"), raw.get("load")
    if (target is None) == (load is None):
        raise CampError(f'{where}: exactly one of "target" and "load" is required.')
    if load is not None and load != "env":
        raise CampError(f'{where}: "load" only supports "env".')

    target_path = None
    if target is not None:
        if not isinstance(target, str) or not target.startswith("~/") or len(target) < 3:
            raise CampError(f'{where}: "target" must be a path under the home directory, "~/...".')
        if ".." in Path(target[2:]).parts:
            raise CampError(f'{where}: "target" must not contain "..".')
        target_path = HOME / target[2:]
        if target_path == CAMP_HOME or CAMP_HOME in target_path.parents:
            raise CampError(f'{where}: "target" must not point into {CAMP_HOME}.')

    mode = raw.get("mode", "600")
    if not isinstance(mode, str) or not re.fullmatch(r"0?[0-7]{3}", mode):
        raise CampError(f'{where}: "mode" must be an octal string such as "600".')

    local_only = raw.get("local_only", False)
    if not isinstance(local_only, bool):
        raise CampError(f'{where}: "local_only" must be true or false.')

    if not isinstance(raw.get("comment", ""), str):
        raise CampError(f'{where}: "comment" must be a string.')

    return SecretEntry(
        source=source, target=target_path, load=load, mode=int(mode, 8), local_only=local_only
    )
