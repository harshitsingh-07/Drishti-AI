# ------------------------------
# Stage 1: Build React frontend
# ------------------------------
FROM node:22-slim AS frontend-builder

WORKDIR /frontend

COPY AI-EYE-Frontend/package*.json ./

RUN npm ci

COPY AI-EYE-Frontend/ ./

ENV VITE_API_BASE_URL=/api

RUN npm run build


# ------------------------------
# Stage 2: Flask + YOLO backend
# ------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-cloud.txt ./requirements-cloud.txt

RUN pip install --upgrade pip && \
    pip install -r requirements-cloud.txt

COPY backend/ ./backend/
COPY distance_model.pth ./distance_model.pth
COPY yolov8n.pt ./yolov8n.pt

COPY --from=frontend-builder /frontend/dist ./frontend-dist

EXPOSE 7860

CMD ["gunicorn", "--chdir", "backend", "app:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "2", "--timeout", "120"]
