FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY . /app/

RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install .

# Run the bot
CMD [".venv/bin/tgmusicbot"]
