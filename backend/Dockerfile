FROM python:3.11-slim-bookworm

# Instead of downloading ffmpeg-linux.zip when installing playwright, we put it in the tmp folder
COPY ffmpeg-linux.zip /tmp/ffmpeg-linux.zip
COPY chromium-linux.zip.part.aa /tmp/chromium-linux.zip.part.aa
COPY chromium-linux.zip.part.ab /tmp/chromium-linux.zip.part.ab
RUN cat /tmp/chromium-linux.zip.part.* > /tmp/chromium-linux.zip

LABEL com.danswer.maintainer="founders@onyx.app"
LABEL com.danswer.description="This image is the web/frontend container of Onyx which \
contains code for both the Community and Enterprise editions of Onyx. If you do not \
have a contract or agreement with DanswerAI, you are not permitted to use the Enterprise \
Edition features outside of personal development or testing purposes. Please reach out to \
founders@onyx.app for more information. Please visit https://github.com/onyx-dot-app/onyx"

# Build argument for Craft support (disabled by default)
# Use --build-arg ENABLE_CRAFT=true to include Node.js and opencode CLI
ARG ENABLE_CRAFT=false

# DO_NOT_TRACK is used to disable telemetry for Unstructured
ENV DANSWER_RUNNING_IN_DOCKER="true" \
    DO_NOT_TRACK="true" \
    PLAYWRIGHT_BROWSERS_PATH="/app/.cache/ms-playwright" \
    NLTK_DATA="/usr/share/nltk_data" \
    HF_HOME="/usr/share/huggingface" \
    TIKTOKEN_CACHE_DIR="/usr/share/tiktoken_cache"

# Create non-root user for security best practices
RUN groupadd -g 1001 onyx && \
    useradd -u 1001 -g onyx -m -s /bin/bash onyx && \
    mkdir -p /var/log/onyx && \
    chmod 755 /var/log/onyx && \
    chown onyx:onyx /var/log/onyx

COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/

# Install system dependencies
# cmake needed for psycopg (postgres)
# libpq-dev needed for psycopg (postgres)
# curl included just for users' convenience
# zip/unzip for Vespa and playwright cache setup
# ca-certificates for HTTPS
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        cmake \
        curl \
        zip \
        unzip \
        ca-certificates \
        libgnutls30 \
        libblkid1 \
        libmount1 \
        libsmartcols1 \
        libuuid1 \
        libxmlsec1-dev \
        pkg-config \
        procps \
        tini \
        libjemalloc2 \
        gcc \
        nano \
        vim \
        && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean


# Extract playwright browsers and cleanup archives in same layer
RUN mkdir -p ~/.cache/ms-playwright/ffmpeg-1009 \
 && unzip /tmp/ffmpeg-linux.zip -d ~/.cache/ms-playwright/ffmpeg-1009 \
 && touch ~/.cache/ms-playwright/ffmpeg-1009/INSTALLATION_COMPLETE \
 && mkdir -p ~/.cache/ms-playwright/chromium-1097 \
 && unzip /tmp/chromium-linux.zip -d ~/.cache/ms-playwright/chromium-1097 \
 && touch ~/.cache/ms-playwright/chromium-1097/INSTALLATION_COMPLETE \
 && rm -f /tmp/ffmpeg-linux.zip /tmp/chromium-linux.zip /tmp/chromium-linux.zip.part.*

