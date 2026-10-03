"""`camp pitch`, `strike` and `scout` with hosts: the same install, on remote hosts over ssh.

A host is probed first and refused with the full list of its problems, so that a deploy never stops
halfway through for a missing dependency. A host without rsync, or without Python 3.12+, gets a
private one inside ~/.camp; git, tmux and make it gets from pixi like any host that lacks them.
Then the source tree is rsynced into ~/.camp/src there and `camp pitch` runs from that copy,
exactly as it would locally.
"""

from __future__ import annotations

import dataclasses
import shlex
import shutil
import subprocess

from .model import CampError, SecretEntry
from .paths import SOURCE_HOME, SOURCE_IGNORE_PATTERNS, SOURCE_ITEMS
from .secrets_manifest import load_secrets_manifest, missing_secret_sources
from .toolchain import PIXI_CONFIG_TOML, PIXI_INSTALL_URL


# Paths are written for the REMOTE shell: rsync resolves a relative destination against the remote
# home, and "$HOME" is expanded there.
REMOTE_CAMP_HOME = '"$HOME/.camp"'
REMOTE_SRC = ".camp/src/"
REMOTE_BOOTSTRAP = '"$HOME/.camp/src/bootstrap.py"'

# Where the probe looks for an rsync when the system has none: the shim an earlier install
# published (rsync is one of the FALLBACK_TOOLS), then the one an earlier deploy brought.
REMOTE_PRIVATE_RSYNCS = (
    "$HOME/.camp/dev-tools/shims/rsync",
    "$HOME/.camp/pixi/envs/rsync/bin/rsync",
)

# The Python install runs on where the host's python3 is missing or older than REMOTE_MIN_PYTHON;
# bootstrap.py brings the same one where it is started on an older Python.
REMOTE_MIN_PYTHON = (3, 12)
REMOTE_PRIVATE_PYTHON = "$HOME/.camp/pixi/envs/python/bin/python3"

# Sets $py to the python3 to run bootstrap.py with: the host's where it is new enough.
REMOTE_PYTHON = (
    f"py=python3; python3 -c 'import sys; sys.exit(sys.version_info < {REMOTE_MIN_PYTHON})'"
    f' 2>/dev/null || py="{REMOTE_PRIVATE_PYTHON}"'
)

# Brings the private rsync and Python. They come from bash-camp's private pixi - the same pixi, in
# the same place, that install would download first thing, and then finds in place - as pixi global
# environments. Everything stays inside ~/.camp: private home, private cache, no PATH line in any
# RC file; a reinstall keeps them.
REMOTE_PIXI = "\n".join(
    [
        "set -e",
        'export PIXI_HOME="$HOME/.camp/pixi" PIXI_CACHE_DIR="$HOME/.camp/cache/pixi"',
        "export PIXI_NO_PATH_UPDATE=1",
        'if [ ! -x "$PIXI_HOME/bin/pixi" ]; then',
        f"  curl -fsSL {PIXI_INSTALL_URL} | bash",
        "fi",
        f'printf %s {shlex.quote(PIXI_CONFIG_TOML)} > "$PIXI_HOME/config.toml"',
    ]
)
REMOTE_RSYNC_INSTALL = f'{REMOTE_PIXI}\n"$PIXI_HOME/bin/pixi" global install rsync'
# Only python3 is exposed, and only behind the host's own on PATH: a host whose python3 is old keeps
# it, and gets no pip or anything else of ours.
REMOTE_PYTHON_INSTALL = (
    f'{REMOTE_PIXI}\n"$PIXI_HOME/bin/pixi" global install --expose python3=python3'
    f' "python>={".".join(map(str, REMOTE_MIN_PYTHON))}"'
)

REMOTE_REQUIRED_TOOLS = ("bash", "curl", "tar")
REMOTE_ARCHITECTURES = ("x86_64", "aarch64")

# Install downloads pixi and ble.sh from GitHub, by way of pixi's installer, and packages from
# conda-forge.
REMOTE_REQUIRED_URLS = (
    "https://pixi.prefix.dev",
    "https://github.com",
    "https://conda.anaconda.org",
)
SSH_BASE_OPTIONS = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=10")


def deploy(hosts: list[str], check: bool, ssh_option: list[str]) -> int:
    """`camp pitch HOST...`: check, sync and install bash-camp on remote hosts over ssh.

    :param hosts: the hosts, as ssh understands them.
    :param check: only check that the hosts have everything install needs - `camp scout`.
    :param ssh_option: extra `ssh -o` options.
    :return: the exit status - 1 if any host failed.
    :raises CampError: without a local rsync, or if the secrets manifest is broken.
    """
    if not check and shutil.which("rsync") is None:
        raise CampError("rsync is required locally to reach remote hosts. Install it first.")

    entries = load_secrets_manifest(SOURCE_HOME / "secrets")
    problems = missing_secret_sources(SOURCE_HOME / "secrets", entries)
    if problems:
        raise CampError("\n".join(problems))

    shipped = [entry for entry in entries if not entry.local_only]
    print(
        f"Source: {SOURCE_HOME}; secrets: {len(shipped)} shipped,"
        f" {len(entries) - len(shipped)} local-only kept back."
    )

    failed: list[str] = []
    for host in hosts:
        print(f"\n==> {host}")
        try:
            _deploy_host(host, ssh_option, entries, check=check)
        except CampError as error:
            print(f"  FAILED: {error}")
            failed.append(host)

    print()
    if failed:
        print(f"Failed: {', '.join(failed)}.")
        return 1

    print("All hosts checked." if check else "All hosts deployed.")
    return 0


