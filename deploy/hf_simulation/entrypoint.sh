#!/usr/bin/env bash
set -e

echo "[HORIZON HF Space] Initializing Virtual Desktop Environment..."

# Display Configuration
export DISPLAY=:99
export SCREEN_WIDTH=1920
export SCREEN_HEIGHT=1080
export SCREEN_DEPTH=24
export QT_QPA_PLATFORM=xcb
export LIBGL_ALWAYS_SOFTWARE=1
export QT_XCB_GL_INTEGRATION=none

# 1. Start Xvfb virtual framebuffer
echo "[HORIZON HF Space] Launching Xvfb display ${DISPLAY} (${SCREEN_WIDTH}x${SCREEN_HEIGHT}x${SCREEN_DEPTH})..."
Xvfb ${DISPLAY} -screen 0 ${SCREEN_WIDTH}x${SCREEN_HEIGHT}x${SCREEN_DEPTH} -nolisten tcp &
XVFB_PID=$!

# Wait for Xvfb to be ready
sleep 1

# 2. Start Openbox window manager
echo "[HORIZON HF Space] Starting Openbox window manager..."
if [ -f /home/user/app/openbox_rc.xml ]; then
    openbox --config-file /home/user/app/openbox_rc.xml &
else
    openbox &
fi

# 3. Start x11vnc server
echo "[HORIZON HF Space] Starting x11vnc server on port 5900..."
x11vnc -display ${DISPLAY} -forever -shared -rfbport 5900 -nopw -quiet -bg

# 4. Prepare noVNC index page (ensure autoconnect and scale by default)
NOVNC_DIR="/usr/share/novnc"
if [ -d "$NOVNC_DIR" ]; then
    # If index.html is missing or a placeholder, link vnc.html with parameters
    if [ -f "$NOVNC_DIR/vnc.html" ] && [ ! -f "$NOVNC_DIR/index.html" ]; then
        cp "$NOVNC_DIR/vnc.html" "$NOVNC_DIR/index.html"
    fi
fi

# 5. Start websockify bridge on port 7860 (Hugging Face default)
echo "[HORIZON HF Space] Starting websockify bridge on port 7860..."
websockify --web="$NOVNC_DIR" 7860 localhost:5900 &
WEBSOCKIFY_PID=$!

# 6. Launch HORIZON PySide6 5-Screen Simulation Suite
echo "[HORIZON HF Space] Launching Project HORIZON PySide6 simulation suite..."
cd /home/user/app

# Launch PySide6 main GUI in background so entrypoint can monitor
python main.py --gui &
PYTHON_PID=$!

echo "[HORIZON HF Space] System fully online on port 7860. Ready for browser connections."

# Graceful termination trap
trap "kill -TERM $PYTHON_PID $WEBSOCKIFY_PID $XVFB_PID 2>/dev/null || true; exit 0" SIGINT SIGTERM

# Keep container alive while monitoring python process
wait $PYTHON_PID
