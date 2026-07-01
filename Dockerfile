FROM python:3.11-slim

WORKDIR /app

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY gateway.py reminders.py scheduler.py pushover.py .

# Volume para persistir o banco de lembretes entre deploys (configure um
# Railway Volume montado em /data e defina REMINDER_DB_PATH=/data/reminders.db)
VOLUME ["/data"]

EXPOSE 8000

ENV PORT=8000
ENV HOST=0.0.0.0

CMD uvicorn gateway:app --host $HOST --port $PORT --proxy-headers --forwarded-allow-ips='*'