def undeploy(hosts: list[str], ssh_option: list[str]) -> int:
    """`camp strike HOST...`: uninstall bash-camp on remote hosts, restoring what was there before.

    :param hosts: the hosts, as ssh understands them.
    :param ssh_option: extra `ssh -o` options.
    :return: the exit status - 1 if any host failed.
    """
    remote_script = "\n".join(
        [
            f"if [ -f {REMOTE_BOOTSTRAP} ]; then",
            f"  {REMOTE_PYTHON}",
            f'  CAMP_HOME={REMOTE_CAMP_HOME} exec "$py" {REMOTE_BOOTSTRAP} strike',
            "fi",
            'echo "bash-camp is not installed in ~/.camp."',
            # What a deploy that failed before shipping anything leaves: a private rsync or Python.
            f"if [ -d {REMOTE_CAMP_HOME} ]; then",
            '  echo "~/.camp is there, without an installation in it; left alone."',
            "fi",
        ]
    )

    failed: list[str] = []
    for host in hosts:
        print(f"\n==> {host}")
        try:
            _run_remote(host, ssh_option, remote_script, what="remote uninstall")
        except CampError as error:
            print(f"  FAILED: {error}")
            failed.append(host)

    if failed:
        print(f"\nFailed: {', '.join(failed)}.")
        return 1

    return 0


@dataclasses.dataclass(frozen=True)
class HostProbe:
    """What deploy needs to know about a host, collected over ssh without changing anything.

    Attributes:
        missing: required tools the host lacks.
        rsync: the rsync to run there - "rsync" for the system's, the path of a private one, or
            None when it has neither.
        python: python3's version, or None without one.
        private_python: whether an earlier deploy brought a Python of its own.
        arch: the machine architecture, `uname -m`.
        unreachable: required URLs the host cannot reach.
    """

    missing: list[str]
    rsync: str | None
    python: tuple[int, ...] | None
    private_python: bool
    arch: str
    unreachable: list[str]

    @property
    def needs_python(self) -> bool:
        """Whether install has to bring a Python of its own.

        :return: True when the host's python3 is missing or too old, and none was brought yet.
        """
        too_old = self.python is None or self.python < REMOTE_MIN_PYTHON
        return too_old and not self.private_python

    def problems(self) -> list[str]:
        """Everything that stops install from finishing on this host.

        A missing rsync or Python 3.12+ is not one of them: deploy brings its own.

        :return: one line per problem; empty when the host can take an install.
        """
        problems: list[str] = []
        if self.missing:
            problems.append(f"missing {', '.join(self.missing)}")

        if self.arch not in REMOTE_ARCHITECTURES:
            problems.append(f"unsupported architecture {self.arch or '?'}")

        if self.unreachable:
            problems.append(f"no network access to {', '.join(self.unreachable)}")

        return problems


def _deploy_host(
    host: str,
    ssh_options: list[str],
    entries: list[SecretEntry],
    *,
    check: bool,
) -> None:
    """Probe one host, then sync the source tree to it and run install there.

    :param host: the host, as ssh understands it.
    :param ssh_options: extra `ssh -o` options.
    :param entries: the secrets manifest, for the local-only entries to keep back.
    :param check: stop after the probe.
    :raises CampError: if the host is unreachable, lacks a dependency, or installing Python or
        rsync, the sync or the remote install fails.
    """
    probe = _probe_host(host, ssh_options)
    problems = probe.problems()
    if problems:
        raise CampError(f"{'; '.join(problems)}.")

    print("  Dependencies: OK.")
    if check:
        if probe.needs_python:
            found = ".".join(map(str, probe.python)) if probe.python else "none"
            print(f"  Note: python3 is {found}; pitching brings a private 3.12+ into ~/.camp.")
        if probe.rsync is None:
            print("  Note: no rsync; pitching brings a private one into ~/.camp.")
        return

    _run_remote(
        host,
        ssh_options,
        f"mkdir -p {REMOTE_CAMP_HOME} && chmod 700 {REMOTE_CAMP_HOME}",
        what="preparing ~/.camp",
    )

    if probe.needs_python:
        print("  No python3 >= 3.12; installing a private one into ~/.camp...")
        _run_remote(host, ssh_options, REMOTE_PYTHON_INSTALL, what="installing Python")

    rsync = probe.rsync
    if rsync is None:
        print("  No rsync; installing a private one into ~/.camp...")
        _run_remote(host, ssh_options, REMOTE_RSYNC_INSTALL, what="installing rsync")
        # Found the way every later deploy finds it, so that this one proves they will.
        rsync = _probe_host(host, ssh_options).rsync
        if rsync is None:
            raise CampError("rsync was installed into ~/.camp, but is not found there.")
        print(f"  Using {rsync}.")

    print("  Syncing sources...")
    rsync_command = [
        "rsync",
        "-az",
        "--delete",
        "--delete-excluded",
        *([] if rsync == "rsync" else [f"--rsync-path={rsync}"]),
        "-e",
        shlex.join(_ssh_command(ssh_options)),
        *_rsync_filters(entries),
        f"{SOURCE_HOME}/",
        f"{host}:{REMOTE_SRC}",
    ]
    if subprocess.run(rsync_command, check=False).returncode != 0:
        raise CampError("rsync failed.")

    print("  Installing...")
    _run_remote(
        host,
        ssh_options,
        f'{REMOTE_PYTHON}; CAMP_HOME={REMOTE_CAMP_HOME} exec "$py" {REMOTE_BOOTSTRAP} pitch',
        what="remote install",
    )


