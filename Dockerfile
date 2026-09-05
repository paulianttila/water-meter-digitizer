FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN \
  apt-get update -y && \
  apt-get install -qq --no-install-recommends libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1 && \
  rm -rf /var/lib/apt/lists/*

EXPOSE 3000

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY requirements.txt ./

RUN uv pip install --system --no-cache -r requirements.txt

RUN mkdir -p /log /config

WORKDIR /config
COPY ./config/ ./

WORKDIR /app
COPY ./src/ ./

CMD ["python", "./main.py"]
