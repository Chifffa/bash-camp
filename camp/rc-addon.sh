# shellcheck shell=bash
# shellcheck disable=SC2317 # `exit` runs when the file is executed rather than sourced.
#
# bash-camp RC addon, sourced by ~/.bashrc.
#
# Installed verbatim as $CAMP_HOME/rc-addon.sh; edit camp/rc-addon.sh in bash-camp instead. Every
# path is resolved here, from this file's own location, so one copy works wherever $CAMP_HOME is
# mounted - a container may mount it under another $HOME. Section order matters.

if [ -z "${BASH_VERSION-}" ]; then
  return 0 2>/dev/null || exit 0
fi

# Where this file really is, through any symlink, which has to be an installation: everything
# below is found from there. A sourced file returns rather than exits - exit would close the shell
# sourcing it.
__camp_root=$(readlink -f -- "${BASH_SOURCE[0]}" 2>/dev/null) && __camp_root=${__camp_root%/*}
if [[ -z $__camp_root || ! -d $__camp_root/src ]]; then
  echo "bash-camp: ${BASH_SOURCE[0]} is not in an installation (no src/ next to it);" \
    "nothing loaded. Source \$CAMP_HOME/rc-addon.sh, or run \`camp pitch\` again." >&2
  unset __camp_root
  return 1 2>/dev/null || exit 1
fi
__camp_env=$__camp_root/dev-tools/.pixi/envs/default

# --- Identity -------------------------------------------------------------------------------------
# `docker exec` and some SSH/PAM paths leave $USER empty.
export USER=${USER:-$(id -un)}
export LOGNAME=${LOGNAME:-$USER}

# --- SSH agent ------------------------------------------------------------------------------------
# Shells export the stable link ~/.ssh/ssh_auth_sock, so tmux panes outlive the login's socket. A
# dead link first heals to the keyring. Then a login re-aims it at its own socket, unless that
# already is the link's target - compared by inode, since a container spells the same file
# differently and a link aimed at itself fails with ELOOP. A forwarded agent, sshd's per-session
# socket (in ~/.ssh/agent since OpenSSH 10.1, in /tmp before), dies with its connection: it takes
# the link from another login's forwarded agent, the newest login winning, but never from a live
# agent of the machine's own, such as the keyring.
__camp_link=$HOME/.ssh/ssh_auth_sock
__camp_keyring=/run/user/$(id -u)/keyring/ssh
__camp_inode() { stat -Lc %d:%i -- "$1" 2>/dev/null; }
__camp_forwarded() { [[ $1 == /tmp/ssh-*/agent.* || $1 == */.ssh/agent/s.*.sshd.* ]]; }
if [[ -L $__camp_link && ! -e $__camp_link && -S $__camp_keyring ]]; then
  ln -sfn -- "$__camp_keyring" "$__camp_link"
fi
if [[ -z ${TMUX-} && -S ${SSH_AUTH_SOCK-} && $SSH_AUTH_SOCK != "$__camp_link" ]] &&
  [[ $(__camp_inode "$SSH_AUTH_SOCK") != "$(__camp_inode "$__camp_link")" ]] &&
  { ! __camp_forwarded "$SSH_AUTH_SOCK" || [[ ! -S $__camp_link ]] ||
    __camp_forwarded "$(readlink -- "$__camp_link")"; }; then
  mkdir -p -- "${__camp_link%/*}"
  ln -sfn -- "$SSH_AUTH_SOCK" "$__camp_link"
fi
# The session keeps its own live socket only while the link is beyond repair.
if [[ -S $__camp_link || ! -S ${SSH_AUTH_SOCK-} ]]; then
  export SSH_AUTH_SOCK=$__camp_link
fi
unset __camp_link __camp_keyring
unset -f __camp_inode __camp_forwarded