def _probe_host(host: str, ssh_options: list[str]) -> HostProbe:
    """Collect what deploy needs to know about a host, without changing it.

    :param host: the host, as ssh understands it.
    :param ssh_options: extra `ssh -o` options.
    :return: what was found.
    :raises CampError: if the host is unreachable over ssh.
    """
    private_rsyncs = " ".join(f'"{path}"' for path in REMOTE_PRIVATE_RSYNCS)
    script = "\n".join(
        [
            'missing=""',
            f"for tool in {' '.join(REMOTE_REQUIRED_TOOLS)}; do",
            '  command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"',
            "done",
            'echo "missing=$missing"',
            "if command -v rsync >/dev/null 2>&1; then",
            '  echo "rsync=rsync"',
            "else",
            f"  for rsync in {private_rsyncs}; do",
            '    if [ -x "$rsync" ]; then echo "rsync=$rsync"; break; fi',
            "  done",
            "fi",
            "if command -v python3 >/dev/null 2>&1; then",
            "  version=$(python3 -c 'import sys; print(\"%d.%d\" % sys.version_info[:2])')",
            '  echo "python=$version"',
            "fi",
            f'if [ -x "{REMOTE_PRIVATE_PYTHON}" ]; then echo "private_python=1"; fi',
            'echo "arch=$(uname -m)"',
            "if command -v curl >/dev/null 2>&1; then",
            f"  for url in {' '.join(REMOTE_REQUIRED_URLS)}; do",
            '    curl -sSIL -o /dev/null -m 10 "$url" >/dev/null 2>&1 || echo "unreachable=$url"',
            "  done",
            "fi",
            "exit 0",
        ]
    )
    result = subprocess.run(
        [*_ssh_command(ssh_options), host, "sh -s"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise CampError(f"unreachable over ssh: {result.stderr.strip() or 'unknown error'}")

    values: dict[str, str] = {}
    unreachable: list[str] = []
    for line in result.stdout.splitlines():
        key, _, value = line.partition("=")
        if key == "unreachable":
            unreachable.append(value)
        elif key:
            values[key] = value.strip()

    python = values.get("python")
    return HostProbe(
        missing=values.get("missing", "").split(),
        rsync=values.get("rsync") or None,
        python=tuple(int(part) for part in python.split(".")) if python else None,
        private_python=values.get("private_python") == "1",
        arch=values.get("arch", ""),
        unreachable=unreachable,
    )


def _rsync_filters(entries: list[SecretEntry]) -> list[str]:
    """The rsync filter rules that ship SOURCE_ITEMS minus the local-only secrets.

    :param entries: the secrets manifest.
    :return: rsync arguments, in the order rsync applies them.
    """
    filters = [f"--exclude=/secrets/{entry.source}" for entry in entries if entry.local_only]
    filters += [f"--exclude={pattern}" for pattern in SOURCE_IGNORE_PATTERNS]
    for name in SOURCE_ITEMS:
        pattern = f"/{name}/***" if (SOURCE_HOME / name).is_dir() else f"/{name}"
        filters.append(f"--include={pattern}")
    filters.append("--exclude=*")
    return filters


def _run_remote(host: str, ssh_options: list[str], script: str, *, what: str) -> None:
    """Run a shell script on a host, streaming its output.

    :param host: the host, as ssh understands it.
    :param ssh_options: extra `ssh -o` options.
    :param script: the script, run by the remote login shell.
    :param what: what the script does, for the error message.
    :raises CampError: if the script fails.
    """
    result = subprocess.run([*_ssh_command(ssh_options), host, script], check=False)
    if result.returncode != 0:
        raise CampError(f"{what} exited with status {result.returncode}.")


def _ssh_command(ssh_options: list[str]) -> list[str]:
    """The ssh command line up to the host: non-interactive, with the user's extra options.

    :param ssh_options: extra `ssh -o` options.
    :return: the command line, without the host.
    """
    return ["ssh", *SSH_BASE_OPTIONS, *[arg for option in ssh_options for arg in ("-o", option)]]
