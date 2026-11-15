# Bol-Khata — one container: React app + FastAPI API on the same origin.
# Build:  docker build -t bol-khata .
# Run:    docker run -p 8000:8000 --env-file backend/.env bol-khata

FROM node:20-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/ ./
COPY --from=web /app/frontend/dist /app/frontend/dist
RUN useradd --create-home app && mkdir -p data && chown -R app /app
USER app
ENV PORT=8000 SEED_ON_START=1
EXPOSE 8000
CMD ["python", "-m", "scripts.start"]
