FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install the package with the API + vector-db extras.
COPY pyproject.toml README.md ./
COPY tastebench ./tastebench
RUN pip install --upgrade pip && pip install ".[tastegraph,web,vectordb]"

# Run as a non-root user.
RUN useradd --create-home --uid 10001 tastegraph
USER tastegraph

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request,sys; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/health'); " || exit 1

# server.py builds `app` from environment variables (see its docstring).
CMD ["sh", "-c", "uvicorn tastebench.tastegraph.server:app --host 0.0.0.0 --port ${PORT}"]
