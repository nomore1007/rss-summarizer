FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rss_summarizer.py .

VOLUME ["/data"]

ENTRYPOINT ["python", "rss_summarizer.py"]
