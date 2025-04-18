FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml requirements.txt* /app/

RUN uv pip install --no-cache -r requirements.txt --system

COPY . /app/

CMD ["python3", "-m", "src"]
