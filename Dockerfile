FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app /app
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "600", "main:app"]