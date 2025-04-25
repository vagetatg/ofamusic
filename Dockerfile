FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libx11-dev \
    libasound2-dev \
    libpulse-dev \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "setuptools>=78.1.0" uv==0.6.16

WORKDIR /app
RUN git clone https://github.com/pytgcalls/ntgcalls.git --recursive
WORKDIR /app/ntgcalls
RUN python3 setup.py build_lib && \
    uv pip install . --system --no-deps

WORKDIR /app
COPY . /app/

RUN uv pip install -e . --system

CMD ["tgmusic"]
