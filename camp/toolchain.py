"""What gets installed, what of it goes on PATH, and what the tools leave behind at run time.

Each list keeps the comment that says why an entry is in it - or deliberately is not.
"""

from __future__ import annotations

from .paths import HOME, XDG_CACHE_HOME, XDG_CONFIG_HOME, XDG_DATA_HOME, XDG_STATE_HOME


# Packages installed into the dev-tools pixi environment. Every install builds the environment
# afresh, from this list and the FALLBACK_TOOLS the host lacks, so dropping an entry here drops the
# package everywhere on the next install or deploy.
PIXI_PACKAGES = (
    # Shell and prompt.
    "starship",
    "zoxide",
    # History. atuin replaces bash's Ctrl-R with a searchable SQLite database.
    "atuin",
    # File operations.
    "fd-find",
    "ripgrep",
    "bat",
    "lsdeluxe",
    # Editors.
    "nvim",
    "micro",
    # Monitoring.
    "htop",
    "btop",
    # Development.
    "tree-sitter-cli",
    "ruff",
    "uv",
    # Syntax-highlighted diffs, of two files (`delta a b`) and as git's pager.
    "git-delta",
    # Utilities.
    "fzf",
    "mc",
    # Linters `check` runs that PyPI does not have, so uvx cannot bring them.
    "yamlfmt",
    "lychee",
    "stylua",
    # Clipboard bridge for tmux-yank. Without xclip (or xsel) on the box, tmux-yank disables
    # itself and rebinds `y` to an error message, so nothing ever reaches the desktop clipboard.
    # Only useful where there is an X display; remote servers rely on OSC 52 instead.
    "xclip",
    # Data-only: terminfo database and the bash-completion script. Neither contributes an
    # executable to PATH.
    "ncurses",
    "bash-completion",
    # Build-time only, for setup_bash_plugins: ble.sh's Makefile needs GNU awk, and Ubuntu ships
    # mawk. It is not shimmed, so it stays invisible to the interactive shell and cannot shadow the
    # system awk.
    "gawk",
)

# Tools the host normally provides, installed from pixi and shimmed only where it does not:
# package name -> executable. Where the host has one, the host's is used and pixi's is not even
# installed - an install that finds the tool on the system skips it.
FALLBACK_TOOLS = {
    # A tmux client can only attach to a server started by a compatible binary, so a tmux of our
    # own next to the system's would strand whatever server the system one already runs (symptom:
    # "open terminal failed: not a terminal"), and do it again on every version bump. On shared
    # servers that trap is worse than an older tmux. Without a system tmux there is no server to
    # strand. Note config/tmux/tmux.conf wants tmux >= 3.2 for terminal-features and #{E:...}; on
    # older distro versions those degrade quietly.
    "tmux": "tmux",
    # ble.sh's build runs it (setup_bash_plugins). Like every other build tool, it comes from the
    # host wherever there is one.
    "make": "make",
    # deploy ships the source tree with it. On a host without one, the first deploy brings a
    # private rsync of its own; this keeps one in place for the deploys after it.
    "rsync": "rsync",
    # Install clones ble.sh and TPM with it, Neovim's lazy.nvim its plugins.
    "git": "git",
}

# Where pixi's installer comes from, here and on the remote hosts deploy brings rsync to.
PIXI_INSTALL_URL = "https://pixi.prefix.dev/install.sh"

# $PIXI_HOME/config.toml of bash-camp's private pixi, written before it fetches anything. On some
# networks the sharded package index times out - its downloads from conda.anaconda.org and
# prefix.dev alike, however few at a time - while the full index goes through; it costs about
# 90 MB per fresh environment. bootstrap.py repeats it: it runs before this package can be imported.
PIXI_CONFIG_TOML = """\
[repodata-config]
disable-sharded = true
"""

