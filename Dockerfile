# Playwright's official image ships Chromium + every system library it needs,
# pre-installed and version-matched. This is what makes "Playwright in Docker"
# work without hunting missing libs. Tag matches playwright==1.60.0 in requirements.
FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

WORKDIR /app

# Install Python deps first so this layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The base image already includes the Chromium browser binary, so no
# `playwright install` step is needed here.

# Copy only the backend code (see .dockerignore for what's excluded).
COPY agent.py tools.py summary.py api.py ./

# AgentBox assigns a port at runtime via $PORT; default to 8000 locally.
ENV PORT=8000
# Default model — override in AgentBox env if your account uses a different one.
ENV GMI_MODEL=nvidia/nemotron-3-ultra-550b-a55b

EXPOSE 8000

# Shell form so ${PORT} expands. Binds 0.0.0.0 so the container is reachable.
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
