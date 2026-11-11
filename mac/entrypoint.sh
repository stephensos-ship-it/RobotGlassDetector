#!/usr/bin/env bash

# Start a virtual display, serve it at http://localhost:6080/vnc.html, then run the command.
# x11vnc's password auth uses only the first 8 characters; mac/tiago.sh up makes 8.
set -o errexit
set -o nounset
set -o pipefail

rm -f /tmp/.X1-lock /tmp/.X11-unix/X1
Xvfb :1 -screen 0 1920x1080x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
for _ in $(seq 1 50); do
  [[ -S /tmp/.X11-unix/X1 ]] && break
  sleep 0.1
done

bash /ws/mac/desktop.sh
openbox >/tmp/openbox.log 2>&1 &
# Password-protect the desktop: websockify does not check origins, so any web page open
# in the browser could otherwise connect to it. mac/tiago.sh up sets VNC_PASSWORD.
x11vnc -storepasswd "${VNC_PASSWORD:?Set VNC_PASSWORD; mac/tiago.sh up does this}" \
  /tmp/vncpasswd >/dev/null 2>&1
x11vnc -display :1 -forever -shared -localhost -rfbauth /tmp/vncpasswd -quiet \
  -rfbport 5900 >/tmp/x11vnc.log 2>&1 &
websockify --web /usr/share/novnc 6080 localhost:5900 >/tmp/novnc.log 2>&1 &

exec "$@"
