FROM python:3.11-slim

WORKDIR /app

COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/README.md /app/README.md
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e .

COPY backend /app

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
