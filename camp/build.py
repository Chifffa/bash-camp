"""The install steps that build inside $CAMP_HOME.

None of them changes anything outside it, so none of them takes the journal: uninstall deletes
$CAMP_HOME as a whole, and with it everything built here. They build into an empty $CAMP_HOME -
install uninstalls an earlier installation first - so none of them has an earlier build to update.
The one exception is the private pixi `camp pitch HOST` may have brought already, with an rsync.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import warnings
from pathlib import Path

from .model import CampError
from .ops import display, prune_empty_dirs, remove_path, restrict_tree, rewrite_file, sh
from .paths import (
    BLESH_HOME,
    CAMP_BIN,
    CAMP_ENV_FILES,
    CAMP_HOME,
    CAMP_RC_ADDON,
    CAMP_RC_ADDON_SOURCE,
    CAMP_SECRETS,
    CAMP_SRC,
    DEV_TOOLS_BIN,
    DEV_TOOLS_DIR,
    DEV_TOOLS_MANIFEST,
    DEV_TOOLS_SHIMS,
    PIXI_CACHE_DIR,
    PIXI_CONFIG,
    PIXI_EXE,
    PIXI_HOME,
    SOURCE_HOME,
    SOURCE_IGNORE_PATTERNS,
    SOURCE_ITEMS,
)
from .secrets_manifest import load_secrets_manifest
from .toolchain import (
    FALLBACK_TOOLS,
    PIXI_CONFIG_TOML,
    PIXI_INSTALL_URL,
    PIXI_PACKAGES,
    SHIMMED_EXECUTABLES,
)


def install_sources() -> None:
    """Copy the source tree into $CAMP_HOME/src.

    Everything installed afterwards - config symlinks, bin/ on PATH, secrets - refers to this copy
    and never to the checkout.
    """
    print("Copying sources...")

    # On a remote host, `camp pitch HOST` has rsynced the tree here; this copy replaces it.
    remove_path(CAMP_SRC)
    copy_source_tree(CAMP_SRC)
    print(f"  Copied {SOURCE_HOME} -> {display(CAMP_SRC)}.")

    # The installed copy of the secrets is readable by the owner only.
    if CAMP_SECRETS.is_dir():
        restrict_tree(CAMP_SECRETS, file_mode=0o600)

    if CAMP_BIN.is_dir():
        for exe_path in CAMP_BIN.iterdir():
            exe_path.chmod(exe_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_secrets() -> None:
    """Replace the installed copy of secrets/ with the source tree's - all `camp resupply` copies.

    Run from the installed copy - on a remote host, where `camp resupply HOST` has just rsynced
    secrets/ into it - there is nothing to copy, only modes to tighten.
    """
    print("Copying secrets...")

    source = SOURCE_HOME / "secrets"
    if CAMP_SRC.resolve() == SOURCE_HOME:
        print(f"  Running from {display(CAMP_SRC)}; its secrets are the ones placed.")
    else:
        remove_path(CAMP_SECRETS)
        if source.is_dir():
            ignore = shutil.ignore_patterns(*SOURCE_IGNORE_PATTERNS)
            shutil.copytree(source, CAMP_SECRETS, ignore=ignore)
        print(f"  Copied {source} -> {display(CAMP_SECRETS)}.")

    if CAMP_SECRETS.is_dir():
        restrict_tree(CAMP_SECRETS, file_mode=0o600)


def copy_source_tree(destination: Path) -> None:
    """Copy SOURCE_ITEMS of the source tree, without caches.

    :param destination: the directory to create; it must not exist yet.
    """
    destination.mkdir(parents=True)
    ignore = shutil.ignore_patterns(*SOURCE_IGNORE_PATTERNS)
    for name in SOURCE_ITEMS:
        source = SOURCE_HOME / name
        if source.is_dir():
            shutil.copytree(source, destination / name, ignore=ignore)
        elif source.is_file():
            shutil.copy2(source, destination / name)


def setup_pixi() -> None:
    """Install bash-camp's private copy of the pixi package manager, and its configuration.

    Pixi is a fast, cross-platform package manager that provides conda-compatible environments
    without requiring conda itself.
    """
    if PIXI_EXE.exists():
        # Brought already: by bootstrap.py for a private Python, by `camp pitch HOST` for a
        # private rsync, or kept from the installation this one replaces.
        print(f"Pixi already installed at {display(PIXI_EXE)}.")
    else:
        _install_pixi()
    rewrite_file(PIXI_CONFIG, PIXI_CONFIG_TOML)


def _install_pixi() -> None:
    """Download and run pixi's installer, into $CAMP_HOME/pixi.

    :raises CampError: without curl.
    """
    print("Installing Pixi package manager...")

    curl_exe = shutil.which("curl")
    if curl_exe is None:
        raise CampError("curl is required but not found. Install it first.")

    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fout:
        temp_script = fout.name

    try:
        sh([curl_exe, "-fsSL", "--output", temp_script, PIXI_INSTALL_URL])
        sh(["bash", temp_script], env=_pixi_env())
    finally:
        Path(temp_script).unlink(missing_ok=True)


def setup_essentials() -> None:
    """Install the toolchain into the dev-tools pixi environment.

    That is PIXI_PACKAGES, and the FALLBACK_TOOLS where the system lacks them.
    """
    print("Installing essential tools via Pixi...")

    fallbacks = _missing_system_tools()
    if fallbacks:
        print(f"  Not provided by this system, so installed too: {', '.join(fallbacks)}.")

    DEV_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    if not DEV_TOOLS_MANIFEST.exists():
        sh([str(PIXI_EXE), "init", "."], cwd=DEV_TOOLS_DIR, env=_pixi_env())
    sh([str(PIXI_EXE), "add", *PIXI_PACKAGES, *fallbacks], cwd=DEV_TOOLS_DIR, env=_pixi_env())

    # The package cache would roughly double the footprint of $CAMP_HOME (about 1 GB).
    # The environment keeps its own (hard-linked) copies, and the next install starts over anyway.
    # It holds the downloads of the private Python and rsync, too, which pixi made before this. A
    # cache the user pointed $PIXI_CACHE_DIR at is theirs and stays.
    if "PIXI_CACHE_DIR" not in os.environ:
        remove_path(PIXI_CACHE_DIR, label="the private pixi package cache")
        prune_empty_dirs(PIXI_CACHE_DIR.parent, CAMP_HOME)


def setup_tool_shims() -> None:
    """Publish the curated set of pixi executables as symlinks in dev-tools/shims.

    Only this directory goes on PATH, never the pixi env's own bin/. See the comment on
    SHIMMED_EXECUTABLES for why that distinction matters.
    """
    print("Publishing tool shims...")

    DEV_TOOLS_SHIMS.mkdir(parents=True, exist_ok=True)

    names = (*SHIMMED_EXECUTABLES, *(FALLBACK_TOOLS[name] for name in _missing_system_tools()))
    missing: list[str] = []
    for name in names:
        target = DEV_TOOLS_BIN / name
        if not target.exists():
            missing.append(name)
            continue

        # Relative, so the links keep resolving wherever $CAMP_HOME is mounted: a container sees
        # it under its own $HOME, not under the host's.
        relative_target = os.path.relpath(target, DEV_TOOLS_SHIMS)
        (DEV_TOOLS_SHIMS / name).symlink_to(relative_target)

    print(f"  Linked {len(names) - len(missing)} tools into {display(DEV_TOOLS_SHIMS)}.")
    if missing:
        warnings.warn(
            f"Not provided by the pixi environment, skipped: {', '.join(missing)}.", stacklevel=2
        )


def setup_bash_plugins() -> None:
    """Build ble.sh, which pixi does not have, into $CAMP_HOME/blesh.

    It is built from source with its own installer, so the RC addon can source a stable path, and
    then kept from announcing its terminal cache.
    """
    print("Installing bash plugins...")

    with tempfile.TemporaryDirectory(prefix="bash-camp-blesh-") as temp_dir:
        repo_path = Path(temp_dir) / "ble.sh"
        # git comes from the system, or from the shims where it has none.
        clone_env = {**os.environ, "PATH": f"{DEV_TOOLS_SHIMS}:{os.environ.get('PATH', '')}"}
        # The build needs GNU awk from the pixi env, and make from the system or, where it has
        # none, from the env too; so it gets the full env bin on PATH. This is scoped to the build
        # subprocess only; the interactive shell still sees just dev-tools/shims.
        build_env = {**os.environ, "PATH": f"{DEV_TOOLS_BIN}:{os.environ.get('PATH', '')}"}

        try:
            sh(
                [
                    "git",
                    "clone",
                    "-q",
                    "--recursive",
                    "--depth",
                    "1",
                    "--shallow-submodules",
                    "https://github.com/akinomyoga/ble.sh.git",
                    str(repo_path),
                ],
                env=clone_env,
            )
            sh(["make", "-C", str(repo_path), "install", f"INSDIR={BLESH_HOME}"], env=build_env)
        except subprocess.CalledProcessError as error:
            warnings.warn(f"Failed to install ble.sh: {error}.", stacklevel=2)
            return

    _silence_blesh_term_cache()


def install_rc_addon() -> None:
    """Install the shell RC addon that configures the environment, and the env files it loads.

    The addon is sourced by the user's ~/.bashrc and sets up PATH, environment variables, shell
    plugins, aliases, and tools; bash is the only supported shell. It is camp/rc-addon.sh, copied
    verbatim: every path in it is resolved at run time, relative to where it finds itself. The
    one thing that differs per installation, which secrets to export, goes into a list it reads.
    """
    print("Installing RC addon...")

    rewrite_file(CAMP_RC_ADDON, CAMP_RC_ADDON_SOURCE.read_text())
    print(f"  Installed {display(CAMP_RC_ADDON)}.")
    install_env_files()


def install_env_files() -> None:
    """List the "load": "env" secrets in $CAMP_HOME/state/env-files, for the RC addon to export."""
    env_files = [
        str((CAMP_SECRETS / entry.source).relative_to(CAMP_HOME))
        for entry in load_secrets_manifest(CAMP_SECRETS)
        if entry.load == "env"
    ]
    rewrite_file(CAMP_ENV_FILES, "".join(f"{path}\n" for path in env_files))
    print(f"  The RC addon loads {len(env_files)} env file(s).")


def _silence_blesh_term_cache() -> None:
    """Drop ble.sh's notice about building a terminal's cache.

    ble.sh announces each cache it builds - once per terminal type, so after every install - and
    writes the notice to /dev/tty itself, so the RC addon cannot silence it like the rest. Nothing
    but the two notice lines goes; a ble.sh that words them differently is left as it is.
    """
    init_term = BLESH_HOME / "lib" / "init-term.sh"
    if not init_term.is_file():
        return

    lines = init_term.read_text().splitlines(keepends=True)
    kept = [line for line in lines if "updating tput cache" not in line]
    if len(kept) < len(lines):
        rewrite_file(init_term, "".join(kept))


def _pixi_env() -> dict[str, str]:
    """Environment for every pixi invocation: private home, private cache, no RC edits.

    :return: the current environment with pixi's variables set.
    """
    return {
        **os.environ,
        "PIXI_HOME": str(PIXI_HOME),
        "PIXI_CACHE_DIR": str(PIXI_CACHE_DIR),
        "PIXI_NO_PATH_UPDATE": "1",
    }


def _missing_system_tools() -> list[str]:
    """The FALLBACK_TOOLS this system does not provide, which pixi provides instead.

    Asked of PATH minus everything in $CAMP_HOME: an install run from a bash-camp shell must not
    take a tool bash-camp itself put on PATH for the system's.

    :return: the package names, in FALLBACK_TOOLS order.
    """
    system_path = os.pathsep.join(
        entry
        for entry in os.environ.get("PATH", "").split(os.pathsep)
        if entry and CAMP_HOME not in (Path(entry).resolve(), *Path(entry).resolve().parents)
    )
    return [
        package
        for package, executable in FALLBACK_TOOLS.items()
        if shutil.which(executable, path=system_path) is None
    ]
