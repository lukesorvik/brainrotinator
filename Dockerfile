# Use an official Python runtime as a base image
FROM python:3.12.2

# Set the working directory in the container
WORKDIR /app

# System deps: git for pip-from-git, ffmpeg (with libass for subtitle burn-in), fonts, debugging tools.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git bash nano wget ca-certificates \
        ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Verify libass is built into ffmpeg (subtitle burn-in needs it).
RUN ffmpeg -hide_banner -filters 2>/dev/null | grep -q "ass " || (echo "ffmpeg lacks ass filter" && exit 1)

# Upgrade pip and pin setuptools < 71 (newer versions break legacy setup.py
# packages like openai-whisper that import pkg_resources at module top-level).
RUN pip install --upgrade pip "setuptools<71" wheel

# Copy the current directory contents into the container at /app
COPY . /app

# Install Python deps. --no-build-isolation lets setup.py-based packages reuse
# the setuptools we just pinned, instead of pip pulling latest into an isolated env.
RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt

# Geckodriver for the (optional) selenium uploaders.
RUN wget -q https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz \
    && tar -xzf geckodriver-v0.32.0-linux64.tar.gz \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.32.0-linux64.tar.gz \
    && geckodriver --version

# Firefox for selenium uploaders (optional). firefox-esr ships in Debian stable
# so we don't need to add the `unstable` repo (which causes openssl conflicts).
RUN apt-get update \
    && apt-get install -y --no-install-recommends firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Gradio default port
EXPOSE 7860

# Default: launch the Gradio UI. Override with `docker run ... bash` for the CLI.
CMD ["python", "app.py"]
