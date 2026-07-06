# ── Stage 1: Build frontend ──────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /build

# Copy dependency manifests first (better layer caching)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source and build
COPY frontend/ .
RUN npm run build

# ── Stage 2: nginx runtime ───────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Install envsubst (provided by gettext) for config templating
# Install htpasswd (provided by apache2-utils) for Basic Auth
RUN apk add --no-cache gettext apache2-utils

# Copy built frontend from builder stage
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy nginx config template
COPY nginx/astrology.conf /etc/nginx/templates/astrology.conf.template

# Copy docker-entrypoint
COPY nginx/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Environment variables with defaults
ENV NGINX_SERVER_NAME=localhost
ENV BASIC_AUTH_USER=bix
ENV BASIC_AUTH_PASS=changeme

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
