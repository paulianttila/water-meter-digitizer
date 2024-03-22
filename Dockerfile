FROM python:3.7

EXPOSE 3000

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY ./code/ ./
RUN pip install --no-cache-dir ./wheels/tflite_runtime-2.1.0.post1-cp37-cp37m-linux_x86_64.whl && \
	pip install --no-cache-dir -r requirements.txt && \
	rm -r ./wheels

CMD ["python", "./wasseruhr.py"]
