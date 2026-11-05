# Hosted demo: one container serving the API (/api) and the built React app.
# The demo database is copied fresh from deploy/demo.db on every start, so the public demo always begins clean.

FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npx vite build

FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
# numpy/pillow pins have no Linux wheels for Python 3.14; use the nearest releases that do (same APIs used here).
RUN sed -E 's/^numpy==.*/numpy>=2.3.4,<3/; s/^pillow==.*/pillow>=12.0,<13/' backend/requirements.txt > /tmp/req.txt \
    && pip install --no-cache-dir -r /tmp/req.txt
COPY backend/ backend/
COPY app_data/inbox/ app_data/inbox/
COPY app_data/seed/ app_data/seed/
COPY deploy/demo.db deploy/demo.db
COPY --from=web /web/dist frontend/dist
ENV PYTHONPATH=/srv/backend APP_DATA_ROOT=/srv/app_data PORT=10000
EXPOSE 10000
CMD ["sh", "-c", "mkdir -p app_data/storage && cp deploy/demo.db app_data/app.db && exec uvicorn app.serve:create_public_app --factory --host 0.0.0.0 --port ${PORT}"]
