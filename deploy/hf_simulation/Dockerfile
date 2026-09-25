FROM python:3.10-slim-bullseye

# Prevent interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# 1. Install system runtime dependencies for X11, Xvfb, noVNC, and Qt6/PySide6
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    openbox \
    x11-utils \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    libdbus-1-3 \
    libxcb-xinerama0 \
    libxcb1 \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xrm0 \
    net-tools \
    procps \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Configure Hugging Face standard non-root user (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    DISPLAY=:99 \
    PYTHONUNBUFFERED=1 \
    QT_QPA_PLATFORM=xcb \
    LIBGL_ALWAYS_SOFTWARE=1 \
    QT_XCB_GL_INTEGRATION=none

WORKDIR /home/user/app

# 3. Install Python dependencies
COPY --chown=user:user requirements.txt /home/user/app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /home/user/app/requirements.txt

# 4. Copy application files and runtime configuration
COPY --chown=user:user . /home/user/app/

# Ensure entrypoint script is executable
RUN chmod +x /home/user/app/entrypoint.sh

# 5. Expose Hugging Face default application port
EXPOSE 7860

# 6. Launch orchestrator
CMD ["/home/user/app/entrypoint.sh"]
