# Use Python 3.12 Alpine image as base (minimal Linux)
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Install system dependencies
# - git: for cloning repositories
# - wget, bash: for downloading uv installer
# - chromium: lightweight browser for Selenium
# - chromium-chromedriver: ChromeDriver for Selenium automation
RUN apk add --no-cache \
    git \
    wget \
    bash \
    chromium \
    chromium-chromedriver

# Install uv package manager
RUN wget -qO- https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Set Chromium path for Selenium
ENV CHROME_BIN=/usr/bin/chromium-browser \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Copy project files
COPY pyproject.toml ./
COPY crawl-jobs.txt ./
COPY git-gist-crawler.py ./

# Install Python dependencies globally using uv
# Use --no-cache to reduce image size
RUN uv pip install --system --no-cache selenium>=4.15.0

# Create data directory
RUN mkdir -p /app/data

# Set environment variable to disable Chrome sandbox (required for Docker)
ENV CHROME_NO_SANDBOX=1

# Run the crawler
CMD ["python", "git-gist-crawler.py"]
