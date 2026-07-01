FROM python:3.11-slim

WORKDIR /app

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY gateway.py reminders.py scheduler.py pushover.py .

EXPOSE 8000

ENV PORT=8000
ENV HOST=0.0.0.0

CMD uvicorn gateway:app --host $HOST --port $PORT --proxy-headers --forwarded-allow-ips='*'
