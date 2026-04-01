# syntax = docker/dockerfile:1.2
FROM python:3.14-slim

RUN apt-get update && apt-get install -y gcc python3-dev libssl-dev libmariadb-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY ./ .

# Expose the port Gunicorn will listen on
EXPOSE 8000

# Command to run Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]