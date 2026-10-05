FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY code/ code/
COPY data/photo_edit_alarm.jpg data/
RUN useradd --create-home --uid 1000 app \
    && mkdir -p data/icals db \
    && chown -R app:app /app
USER app
VOLUME ["/app/data/icals", "/app/db"]

# пути к данным в коде — относительно папки code/ (../data, ../db)
WORKDIR /app/code
CMD ["python", "bot.py"]
