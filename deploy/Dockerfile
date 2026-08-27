FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY scripts ./scripts
RUN pip install --no-cache-dir -e .

RUN mkdir -p /app/data
VOLUME /app/data

# paper trading by default; live requires -e MEMEBOT_LIVE=YES and a key
ENV PYTHONUNBUFFERED=1
CMD ["memebot", "paper"]
