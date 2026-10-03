"""bash-camp: a portable, userspace bash environment.

`camp pitch` copies the source tree into $CAMP_HOME (~/.camp by default) and builds the whole
environment inside it: a private pixi with a curated toolchain, ble.sh, and the RC addon that
~/.bashrc sources. Nothing is read from the checkout afterwards, so the checkout itself can live
anywhere, be moved or be deleted without affecting the installed environment. Installing again
replaces the installation: the earlier one is uninstalled first.

Every change install makes OUTSIDE $CAMP_HOME - config and font links, secrets, tmux plugins, the
line in ~/.bashrc, the state directories the tools are going to create - is recorded in
$CAMP_HOME/state/journal.json together with whatever it displaced. `camp strike` replays that
journal backwards and then deletes $CAMP_HOME, leaving the home directory as it was before the
first install.

Layout
------

The package splits along that same line: what is built inside $CAMP_HOME needs no record, what is
changed outside it goes through the journal.

    build.py             the steps that build inside $CAMP_HOME
    cli.py               the `camp` command line
    deploy.py            pitch, strike and scout on remote hosts - the same install, over ssh
    home.py              the steps that change the home directory, each through the journal
    install.py           the order of the steps, install and uninstall
    journal.py           the record of every change outside $CAMP_HOME, and how each is undone
    model.py             the types the modules hand to each other; imports nothing from here
    ops.py               the file and process primitives everything else is written in
    paths.py             where everything lives
    rc-addon.sh          what ~/.bashrc sources, with the reason behind every part of it
    secrets_manifest.py  secrets/manifest.json, validated before the first change
    toolchain.py         what gets installed, what goes on PATH, what the tools leave behind

The package runs under a bare python3 >= 3.12, with the standard library only; bootstrap.py brings
one where the system's is older.

Reading order: install.py for what happens and in which order, then build.py and home.py for each
step, then journal.py for how uninstall takes it back.
"""
