FROM python:3.14-slim

WORKDIR /app

COPY ./ .
RUN pip install --no-cache-dir -r requirements.txt


# Expose the port Gunicorn will listen on
EXPOSE 8000

# Command to run Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]