# --- PATH -----------------------------------------------------------------------------------------
# Prepend moves an existing entry to the front, so re-sourcing neither duplicates nor reorders.
__camp_path_prepend() {
  [[ -d $1 ]] || return 0
  local rest=":$PATH:"
  rest=${rest//":$1:"/:}
  rest=${rest#:}
  rest=${rest%:}
  export PATH=$1${rest:+:$rest}
}
# Append only adds a fallback: whatever already provides a command keeps precedence.
__camp_path_append() {
  [[ -d $1 && :$PATH: != *:"$1":* ]] || return 0
  export PATH=${PATH:+$PATH:}$1
}
# The curated shims only, never the pixi env's bin/: it would shadow the host's python, coreutils,
# git and more (SHIMMED_EXECUTABLES in camp/toolchain.py).
__camp_path_prepend "$__camp_root/dev-tools/shims"
__camp_path_prepend "$__camp_root/src/bin"
# Last, so a pixi of the system, the image or the user wins.
__camp_path_append "$__camp_root/pixi/bin"
unset -f __camp_path_prepend __camp_path_append

# --- Environment ----------------------------------------------------------------------------------
# A fallback only: forcing TERM replaced tmux's tmux-256color in every pane.
export TERM=${TERM:-xterm-256color}
export TERMINFO_DIRS=$__camp_env/share/terminfo:/usr/share/terminfo:/lib/terminfo

if command -v micro &>/dev/null; then
  export EDITOR=micro VISUAL=micro
else
  export EDITOR=nano VISUAL=nano
fi

export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONFAULTHANDLER=1
export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
export DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1

# A UTF-8 locale, but only one the system has: assigning a missing one - or inheriting it, say from
# ssh's SendEnv - makes bash warn and ble.sh complain at every shell start. A working one stays;
# else LANG, if only an override is broken; else en_US.UTF-8 where it is generated; else C.UTF-8,
# which modern glibc has built in.
# Probed through env: bash itself, given even a temporary LC_ALL=..., warns about a broken one.
__camp_utf8() { [[ -n $1 && $(env LC_ALL="$1" locale charmap 2>/dev/null) == UTF-8 ]]; }
__camp_locale=${LC_ALL:-${LC_CTYPE:-${LANG-}}}
if ! __camp_utf8 "$__camp_locale"; then
  for __camp_locale in "${LANG-}" en_US.UTF-8 C.UTF-8 ""; do
    __camp_utf8 "$__camp_locale" && break
  done
  if [[ -n $__camp_locale ]]; then
    export LANG=$__camp_locale
    # LC_CTYPE first: while LC_ALL is set, unsetting it applies nothing, so nothing can warn.
    unset LC_CTYPE 2>/dev/null
    unset LC_ALL 2>/dev/null
  fi
fi
# ble.sh also complains about an empty LANG where LC_ALL or LC_CTYPE alone work.
if [[ -z ${LANG-} && -n $__camp_locale ]]; then
  export LANG=$__camp_locale
fi
unset __camp_locale
unset -f __camp_utf8

# The "load": "env" secrets, listed by install. Read on fd 3: an env file that reads stdin must not
# swallow the rest of the list.
if [[ -f $__camp_root/state/env-files ]]; then
  while IFS= read -r __camp_file <&3; do
    if [[ -f $__camp_root/$__camp_file ]]; then
      set -a
      # shellcheck source=/dev/null
      . "$__camp_root/$__camp_file"
      set +a
    fi
  done 3<"$__camp_root/state/env-files"
  unset __camp_file
fi

# =================================================================================================
# Interactive shells only.
# =================================================================================================
if [[ $- != *i* ]]; then
  unset __camp_root __camp_env
  return 0 2>/dev/null || exit 0
fi

# Servers may set TMOUT, which logs idle shells and tmux panes out; a readonly one stays.
unset TMOUT 2>/dev/null

# HISTFILE is left alone: a container may keep history on a volume.
export HISTSIZE=100000 HISTFILESIZE=200000 HISTCONTROL=ignoreboth:erasedups HISTTIMEFORMAT='%F %T '
shopt -s histappend cmdhist checkwinsize globstar

# --- Aliases and tools ----------------------------------------------------------------------------
if command -v micro &>/dev/null; then
  alias nano=micro
fi
if command -v lsd &>/dev/null; then
  alias ls=lsd l='ls -l' la='ls -a' lla='ls -la' lt='ls --tree'
fi
if command -v bat &>/dev/null; then
  alias cat='bat --paging=never --decorations=never'
fi
# delta pages git's diffs, unless git has a pager of its own already.
if command -v delta &>/dev/null && [[ -z ${GIT_PAGER-} ]] &&
  ! git config --get core.pager &>/dev/null; then
  export GIT_PAGER=delta
fi
if command -v zoxide &>/dev/null; then
  eval "$(zoxide init bash)"
fi
if command -v pixi &>/dev/null; then
  eval "$(pixi completion --shell bash)"
fi

# --- Completion -----------------------------------------------------------------------------------
if [[ -f $__camp_env/share/bash-completion/bash_completion ]]; then
  # shellcheck source=/dev/null
  . "$__camp_env/share/bash-completion/bash_completion"
fi

# `python -m pkg.<TAB>` imports every package on sys.path (walk_packages): minutes of frozen shell
# on a network mount, and ble.sh's auto-complete fires it while typing. Load the completer now, so
# its lazy load cannot undo this, and list top-level modules only, time-boxed.
# shellcheck source=/dev/null
if [[ -f $__camp_env/share/bash-completion/completions/python ]] &&
  . "$__camp_env/share/bash-completion/completions/python" 2>/dev/null; then
  _python_modules() {
    local candidates code='import pkgutil; print("\n".join(m.name for m in pkgutil.iter_modules()))'
    candidates=$(command timeout 2 "${1:-python}" -c "$code" 2>/dev/null)
    # shellcheck disable=SC2154 # $cur is a local of the bash-completion caller.
    mapfile -t -O "${#COMPREPLY[@]}" COMPREPLY < <(compgen -W "$candidates" -- "$cur")
  }
fi
unset __camp_env

# --- Line editor and prompt -----------------------------------------------------------------------
# ble.sh is loaded first, so atuin hooks into it, and attached last: attaching snapshots PS1 and
# drops PROMPT_COMMAND, so a prompt set up after it is silently lost.
# ble.sh prints nothing: its load-time notices, on stdout and stderr, go to /dev/null, and its
# markers are off. Safe: ble-attach takes the streams commands write to from the shell itself, and
# ble.sh draws on /dev/tty. connect_tty, at its default, has to be set before loading for that:
# otherwise ble.sh refuses to load with stdout not a terminal.
if [[ -f $__camp_root/blesh/ble.sh ]]; then
  # shellcheck disable=SC2034 # read by ble.sh
  bleopt_connect_tty=1
  # shellcheck source=/dev/null
  . "$__camp_root/blesh/ble.sh" --attach=none &>/dev/null
fi
if [[ -n ${BLE_VERSION-} ]]; then
  bleopt exec_errexit_mark= exec_elapsed_mark= exec_exit_mark=
  bleopt complete_timeout_auto=500 # ms; a slow completer must not stall typing
fi
if command -v atuin &>/dev/null; then
  eval "$(atuin init bash)"
fi
if command -v starship &>/dev/null; then
  eval "$(starship init bash)"
fi
unset __camp_root
if [[ -n ${BLE_VERSION-} ]]; then
  ble-attach
fi
