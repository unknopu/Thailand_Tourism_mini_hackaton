FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source (overridden by the volume mount in docker-compose for development)
COPY . .

EXPOSE 1323

# --reload watches for file changes; works because docker-compose mounts the source as a volume
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "1323", "--reload"]