# Conditionally install Node.js 20 for Craft (required for Next.js)
# Only installed when ENABLE_CRAFT=true
RUN if [ "$ENABLE_CRAFT" = "true" ]; then \
        echo "Installing Node.js 20 for Craft support..." && \
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
        apt-get install -y nodejs && \
        rm -rf /var/lib/apt/lists/*; \
    fi

# Conditionally install opencode CLI for Craft agent functionality
# Only installed when ENABLE_CRAFT=true
# TODO: download a specific, versioned release of the opencode CLI
RUN if [ "$ENABLE_CRAFT" = "true" ]; then \
        echo "Installing opencode CLI for Craft support..." && \
        curl -fsSL https://opencode.ai/install | bash; \
    fi
ENV PATH="/root/.opencode/bin:${PATH}"


# Install Python dependencies
# Remove py which is pulled in by retry, py is not needed and is a CVE
COPY ./requirements/default.txt /tmp/requirements.txt
COPY ./requirements/ee.txt /tmp/ee-requirements.txt
RUN uv pip install --system --no-cache-dir --upgrade \
        -r /tmp/requirements.txt \
        -r /tmp/ee-requirements.txt && \
    pip uninstall -y py && \
    playwright install chromium && \
    playwright install-deps chromium && \
    chown -R onyx:onyx /app && \
    ln -s /usr/local/bin/supervisord /usr/bin/supervisord && \
    # Cleanup for CVEs and size reduction
    # https://github.com/tornadoweb/tornado/issues/3107
    # xserver-common and xvfb included by playwright installation but not needed after
    # perl-base is part of the base Python Debian image but not needed for Onyx functionality
    # perl-base could only be removed with --allow-remove-essential
    apt-get update && \
    apt-get remove -y --allow-remove-essential --no-install-recommends \
        perl-base \
        xserver-common \
        xvfb \
        cmake \
        libldap-2.5-0 \
        libxmlsec1-dev \
        pkg-config \
        gcc && \
    # Install here to avoid some packages being cleaned up above
    apt-get install -y --no-install-recommends \
        libxmlsec1-openssl \
        # Install postgresql-client for easy manual tests
        postgresql-client && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf ~/.cache/uv /tmp/*.txt && \
    rm -f /usr/local/lib/python3.11/site-packages/tornado/test/test.key

# Pre-download all models/data in single layer and cleanup Python cache
# NLTK data for read-only filesystems, tokenizers, and tiktoken encodings
RUN python -c "import nltk; \
    nltk.download('stopwords', download_dir='/usr/share/nltk_data', quiet=True); \
    nltk.download('punkt_tab', download_dir='/usr/share/nltk_data', quiet=True);" && \
python -c "from tokenizers import Tokenizer; \
Tokenizer.from_pretrained('nomic-ai/nomic-embed-text-v1')" && \
python -c "import tiktoken; \
tiktoken.get_encoding('cl100k_base')" && \
chown -R onyx:onyx /usr/share/nltk_data /usr/share/huggingface /usr/share/tiktoken_cache && \
find /usr/local/lib/python3.11 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
find /usr/local/lib/python3.11 -type f -name '*.pyc' -delete 2>/dev/null || true && \
find /usr/local/lib/python3.11 -type f -name '*.pyo' -delete 2>/dev/null || true

# nltk.download('wordnet', quiet=True); introduce this back if lemmatization is needed

USER onyx

# Set up application files
WORKDIR /app

# Enterprise Version Files
COPY --chown=onyx:onyx ./ee /app/ee
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set up application files
COPY --chown=onyx:onyx ./onyx /app/onyx
COPY --chown=onyx:onyx ./shared_configs /app/shared_configs
COPY --chown=onyx:onyx ./alembic /app/alembic
COPY --chown=onyx:onyx ./alembic_tenants /app/alembic_tenants
COPY --chown=onyx:onyx ./alembic.ini /app/alembic.ini
COPY supervisord.conf /usr/etc/supervisord.conf
COPY --chown=onyx:onyx ./static /app/static
COPY --chown=onyx:onyx ./keys /app/keys

# Escape hatch scripts
COPY --chown=onyx:onyx ./scripts/debugging /app/scripts/debugging
COPY --chown=onyx:onyx ./scripts/force_delete_connector_by_id.py /app/scripts/force_delete_connector_by_id.py
COPY --chown=onyx:onyx ./scripts/supervisord_entrypoint.sh /app/scripts/supervisord_entrypoint.sh
COPY --chown=onyx:onyx ./scripts/setup_craft_templates.sh /app/scripts/setup_craft_templates.sh
COPY --chown=onyx:onyx ./scripts/reencrypt_secrets.py /app/scripts/reencrypt_secrets.py
RUN chmod +x /app/scripts/supervisord_entrypoint.sh /app/scripts/setup_craft_templates.sh

# Run Craft template setup at build time when ENABLE_CRAFT=true
# This pre-bakes demo data, Python venv, and npm dependencies into the image
RUN if [ "$ENABLE_CRAFT" = "true" ]; then \
        echo "Running Craft template setup at build time..." && \
        ENABLE_CRAFT=true /app/scripts/setup_craft_templates.sh; \
    fi

# Set Craft template paths to the in-image locations
# These match the paths where setup_craft_templates.sh creates the templates
ENV OUTPUTS_TEMPLATE_PATH=/app/onyx/server/features/build/sandbox/kubernetes/docker/templates/outputs
ENV VENV_TEMPLATE_PATH=/app/onyx/server/features/build/sandbox/kubernetes/docker/templates/venv

# Put logo in assets
COPY --chown=onyx:onyx ./assets /app/assets

ENV PYTHONPATH=/app

# Default ONYX_VERSION, typically overriden during builds by GitHub Actions.
ARG ONYX_VERSION=0.0.0-dev
ENV ONYX_VERSION=${ONYX_VERSION}

# Use jemalloc instead of glibc malloc to reduce memory fragmentation
# in long-running Python processes (API server, Celery workers).
# The soname is architecture-independent; the dynamic linker resolves
# the correct path from standard library directories.
# Placed after all RUN steps so build-time processes are unaffected.
ENV LD_PRELOAD=libjemalloc.so.2

# Default command which does nothing
# This container is used by api server and background which specify their own CMD
CMD ["tail", "-f", "/dev/null"]
