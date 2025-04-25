FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential \
    curl \
    libx11-dev \
    libasound2-dev \
    libpulse-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.6.14

RUN git clone https://github.com/pytgcalls/ntgcalls.git --recursive
WORKDIR /app/ntgcalls
RUN python3 setup.py build_lib

WORKDIR /app

COPY . /app/

RUN uv pip install -e . --system

ENV PYTHONPATH="/app/ntgcalls:$PYTHONPATH"

CMD ["tgmusic"]
