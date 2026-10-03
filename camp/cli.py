"""The `camp` command line.

Usage:
    camp pitch                    # install here; an earlier installation is replaced
    camp strike                   # uninstall here, restoring the pre-install state
    camp pitch HOST...            # check, sync and install on remote hosts over ssh
    camp strike HOST...           # uninstall on remote hosts
    camp scout HOST...            # only check that remote hosts can take it

Inside a bash-camp checkout, `camp` runs that checkout - that is how changes get installed or
shipped - and says so; elsewhere, the installed copy in $CAMP_HOME/src. `camp strike` always runs
the installed copy, the code that made the installation. `python3 bootstrap.py` runs its own tree.

Private files (credentials, keys, env files) go into secrets/ next to bootstrap.py and are
described by secrets/manifest.json; see secrets.example/.
"""

from __future__ import annotations

import argparse
import inspect
import sys

from .deploy import deploy, undeploy
from .install import install, uninstall
from .model import CampError


def main() -> None:
    """CLI entry point with subcommand handling: parse, run, exit with the handler's status."""
    parser = argparse.ArgumentParser(
        prog="camp",
        description="bash-camp: a portable, userspace bash environment.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pitch_parser = subparsers.add_parser(
        "pitch", help="Install here, or on the given hosts, replacing an earlier installation"
    )
    _add_host_arguments(pitch_parser, nargs="*")
    pitch_parser.set_defaults(handler=_pitch)

    strike_parser = subparsers.add_parser(
        "strike", help="Uninstall here, or on the given hosts, restoring the pre-install state"
    )
    _add_host_arguments(strike_parser, nargs="*")
    strike_parser.set_defaults(handler=_strike)

    scout_parser = subparsers.add_parser(
        "scout", help="Only check that remote hosts have everything an install needs"
    )
    _add_host_arguments(scout_parser, nargs="+")
    scout_parser.set_defaults(handler=_scout)

    args = parser.parse_args()
    if args.ssh_option and not args.hosts:
        parser.error("-o/--ssh-option needs hosts")

    # Hand each handler the arguments its signature names.
    handler_kwargs = {
        name: getattr(args, name) for name in inspect.signature(args.handler).parameters
    }
    try:
        status = args.handler(**handler_kwargs)
    except CampError as error:
        print(f"\nError: {error}", file=sys.stderr)
        sys.exit(1)
    sys.exit(status or 0)


def _pitch(hosts: list[str], ssh_option: list[str]) -> int:
    """Install here, or on remote hosts.

    :param hosts: the hosts; none to install here.
    :param ssh_option: extra `ssh -o` options.
    :return: the exit status.
    """
    if hosts:
        return deploy(hosts, check=False, ssh_option=ssh_option)
    return install()


def _strike(hosts: list[str], ssh_option: list[str]) -> int:
    """Uninstall here, or on remote hosts.

    :param hosts: the hosts; none to uninstall here.
    :param ssh_option: extra `ssh -o` options.
    :return: the exit status.
    """
    if hosts:
        return undeploy(hosts, ssh_option)
    uninstall()
    return 0


def _scout(hosts: list[str], ssh_option: list[str]) -> int:
    """Check remote hosts without changing them.

    :param hosts: the hosts.
    :param ssh_option: extra `ssh -o` options.
    :return: the exit status.
    """
    return deploy(hosts, check=True, ssh_option=ssh_option)


def _add_host_arguments(command_parser: argparse.ArgumentParser, *, nargs: str) -> None:
    """Add the hosts and the ssh options every subcommand takes.

    :param command_parser: the subcommand's parser.
    :param nargs: "*" where hosts are optional, "+" where they are required.
    """
    command_parser.add_argument("hosts", nargs=nargs, help="SSH hosts, as ssh understands them.")
    command_parser.add_argument(
        "-o",
        "--ssh-option",
        action="append",
        default=[],
        metavar="OPTION",
        help="Extra ssh option, as for `ssh -o` (repeatable).",
    )
