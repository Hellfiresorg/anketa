FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libcairo-gobject2 \
    fonts-liberation \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

RUN mkdir -p /var/voice-survey/audio/tmp

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
