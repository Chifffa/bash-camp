#!/usr/bin/env python3
"""bash-camp's installer and `camp` command. The code is the `camp` package next to this file.

Run with a bare python3 - from a checkout, from $CAMP_HOME/src through bin/camp, and on remote hosts
by `camp pitch HOST` - so it must stay a plain script with no dependencies. See `camp --help`.

The package needs Python 3.12 or newer. Started on an older one, this script brings a private one
with bash-camp's private pixi and runs again on it, so this file has to stay readable to any
python3 >= 3.6: no newer syntax, and nothing imported from the package before the switch.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


MIN_PYTHON = (3, 12)

# The private pixi and the Python it brings, as camp/paths.py and camp/deploy.py lay them out; the
# package cannot be imported to ask.
CAMP_HOME = Path(os.environ.get("CAMP_HOME") or Path.home() / ".camp").expanduser()
PIXI_HOME = CAMP_HOME / "pixi"
PRIVATE_PYTHON = PIXI_HOME / "envs" / "python" / "bin" / "python3"
PIXI_INSTALL_URL = "https://pixi.prefix.dev/install.sh"
# PIXI_CONFIG_TOML of camp/toolchain.py, which says why.
PIXI_CONFIG_TOML = "[repodata-config]\ndisable-sharded = true\n"
# Set for the run on the private Python, so that one too old cannot loop.
REEXEC_MARKER = "CAMP_PRIVATE_PYTHON"


def bring_python():
    """Install the private Python, and the private pixi first where there is none yet.

    Only python3 is exposed, in $CAMP_HOME/pixi/bin, which the RC addon appends to PATH: a system
    python3, however old, stays the one shells find.
    """
    env = dict(
        os.environ,
        PIXI_HOME=str(PIXI_HOME),
        PIXI_CACHE_DIR=str(CAMP_HOME / "cache" / "pixi"),
        PIXI_NO_PATH_UPDATE="1",
    )
    pixi = PIXI_HOME / "bin" / "pixi"
    CAMP_HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not pixi.exists():
        if shutil.which("curl") is None:
            sys.exit("bash-camp needs curl, to bring a newer Python.")
        script = f"set -o pipefail; curl -fsSL {PIXI_INSTALL_URL} | bash"
        subprocess.check_call(["bash", "-c", script], env=env)
    (PIXI_HOME / "config.toml").write_text(PIXI_CONFIG_TOML)
    spec = "python>={}.{}".format(*MIN_PYTHON)
    command = [str(pixi), "global", "install", "--expose", "python3=python3", spec]
    subprocess.check_call(command, env=env)


# Older Pythons get this far, to bring a new one.
if sys.version_info < MIN_PYTHON:
    if os.environ.get(REEXEC_MARKER):
        sys.exit(f"bash-camp needs Python 3.12 or newer, and {PRIVATE_PYTHON} is not.")
    if not PRIVATE_PYTHON.exists():
        found = sys.version.split()[0]
        print(f"Python {found} is too old for bash-camp; bringing 3.12+ into {PIXI_HOME}.")
        sys.stdout.flush()
        try:
            bring_python()
        except (OSError, subprocess.CalledProcessError) as error:
            sys.exit(f"Could not bring a newer Python: {error}")
    os.environ[REEXEC_MARKER] = "1"
    os.execv(str(PRIVATE_PYTHON), [str(PRIVATE_PYTHON), *sys.argv])

if __name__ == "__main__":
    # The script's directory is normally on sys.path already, but not under `python3 -P` or with
    # PYTHONSAFEPATH set, and bin/camp must find this copy of the package, not any other.
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    from camp.cli import main

    main()
