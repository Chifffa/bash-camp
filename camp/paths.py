"""Where everything lives: the source tree, $CAMP_HOME and its layout, and the home directory.

Every path is computed once, at import, from $HOME, $CAMP_HOME and the XDG variables. A trial run
in a throwaway home therefore only needs a different $HOME.
"""

from __future__ import annotations

import os
from pathlib import Path


HOME = Path.home()


# ------------------------------------------------------------------------------------------------
# The source tree
# ------------------------------------------------------------------------------------------------

# Wherever bootstrap.py lives: a git checkout or $CAMP_HOME/src.
SOURCE_HOME = Path(__file__).resolve().parents[1]

# What install copies into $CAMP_HOME/src and what deploy ships to remote hosts.
SOURCE_ITEMS = ("bootstrap.py", "camp", "bin", "config", "secrets")
SOURCE_IGNORE_PATTERNS = ("__pycache__", "*.pyc", ".ruff_cache", ".rumdl_cache", ".mypy_cache")
SECRETS_MANIFEST = "manifest.json"


# ------------------------------------------------------------------------------------------------
# $CAMP_HOME
#
# Everything bash-camp builds lives here, so that neither the location of the checkout nor its
# later removal affects the environment.
# ------------------------------------------------------------------------------------------------

CAMP_HOME = Path(os.environ.get("CAMP_HOME") or HOME / ".camp").expanduser().resolve()
CAMP_SRC = CAMP_HOME / "src"
CAMP_BIN = CAMP_SRC / "bin"
CAMP_CONFIG = CAMP_SRC / "config"
CAMP_SECRETS = CAMP_SRC / "secrets"

# What ~/.bashrc sources: camp/rc-addon.sh, copied verbatim. It finds $CAMP_HOME from its own
# location, so it has to sit at the top of it.
CAMP_RC_ADDON = CAMP_HOME / "rc-addon.sh"
CAMP_RC_ADDON_SOURCE = CAMP_SRC / "camp" / "rc-addon.sh"
CAMP_STATE = CAMP_HOME / "state"

# The env files the RC addon exports into every shell, one $CAMP_HOME-relative path per line.
CAMP_ENV_FILES = CAMP_STATE / "env-files"
CAMP_JOURNAL = CAMP_STATE / "journal.json"
CAMP_BACKUPS = CAMP_HOME / "backups"

# Pixi is private to bash-camp: its own binary, its own package cache, and no PATH line written
# into the RC files by pixi's installer. A pixi that the user or the system already has is neither
# used nor touched. An explicitly exported $PIXI_CACHE_DIR is honoured - that cache is the user's,
# so uninstall leaves it.
PIXI_HOME = CAMP_HOME / "pixi"
PIXI_EXE = PIXI_HOME / "bin" / "pixi"
PIXI_CONFIG = PIXI_HOME / "config.toml"
PIXI_CACHE_DIR = Path(os.environ.get("PIXI_CACHE_DIR") or CAMP_HOME / "cache" / "pixi")
DEV_TOOLS_DIR = CAMP_HOME / "dev-tools"
DEV_TOOLS_MANIFEST = DEV_TOOLS_DIR / "pixi.toml"
DEV_TOOLS_ENV = DEV_TOOLS_DIR / ".pixi" / "envs" / "default"
DEV_TOOLS_BIN = DEV_TOOLS_ENV / "bin"
DEV_TOOLS_SHIMS = DEV_TOOLS_DIR / "shims"
BLESH_HOME = CAMP_HOME / "blesh"
CAMP_FONTS = CAMP_HOME / "fonts"

# Top-level names install creates in $CAMP_HOME; anything else in there means the directory is not
# ours and must not be deleted.
CAMP_HOME_LAYOUT = frozenset(
    (
        "src",
        "state",
        "backups",
        "pixi",
        "cache",
        "dev-tools",
        "blesh",
        "fonts",
        CAMP_RC_ADDON.name,
    )
)


# ------------------------------------------------------------------------------------------------
# The home directory
# ------------------------------------------------------------------------------------------------

# XDG base directories.
XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
XDG_CACHE_HOME = Path(os.environ.get("XDG_CACHE_HOME") or HOME / ".cache")
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local" / "share")
XDG_STATE_HOME = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local" / "state")

# fontconfig's per-user font directory: $CAMP_HOME/fonts is linked into it.
FONTS_LINK = XDG_DATA_HOME / "fonts" / "bash-camp"

# tmux.conf points TPM at this directory, so it has to stay outside $CAMP_HOME.
TMUX_PLUGINS_HOME = HOME / ".tmux" / "plugins"

# The line install appends to ~/.bashrc carries this tag; uninstall finds it by the tag rather than
# by the path, which changes with $CAMP_HOME.
RC_FILE = HOME / ".bashrc"
RC_MARKER = "# bash-camp:rc-addon"
