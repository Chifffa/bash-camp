"""install and uninstall - `camp pitch` and `camp strike` here - and the order the steps run in.

The steps live in `build` (inside $CAMP_HOME, no journal) and `home` (outside it, through the
journal). install never updates an installation in place: it uninstalls the earlier one first and
builds everything afresh. `uninstall` has no steps of its own: it replays the journal backwards and
deletes $CAMP_HOME.
"""

from __future__ import annotations

import inspect
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .build import (
    copy_source_tree,
    install_rc_addon,
    install_sources,
    setup_bash_plugins,
    setup_essentials,
    setup_pixi,
    setup_tool_shims,
)
from .home import (
    claim_tool_state,
    hook_bashrc,
    install_fonts,
    link_configs,
    place_secrets,
    setup_tmux,
)
from .journal import Journal
from .model import CampError, JournalEntry
from .ops import (
    display,
    drop_lines_containing,
    first_existing_ancestor,
    prune_empty_dirs,
    remove_path,
)
from .paths import (
    CAMP_HOME,
    CAMP_HOME_LAYOUT,
    CAMP_JOURNAL,
    CAMP_SRC,
    PIXI_HOME,
    RC_FILE,
    RC_MARKER,
    SOURCE_HOME,
)
from .secrets_manifest import load_secrets_manifest, missing_secret_sources
from .toolchain import TOOL_STATE_PATHS


# Frames the start and the end of install and uninstall.
BANNER = "=" * 60

# The install steps, in the order they run. A step that changes anything outside $CAMP_HOME takes
# the journal; one that only builds inside it takes nothing.
INSTALL_STEPS = (
    # First, so everything after it reads the installed copy and never the checkout.
    install_sources,
    # Before anything is built or run: a build that created one of the tools' state directories
    # first would make it look like the user's, and uninstall would leave it behind.
    claim_tool_state,
    setup_pixi,
    setup_essentials,
    setup_tool_shims,
    link_configs,
    place_secrets,
    setup_bash_plugins,
    # After link_configs: TPM reads the plugin list from the linked tmux.conf.
    setup_tmux,
    install_fonts,
    install_rc_addon,
    # Last: ~/.bashrc starts sourcing the addon once everything it refers to is in place.
    hook_bashrc,
)


def install() -> int:
    """Install bash-camp from this source tree into $CAMP_HOME, replacing an earlier installation.

    The earlier installation is uninstalled first, all but the tools' run-time state: shell
    history, databases and caches stay, and the new installation takes them over.

    :return: the exit status.
    """
    if CAMP_SRC.resolve() == SOURCE_HOME:
        return _install_from_copy()

    print(BANNER)
    print(f"Installing bash-camp into {CAMP_HOME}")
    print(BANNER)

    _preflight_install()

    carried: list[JournalEntry] = []
    earlier = Journal.load()
    if earlier is None:
        camp_home_keep = (
            CAMP_HOME.parent if CAMP_HOME.exists() else first_existing_ancestor(CAMP_HOME)
        )
    else:
        print("\n>> uninstall the earlier installation")
        camp_home_keep = Path(earlier.data["camp_home_keep"])
        carried = _strike(earlier, keep_tool_state=True)

    CAMP_HOME.mkdir(parents=True, exist_ok=True)
    # $CAMP_HOME carries a copy of the secrets: owner-only, like ~/.ssh.
    CAMP_HOME.chmod(0o700)
    journal = Journal.create(camp_home_keep, carried)

    for step_fn in INSTALL_STEPS:
        print(f"\n>> {step_fn.__name__}")
        if inspect.signature(step_fn).parameters:
            step_fn(journal)
        else:
            step_fn()

    print(f"\n{BANNER}")
    print("Installation complete.")
    print("Open a new shell, or run: source ~/.bashrc.")
    print(BANNER)
    return 0


def uninstall() -> None:
    """Undo everything install did and delete $CAMP_HOME.

    :raises CampError: if $CAMP_HOME has no journal and holds entries bash-camp did not create.
    """
    print(BANNER)
    print(f"Uninstalling bash-camp from {CAMP_HOME}")
    print(BANNER)

    journal = Journal.load()
    if journal is None:
        drop_lines_containing(RC_FILE, RC_MARKER)
        if not CAMP_HOME.exists():
            print("bash-camp is not installed.")
            return
        foreign = _foreign_entries(CAMP_HOME)
        if foreign:
            raise CampError(
                f"{CAMP_HOME} holds unexpected entries ({', '.join(foreign)}); not deleting it."
            )
        remove_path(CAMP_HOME, label=display(CAMP_HOME))
        return

    _strike(journal, keep_tool_state=False)

    print(f"\n{BANNER}")
    print("Uninstallation complete; the home directory is back to its pre-install state.")
    print("Open a new shell to pick up the change.")
    print(BANNER)


