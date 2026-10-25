#!/bin/bash
# usage: render.sh name.svg  -> name.png (2x)
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for f in "$@"; do
  w=$(grep -o 'width="[0-9]*"' "$f" | head -1 | grep -o '[0-9]*')
  h=$(grep -o 'height="[0-9]*"' "$f" | head -1 | grep -o '[0-9]*')
  "$CH" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=$w,$h --screenshot="$PWD/${f%.svg}.png" "file://$PWD/$f" >/dev/null 2>&1
done
