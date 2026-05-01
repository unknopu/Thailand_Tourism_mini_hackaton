FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source (overridden by the volume mount in docker-compose for development)
COPY . .

# RUN python embed_places.py

# # start server
# CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
