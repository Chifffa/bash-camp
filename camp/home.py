"""The install steps that change the home directory.

Each one takes the journal and records every change in it before making it, with whatever the
change displaces moved into $CAMP_HOME/backups, so that uninstall can put the home directory back
exactly as it was. The journal is a fresh one - install uninstalls an earlier installation first -
so a path is never found in it already, except the tools' run-time state that one handed over.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import warnings
from pathlib import Path

from .journal import Journal, is_ours
from .model import CampError, SecretEntry
from .ops import (
    digest,
    display,
    drop_lines_containing,
    exists,
    make_private_dirs,
    remove_path,
    restrict_tree,
    rewrite_file,
    sh,
)
from .paths import (
    CAMP_CONFIG,
    CAMP_FONTS,
    CAMP_RC_ADDON,
    CAMP_SECRETS,
    DEV_TOOLS_SHIMS,
    FONTS_LINK,
    HOME,
    RC_FILE,
    RC_MARKER,
    SECRETS_MANIFEST,
    TMUX_PLUGINS_HOME,
    XDG_CONFIG_HOME,
)
from .secrets_manifest import load_secrets_manifest
from .toolchain import NERD_FONTS, NERD_FONTS_RELEASE, TOOL_STATE_PATHS


def claim_tool_state(journal: Journal) -> None:
    """Record the run-time state directories that do not exist yet.

    The tools write caches, history and settings of their own on first use, which is after install
    has returned. Recording now which of those paths are absent lets uninstall remove exactly them -
    and keep the ones that were already there because the user ran the same tools before bash-camp.

    :param journal: the journal of this install.
    """
    print("Recording tool state directories...")

    # A config/ entry of the same name is linked instead, and journaled as such.
    linked = {XDG_CONFIG_HOME / path.name for path in _config_sources()}
    candidates = [path for path in TOOL_STATE_PATHS if path not in linked]
    claimed = [path for path in candidates if journal.claim(path)]
    print(f"  {len(claimed)} of {len(candidates)} are bash-camp's; uninstall will remove those.")


def link_configs(journal: Journal) -> None:
    """Symlink every entry of config/ into ~/.config.

    Whatever already sits at a link's place is moved into $CAMP_HOME/backups and comes back on
    uninstall. The links are absolute: they then survive a ~/.config that is itself a symlink, and
    a container that bind-mounts the host's home at the same path resolves them too.

    :param journal: the journal of this install.
    """
    print("Linking configs...")

    for source in _config_sources():
        _link(journal, XDG_CONFIG_HOME / source.name, source)


def place_secrets(journal: Journal) -> None:
    """Copy the files secrets/manifest.json lists to their targets.

    Real copies, not symlinks: the targets are often bind-mounted into containers, where a link
    back into $CAMP_HOME may not resolve, and some tools refuse symlinked credentials. Entries that
    "load" an env file are not placed at all - the RC addon sources them straight from
    $CAMP_HOME/src.

    :param journal: the journal of this install.
    :raises CampError: if a listed source is missing and not local-only.
    """
    print("Placing secrets...")

    entries = load_secrets_manifest(CAMP_SECRETS)
    placeable = _placeable_secrets(entries)
    for target, entry in placeable.items():
        _place(journal, target, CAMP_SECRETS / entry.source, entry.mode)

    env_files = sum(1 for entry in entries if entry.load == "env")
    print(f"  {len(placeable)} placed, {env_files} env file(s) loaded by the RC addon.")


def resupply_secrets(journal: Journal) -> None:
    """Bring the placed secrets in line with secrets/manifest.json, and nothing else.

    It ends where installing again would, without the reinstall: a secret no longer listed, or
    local-only and absent here, is taken back as uninstall takes it back; one still listed is copied
    over in place, the backup of what it displaced kept for uninstall; a new one is placed as
    install places it. A placed secret changed here since is kept, as uninstall keeps it.

    :param journal: the journal of the installation.
    :raises CampError: if a listed source is missing and not local-only.
    """
    print("Resupplying secrets...")

    entries = load_secrets_manifest(CAMP_SECRETS)
    wanted = _placeable_secrets(entries)
    placed = {Path(entry["path"]): entry for entry in journal.entries if entry["kind"] == "file"}

    # Newest first, as uninstall goes: a later secret may sit in a directory an earlier one made.
    for path, journal_entry in reversed(placed.items()):
        if path not in wanted:
            journal.revert(journal_entry)

    unchanged = 0
    for target, entry in wanted.items():
        source = CAMP_SECRETS / entry.source
        journal_entry = placed.get(target)
        if journal_entry is None:
            _place(journal, target, source, entry.mode)
        elif exists(target) and not is_ours(journal_entry):
            print(f"  Kept {display(target)}: it was changed since; delete it to take the new one.")
        else:
            previous = journal_entry["digest"] if exists(target) else None
            remove_path(target)
            _copy_secret(target, source, entry.mode)
            journal.update(journal_entry, digest=digest(target))
            if journal_entry["digest"] == previous:
                unchanged += 1
            else:
                print(f"  Updated {display(target)} ({entry.mode:03o}).")

    env_files = sum(1 for entry in entries if entry.load == "env")
    print(f"  {unchanged} unchanged, {env_files} env file(s) loaded by the RC addon.")


def setup_tmux(journal: Journal) -> None:
    """Install the Tmux Plugin Manager (TPM) and the plugins tmux.conf declares.

    tmux itself is the system's, or pixi's where the system has none - see FALLBACK_TOOLS. TPM and
    every plugin directory that does not exist yet are claimed before TPM runs, so uninstall
    removes exactly what this step brought in.

    :param journal: the journal of this install.
    """
    print("Setting up tmux...")

    # TPM runs tmux and git: the shims are where pixi's are, where the system has none.
    tpm_path = f"{DEV_TOOLS_SHIMS}{os.pathsep}{os.environ.get('PATH', '')}"
    if shutil.which("tmux", path=tpm_path) is None:
        print("  tmux is not available; skipping TPM and plugins.")
        return

    tpm_home = TMUX_PLUGINS_HOME / "tpm"
    for name in ("tpm", *_tmux_plugin_names()):
        journal.claim(TMUX_PLUGINS_HOME / name)

    if not tpm_home.is_dir():
        print("  Cloning Tmux Plugin Manager...")
        sh(
            ["git", "clone", "-q", "https://github.com/tmux-plugins/tpm", str(tpm_home)],
            env={**os.environ, "PATH": tpm_path},
        )

    # Install plugins defined in tmux.conf.
    install_script = tpm_home / "bin" / "install_plugins"
    if install_script.exists():
        try:
            sh(
                ["bash", str(install_script)],
                env={
                    **os.environ,
                    "PATH": tpm_path,
                    "TMUX_PLUGIN_MANAGER_PATH": f"{TMUX_PLUGINS_HOME}/",
                },
                cwd=tpm_home,
            )
        except subprocess.CalledProcessError:
            warnings.warn(
                f"TPM plugin installation failed. Run manually: bash {install_script}.",
                stacklevel=2,
            )


def install_fonts(journal: Journal) -> None:
    """Unpack the Nerd Fonts into $CAMP_HOME/fonts and link them where fontconfig looks.

    Only on a machine with a display: the terminal draws the icons, so a font helps only where it
    runs - never on a host reached over ssh, or in a container. An archive that fails to download
    or to match its digest is skipped with a warning; icons are not worth failing install over.

    :param journal: the journal of this install.
    """
    print("Installing fonts...")

    fc_cache = shutil.which("fc-cache")
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) or fc_cache is None:
        print("  No display or no fontconfig; skipped.")
        return

    for archive, (sha256, members) in NERD_FONTS.items():
        try:
            _unpack_fonts(archive, sha256, members)
        except (CampError, OSError, subprocess.CalledProcessError, tarfile.TarError) as error:
            warnings.warn(f"Skipped {archive}: {error}", stacklevel=2)
    if not CAMP_FONTS.is_dir():
        return

    _link(journal, FONTS_LINK, CAMP_FONTS)
    sh([fc_cache])


def hook_bashrc(journal: Journal) -> None:
    """Make ~/.bashrc source the RC addon.

    A missing ~/.bashrc is created from /etc/skel first: distro images ship one, but freshly
    created container users (or homes bind-mounted over) can lack it. What the file looked like
    before is recorded - created or not, whether it ended in a newline - so that uninstall restores
    it byte for byte.

    :param journal: the journal of this install.
    """
    print("Hooking ~/.bashrc...")

    created_digest = None
    if not exists(RC_FILE):
        skel_bashrc = Path("/etc/skel/.bashrc")
        if skel_bashrc.is_file():
            shutil.copy2(skel_bashrc, RC_FILE)
        else:
            RC_FILE.write_text("case $- in *i*) ;; *) return ;; esac\n")
        created_digest = digest(RC_FILE)
        print(f"  Created {display(RC_FILE)}.")

    text = RC_FILE.read_text()
    journal.add(
        "rc_line",
        RC_FILE,
        created_digest=created_digest,
        added_newline=bool(text) and not text.endswith("\n"),
    )

    # A line left by an installation whose journal is gone would source the addon twice.
    drop_lines_containing(RC_FILE, RC_MARKER, quiet=True)
    text = RC_FILE.read_text()
    separator = "\n" if text and not text.endswith("\n") else ""
    rewrite_file(RC_FILE, f"{text}{separator}{_rc_source_line()}\n")
    print(f"  {display(RC_FILE)} sources {display(CAMP_RC_ADDON)}.")


def _rc_source_line() -> str:
    """The line hook_bashrc appends to ~/.bashrc, tagged with RC_MARKER.

    :return: the line, without its newline.
    """
    addon = CAMP_RC_ADDON
    if HOME in addon.parents:
        addon = Path("$HOME") / addon.relative_to(HOME)
    return f'if [ -f "{addon}" ]; then . "{addon}"; fi  {RC_MARKER}'


def _config_sources() -> list[Path]:
    """The entries of the installed config/ that get linked into ~/.config.

    :return: their paths, sorted; dot files excluded.
    """
    if not CAMP_CONFIG.is_dir():
        return []
    return [path for path in sorted(CAMP_CONFIG.iterdir()) if not path.name.startswith(".")]


def _link(journal: Journal, link: Path, target: Path) -> None:
    """Point a symlink at a file or directory in $CAMP_HOME, journaling what it displaces.

    :param journal: the journal of this install.
    :param link: where the link goes.
    :param target: what it points at.
    """
    backup = journal.displace(link) if exists(link) else None
    journal.add("symlink", link, target=str(target), backup=str(backup) if backup else None)

    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target, target_is_directory=target.is_dir())
    print(f"  Linked {display(link)}.")


def _unpack_fonts(archive: str, sha256: str, members: tuple[str, ...]) -> None:
    """Download a Nerd Fonts archive, check it, and unpack the files kept from it.

    :param archive: the release asset's name.
    :param sha256: its expected SHA-256.
    :param members: the files to keep.
    :raises CampError: if the download does not match its digest.
    """
    destination = CAMP_FONTS / archive.removesuffix(".tar.xz")
    with tempfile.TemporaryDirectory(prefix="bash-camp-") as temp_dir:
        download = Path(temp_dir) / archive
        sh(["curl", "-fsSL", "--output", str(download), f"{NERD_FONTS_RELEASE}/{archive}"])
        if digest(download) != sha256:
            raise CampError("the download does not match its digest")

        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(download, "r:xz") as tar:
            kept = [tar.getmember(name) for name in members]
            tar.extractall(destination, members=kept, filter="data")

    print(f"  Unpacked {display(destination)}.")


def _place(journal: Journal, target: Path, source: Path, mode: int) -> None:
    """Copy a secret file or directory to its target, journaling what it displaces.

    :param journal: the journal of this install.
    :param target: where the copy goes.
    :param source: the file or directory in $CAMP_HOME/src/secrets.
    :param mode: permissions of the placed files; directories get 0700.
    """
    backup = journal.displace(target) if exists(target) else None
    entry = journal.add("file", target, digest=None, backup=str(backup) if backup else None)

    _copy_secret(target, source, mode)

    journal.update(entry, digest=digest(target))
    print(f"  Placed {display(target)} ({mode:03o}).")


def _copy_secret(target: Path, source: Path, mode: int) -> None:
    """Copy a secret file or directory to a free target, owner-only.

    :param target: where the copy goes; nothing may sit there.
    :param source: the file or directory in $CAMP_HOME/src/secrets.
    :param mode: permissions of the copied files; directories get 0700.
    """
    make_private_dirs(target.parent)
    if source.is_dir():
        shutil.copytree(source, target)
        restrict_tree(target, file_mode=mode)
    else:
        shutil.copyfile(source, target)
        target.chmod(mode)


def _placeable_secrets(entries: list[SecretEntry]) -> dict[Path, SecretEntry]:
    """The manifest's entries that are placed here: those with a target and a source present.

    :param entries: the manifest's entries.
    :return: the entries by target, in manifest order.
    :raises CampError: if a listed source is missing and not local-only.
    """
    placeable: dict[Path, SecretEntry] = {}
    for entry in entries:
        if entry.target is None:
            continue
        source = CAMP_SECRETS / entry.source
        if not exists(source):
            if entry.local_only:
                print(f"  Skipped {entry.source}: local-only and not present here.")
                continue
            raise CampError(f"{source} is listed in {SECRETS_MANIFEST} but does not exist.")
        placeable[entry.target] = entry
    return placeable


def _tmux_plugin_names() -> list[str]:
    """Directory names TPM gives the plugins tmux.conf declares, TPM itself excluded.

    :return: the names, in tmux.conf order, without duplicates.
    """
    tmux_conf = CAMP_CONFIG / "tmux" / "tmux.conf"
    if not tmux_conf.is_file():
        return []

    pattern = re.compile(r'^\s*set(?:-option)?\s+-g\s+@plugin\s+["\']([^"\']+)["\']')
    names: list[str] = []
    for line in tmux_conf.read_text().splitlines():
        match = pattern.match(line)
        if match:
            # 'catppuccin/tmux#v2.1.0' is cloned into tmux/.
            name = match.group(1).split("#", 1)[0].rstrip("/").split("/")[-1]
            if name and name != "tpm" and name not in names:
                names.append(name)

    return names