# Nerd Fonts, for the icons starship, lsd and tmux draw; installed on desktops only. conda-forge has
# none, so they come from a release, pinned and checked: archive -> (SHA-256, the files kept).
NERD_FONTS_RELEASE = "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.5.1"
NERD_FONTS = {
    # Icons for any font: terminals that draw through fontconfig take the glyphs their own font
    # lacks from it.
    "NerdFontsSymbolsOnly.tar.xz": (
        "01172f37db8543edb102e5cb5c64101c9f4686630804d49b419aa07b23a69996",
        ("SymbolsNerdFontMono-Regular.ttf", "LICENSE"),
    ),
    # The font config/alacritty names.
    "JetBrainsMono.tar.xz": (
        "04d5e8f903693f9dd13e16f867e994834e681eb3c72c0d337a770dcda09010cf",
        (
            "JetBrainsMonoNerdFontMono-Regular.ttf",
            "JetBrainsMonoNerdFontMono-Bold.ttf",
            "JetBrainsMonoNerdFontMono-Italic.ttf",
            "JetBrainsMonoNerdFontMono-BoldItalic.ttf",
            "OFL.txt",
        ),
    ),
}

# Executables published as symlinks in dev-tools/shims and put on PATH.
#
# The pixi env's own bin/ holds ~400 entries, including a full coreutils, perl, git, make and an
# incidental python. Prepending that directory shadows the interpreter and system utilities that
# the host or the container base image provides, which is exactly how `python3` ends up resolving
# to a pixi build instead of the prepared project environment. Only the names below are exposed.
#
# Deliberately NOT shimmed: python, python3, perl, awk, and anything from coreutils. Those must
# keep coming from the underlying system. make, tmux, rsync and git are shimmed only where the
# system lacks them; see FALLBACK_TOOLS. bash-camp's own Python, where the system's is too old,
# is a pixi global environment of its private pixi; see bootstrap.py.
SHIMMED_EXECUTABLES = (
    "starship",
    "zoxide",
    "atuin",
    "fd",
    "rg",
    "bat",
    "lsd",
    "nvim",
    "micro",
    "htop",
    "btop",
    "tree-sitter",
    "ruff",
    "uv",
    "uvx",
    "delta",
    "fzf",
    "mc",
    "mcedit",
    "mcdiff",
    "mcview",
    "yamlfmt",
    "lychee",
    "stylua",
    # tmux-yank shells out to this by name, so it has to be on PATH.
    "xclip",
)

# Directories the tools create on their own at run time, long after install has returned. Install
# records the ones that do not exist yet, so that uninstall can remove exactly those and leave
# alone whatever was there before.
TOOL_STATE_PATHS = (
    # ble.sh: caches, shared-history state and its own data.
    XDG_CACHE_HOME / "blesh",
    XDG_STATE_HOME / "blesh",
    XDG_DATA_HOME / "blesh",
    # starship's session logs and caches.
    XDG_CACHE_HOME / "starship",
    # atuin's history database and key; zoxide's directory database.
    XDG_DATA_HOME / "atuin",
    XDG_DATA_HOME / "zoxide",
    # Settings these programs write by themselves on first run or on exit.
    XDG_CONFIG_HOME / "htop",
    XDG_CONFIG_HOME / "btop",
    XDG_CONFIG_HOME / "mc",
    XDG_CONFIG_HOME / "micro",
    XDG_DATA_HOME / "mc",
    XDG_CACHE_HOME / "mc",
    # nvim's shada/swap/undo state and plugin data.
    XDG_DATA_HOME / "nvim",
    XDG_STATE_HOME / "nvim",
    XDG_CACHE_HOME / "nvim",
    # uv's cache and the interpreters and tools it manages.
    XDG_CACHE_HOME / "uv",
    XDG_DATA_HOME / "uv",
    XDG_CACHE_HOME / "bat",
    XDG_CACHE_HOME / "tree-sitter",
    # fontconfig's cache, which registering the fonts creates where no desktop session has yet.
    XDG_CACHE_HOME / "fontconfig",
    # The stable forwarded-agent link the RC addon maintains.
    HOME / ".ssh" / "ssh_auth_sock",
)
