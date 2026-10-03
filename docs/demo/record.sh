#!/usr/bin/env bash
# record.sh: record docs/demo.gif - build the demo container, play demo.tape in it with VHS, and
# re-encode the GIF.
#
# Usage: docs/demo/record.sh
# Needs docker, vhs and ttyd (`pixi global install vhs ttyd`), ffmpeg, Chrome, and the
# JetBrainsMono Nerd Font.
set -euo pipefail

cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")/../.."

raw=$(mktemp --suffix=.gif)
trap 'rm -f -- "$raw"' EXIT

docker build -t bash-camp-demo -f docs/demo/Dockerfile .
vhs --output "$raw" docs/demo/demo.tape

# VHS stores each frame as the pixels that changed, the rest transparent; a viewer that scales
# those layers before stacking them leaves dark ghosts of cleared text. Whole opaque frames cannot
# be stacked wrong, and merging identical ones keeps the size down. The last frame keeps the
# tape's final Sleep, which merging would drop.
ffmpeg -loglevel error -y -i "$raw" \
  -filter_complex "mpdecimate=hi=1:lo=1:frac=0,split[a][b];
    [a]palettegen=stats_mode=full:reserve_transparent=0[p];
    [b][p]paletteuse=dither=none:diff_mode=none" \
  -fps_mode vfr -gifflags -offsetting-transdiff -final_delay 400 docs/demo.gif
