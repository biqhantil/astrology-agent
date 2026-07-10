# Astrology Agent — Docker Containerization

## Objective
Containerize the astrology agent app so it runs via docker-compose on any VPS with zero manual setup.

## Reference Patterns

The repo at /home/bix/jarvis/content/repos/newsflow/ has proven Docker/nginx patterns:
- Dockerfile (Python 3.11-slim, non-root user, healthcheck)
- nginx/Dockerfile (nginx:1.27-alpine, envsubst templating)
- nginx/newsflow.conf (upstreams, proxy_pass, security headers)
- docker-compose.yml (full stack with services, volumes, healthchecks, depends_on)

## Architecture

Two services:
1. backend — FastAPI + uvicorn (Python 3.12-slim)
2. nginx — reverse proxy with Basic Auth + static frontend files

## Deliverables

Create these files in /opt/astrology-agent/:

### 1. backend/Dockerfile
- Base: python:3.12-slim
- Install: python deps from requirements.txt + aiosqlite httpx
- Copy backend/ source
- Create non-root user
- VOLUME /data (for SQLite persistence)
- ENV SQLITE_PATH=/data/astrology.db
- HEALTHCHECK: curl localhost:8000/v1/health
- CMD: uvicorn app.main:app --host 0.0.0.0 --port 8000

### 2. Dockerfile (frontend + nginx, at project root)
- Multi-stage:
  - Stage 1 (builder): node:20-alpine, npm install && npm run build
  - Stage 2 (runtime): nginx:1.27-alpine
  - Copy built frontend from stage 1 to nginx html dir
  - Copy nginx config template
  - Copy docker-entrypoint.sh
  - ENV for NGINX_SERVER_NAME (optional), BASIC_AUTH_USER, BASIC_AUTH_PASS
- EXPOSE 80
- ENTRYPOINT + CMD for nginx

### 3. nginx/astrology.conf
- Single server block on port 80
- auth_basic with htpasswd generated at runtime from env vars
- location / → serve frontend static files
- location /v1/ → proxy_pass http://backend:8000 (no auth_basic)
- location /v1/stream → proxy_pass with proxy_buffering off
- Standard security headers, gzip, logging

### 4. nginx/docker-entrypoint.sh
- Generate .htpasswd from BASIC_AUTH_USER / BASIC_AUTH_PASS env vars
- Substitute env vars in nginx config template
- exec nginx

### 5. nginx/Dockerfile (if separate, or merge into root Dockerfile)
If keeping separate: nginx:1.27-alpine, copy config template + entrypoint

### 6. docker-compose.yml (at project root)
```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file: .env
    environment:
      OPENCODE_API_KEY: ${OPENCODE_API_KEY}
    volumes:
      - astro_data:/data
    expose:
      - "8000"
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3

  nginx:
    build: ./nginx
    restart: unless-stopped
    ports:
      - "80:80"
    environment:
      NGINX_SERVER_NAME: ${NGINX_SERVER_NAME:-localhost}
      BASIC_AUTH_USER: ${BASIC_AUTH_USER:-bix}
      BASIC_AUTH_PASS: ${BASIC_AUTH_PASS:-changeme}
    depends_on:
      backend:
        condition: service_healthy

volumes:
  astro_data:
```

### 7. .env.example
```
OPENCODE_API_KEY=sk-your-key-here
BASIC_AUTH_USER=bix
BASIC_AUTH_PASS=your-password
NGINX_SERVER_NAME=localhost
```

## Implementation Rules
1. Build one file at a time
2. After all files, build and test with: docker compose up --build -d
3. Test: curl http://localhost:80/v1/health should return ok
4. Test: curl -u bix:password http://localhost:80/ should return HTML
5. Test: create conversation via API and verify data persists after docker compose restart
6. If all passes, git add -A && git commit -m 'feat: docker containerization' && git push

Start now with backend/Dockerfile and work through in order.
