FROM python:3.11-slim

RUN \
  apt-get update -y && \
  apt-get install -qq libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1 && \
  rm -rf /var/lib/apt/lists/*

EXPOSE 3000

ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt pip-tools && \
	rm -r requirements.txt

RUN mkdir -p /image_tmp
RUN mkdir -p /log

WORKDIR /config
COPY ./config/ ./

WORKDIR /app
COPY ./src/ ./

CMD ["python", "./meter.py"]
