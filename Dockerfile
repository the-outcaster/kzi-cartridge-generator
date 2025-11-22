# Use Ubuntu 22.04 (Jammy) - Good balance of modern Python 3.10 and older GLIBC 2.35
FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    make \
    file \
    gcc \
    fuse \
    genisoimage \
    wodim \
    python3 \
    python3-dev \
    python3-pip \
    python3-tk \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# We install PyInstaller, plus the libraries mentioned in your README/Code
RUN pip3 install pyinstaller Pillow certifi requests

# Install AppImageTool
RUN wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -O /usr/local/bin/appimagetool && \
    chmod +x /usr/local/bin/appimagetool

# Set working directory to the mounted volume
WORKDIR /app

# Environment variables to help the build
ENV APPIMAGE_EXTRACT_AND_RUN=1
ENV ARCH=x86_64

# 1. Run the build script
# 2. Move the result from the container's internal folder (/root/Applications) to the mounted folder (/app)
CMD ./build.sh && mv /root/Applications/*.AppImage /app/
