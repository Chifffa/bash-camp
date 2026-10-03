# demo.tape: the scenes of docs/demo.gif, played by VHS (https://github.com/charmbracelet/vhs) in a
# container that has bash-camp pitched. Record with docs/demo/record.sh, which builds the container
# and re-encodes the GIF. The final Sleep is repeated there as -final_delay.

Require docker

Set Shell bash
Set FontFamily "JetBrainsMono Nerd Font Mono"
Set FontSize 12
Set Width 864
Set Height 512
Set Padding 12
Set Theme "Catppuccin Frappe"
Set WindowBar Colorful
Set BorderRadius 8
Set Margin 16
Set MarginFill "#232634"
Set TypingSpeed 70ms
Set Framerate 24
Set CursorBlink false
Set WaitTimeout 60s

Hide
Type "docker run -it --rm --hostname camp bash-camp-demo"
Enter
Wait /❯/
Ctrl+L
Sleep 500ms
Show

Sleep 1.5s

# zoxide: jump by a fragment of the name.
Type "z pix"
Sleep 600ms
Enter
Wait /❯/
Sleep 1s

# lsd and bat, as ls and cat.
Type "ls"
Enter
Wait /❯/
Sleep 1.5s
Type "cat sorter.py"
Enter
Wait /❯/
Sleep 3s
Ctrl+L

# ble.sh: highlighting, and suggestions from history as you type; Right takes one. delta shows
# the diff.
Type "git d"
Sleep 1.2s
Right
Sleep 500ms
Enter
Wait /❯/
Sleep 3.5s
Ctrl+L

# atuin: Ctrl-R searches the whole history; Enter puts the match on the command line.
Ctrl+R
Sleep 1.5s
Type "rg T"
Sleep 1.2s
Enter
Sleep 600ms
Enter
Wait /❯/
Sleep 2.5s
Ctrl+L

# tent: htop and a shell in one tmux session; a GPU host gets nvidia-smi too.
Type "tent"
Enter
Wait+Screen /Load average/
Sleep 3s
Type "tent strike"
Enter
Wait /❯/
Sleep 1s
Ctrl+L

# strike: the home directory as it was, down to the stock prompt.
Type "camp strike && exec bash"
Enter
Wait /\$$/
Sleep 4s