def _install_from_copy() -> int:
    """Run install again, from a temporary copy of the installed source tree.

    install replaces $CAMP_HOME/src - the tree `camp pitch`, and the remote install of a deploy,
    run from - and the uninstall it starts with deletes it altogether.

    :return: the exit status of that install.
    """
    print("Running from the installed copy; installing from a temporary copy of it.", flush=True)
    with tempfile.TemporaryDirectory(prefix="bash-camp-") as temp_dir:
        copy = Path(temp_dir) / "src"
        copy_source_tree(copy)
        command = [sys.executable, str(copy / "bootstrap.py"), "pitch"]
        return subprocess.run(command, cwd=temp_dir, check=False).returncode


def _strike(journal: Journal, *, keep_tool_state: bool) -> list[JournalEntry]:
    """Revert the journal and delete $CAMP_HOME.

    The journal is replayed newest first, so every directory install had to create is pruned only
    after everything later placed inside it is gone.

    :param journal: the journal of the installation.
    :param keep_tool_state: leave the tools' run-time state in place, for the installation that
        replaces this one to take over - and the private pixi, with the Python bash-camp may be
        running on.
    :return: the entries left in place; empty without keep_tool_state.
    """
    kept = [entry for entry in journal.entries if keep_tool_state and _is_tool_state(entry)]
    if kept:
        print("  Keeping the tools' history, databases and caches for the new installation.")

    for entry in reversed(list(journal.entries)):
        if entry not in kept:
            journal.revert(entry)

    if not keep_tool_state:
        remove_path(CAMP_HOME, label=display(CAMP_HOME))
        prune_empty_dirs(CAMP_HOME.parent, Path(journal.data["camp_home_keep"]))
        return kept

    for path in CAMP_HOME.iterdir():
        if path != PIXI_HOME:
            remove_path(path)
    print(f"  Removed {display(CAMP_HOME)}, all but its pixi.")
    return kept


def _is_tool_state(entry: JournalEntry) -> bool:
    """Whether an entry claims one of the tools' run-time state paths.

    :param entry: a journal entry.
    :return: True for a "created" entry of a path in TOOL_STATE_PATHS.
    """
    return entry["kind"] == "created" and Path(entry["path"]) in TOOL_STATE_PATHS


def _preflight_install() -> None:
    """Refuse to start an install that could not finish or would clobber something.

    Everything here is checked before the first change - before an earlier installation is
    uninstalled, too - so a refusal leaves the machine exactly as it was.

    :raises CampError: listing every problem found, not just the first.
    """
    problems: list[str] = []

    if CAMP_HOME.exists() and not CAMP_JOURNAL.is_file():
        foreign = _foreign_entries(CAMP_HOME)
        if foreign:
            problems.append(
                f"{CAMP_HOME} exists and is not a bash-camp home ({', '.join(foreign)})."
            )

    if CAMP_HOME in (SOURCE_HOME, *SOURCE_HOME.parents) or SOURCE_HOME in CAMP_HOME.parents:
        problems.append(
            f"$CAMP_HOME ({CAMP_HOME}) and the source tree ({SOURCE_HOME}) must not nest."
        )

    try:
        entries = load_secrets_manifest(SOURCE_HOME / "secrets")
    except CampError as error:
        problems.append(str(error))
    else:
        problems.extend(missing_secret_sources(SOURCE_HOME / "secrets", entries))

    problems.extend(
        f"{tool} is required but not found."
        for tool in ("curl", "tar")
        if shutil.which(tool) is None
    )

    if problems:
        bullets = "".join(f"\n  - {problem}" for problem in problems)
        raise CampError(f"Cannot install:{bullets}")


def _foreign_entries(camp_home: Path) -> list[str]:
    """Names in a would-be $CAMP_HOME that bash-camp does not create.

    :param camp_home: the directory.
    :return: the names, sorted; empty when the directory is ours to delete.
    """
    return sorted({path.name for path in camp_home.iterdir()} - CAMP_HOME_LAYOUT)
