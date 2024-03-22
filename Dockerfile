FROM python:3.7-slim

RUN \
  apt-get update -y && \
  apt-get install -qq libglib2.0-0 libsm6 libxext6 libxrender-dev && \
  rm -rf /var/lib/apt/lists/*

EXPOSE 3000

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ./code/ ./
RUN pip install --no-cache-dir ./wheels/tflite_runtime-2.1.0.post1-cp37-cp37m-linux_x86_64.whl && \
	pip install --no-cache-dir -r requirements.txt && \
	rm -r ./wheels

CMD ["python", "./watermeter.py"]
