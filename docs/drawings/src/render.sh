#!/bin/bash
# usage: render.sh name.svg  -> name.png (2x)
# macOS では Google Chrome、それ以外では $CHROME か PATH 上の chromium を使う
if [ -n "$CHROME" ]; then
  CH="$CHROME"
elif [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
  CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif [ -x /opt/pw-browsers/chromium ]; then
  CH=/opt/pw-browsers/chromium
else
  CH=$(command -v chromium || command -v chromium-browser || command -v google-chrome) || { echo "Chrome/Chromium が見つかりません。CHROME=/path/to/chrome を指定してください" >&2; exit 1; }
fi
for f in "$@"; do
  w=$(grep -o 'width="[0-9]*"' "$f" | head -1 | grep -o '[0-9]*')
  h=$(grep -o 'height="[0-9]*"' "$f" | head -1 | grep -o '[0-9]*')
  "$CH" --headless=new --disable-gpu --no-sandbox --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=$w,$h --screenshot="$PWD/${f%.svg}.png" "file://$PWD/$f" >/dev/null 2>&1
done
