FROM python:3.12.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SIGNAL_SEARCH_DB_PATH=/data/signal-search.db \
    SIGNAL_SEARCH_CACHE_SIZE=128

WORKDIR /app

COPY pyproject.toml README.md requirements.lock ./
COPY src ./src

RUN python -m pip install --no-cache-dir --requirement requirements.lock \
    && python -m pip install --no-cache-dir --no-deps . \
    && mkdir -p /data \
    && chown 10001:10001 /data

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["uvicorn", "signal_search.api:app", "--host", "0.0.0.0", "--port", "8000"]
