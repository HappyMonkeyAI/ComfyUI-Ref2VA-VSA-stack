FROM python:3.12-slim

WORKDIR /app

COPY requirements-pipe.txt /app/requirements-pipe.txt
RUN pip install --no-cache-dir -r /app/requirements-pipe.txt

COPY pipe /app/pipe
COPY h3_mcp /app/h3_mcp
COPY scripts /app/scripts
COPY workflows /app/workflows

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "h3_mcp.server"]
