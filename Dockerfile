FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    WVAB_OFFLINE=1 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        espeak-ng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.txt

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin wvab
COPY --chown=wvab:wvab . /app
RUN mkdir -p /app/logs /tmp/Ultralytics \
    && chown -R wvab:wvab /app/logs /tmp/Ultralytics

USER wvab

CMD ["python", "udp_streaming.py", "server", "--config", "wvab_config.sample.json"]
