#!/usr/bin/env bash
# props.sh: the demo's props - a small project with an uncommitted change, and a shell history for
# atuin, ble.sh and zoxide to draw on. Run by docs/demo/Dockerfile, as the demo user.
set -euo pipefail

# The shims, for atuin and zoxide.
# shellcheck source=/dev/null
. ~/.camp/rc-addon.sh

git config --global user.name Camper
git config --global user.email camper@example.com
git config --global init.defaultBranch main

project=~/projects/pixel-sorter
mkdir -p "$project/tests" ~/projects/dotfiles ~/projects/notes
cd "$project"

cat >sorter.py <<'EOF'
"""Sort the pixels of an image by brightness, row by row."""

from PIL import Image


def brightness(pixel: tuple[int, int, int]) -> float:
    red, green, blue = pixel
    return 0.299 * red + 0.587 * green + 0.114 * blue


def sort_rows(image: Image.Image) -> Image.Image:
    # TODO: sort by hue as well
    width, height = image.size
    pixels = list(image.getdata())
    rows = [pixels[y * width : (y + 1) * width] for y in range(height)]
    rows = [sorted(row, key=brightness) for row in rows]
    image.putdata([pixel for row in rows for pixel in row])
    return image
EOF

cat >tests/test_sorter.py <<'EOF'
from sorter import brightness


def test_white_is_brightest() -> None:
    # TODO: cover sort_rows
    assert brightness((255, 255, 255)) > brightness((0, 0, 0))
EOF

cat >pyproject.toml <<'EOF'
[project]
name = "pixel-sorter"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["pillow"]
EOF

printf '# pixel-sorter\n\nSorts the pixels of an image by brightness.\n' >README.md
printf '.venv/\n__pycache__/\n' >.gitignore

git init -q
git add -A
git commit -qm "Sort rows by brightness"

# The uncommitted change `git diff` shows.
sed -i -e 's/(image: Image.Image) ->/(image: Image.Image, *, reverse: bool = False) ->/' \
  -e 's/key=brightness)/key=brightness, reverse=reverse)/' sorter.py

cat >~/.bash_history <<'EOF'
uv add pillow
nvim sorter.py
uv run pytest -q
git commit -am "Sort rows by brightness"
docker compose up -d
docker ps --format 'table {{.Names}}\t{{.Status}}'
ssh gpu-1
camp pitch gpu-1 gpu-2
fd -e py
rg TODO
git status
git diff
git log --oneline --graph
EOF
atuin import bash >/dev/null

for _ in 1 2 3; do
  zoxide add "$project"
done
zoxide add ~/projects/dotfiles ~/projects/notes
