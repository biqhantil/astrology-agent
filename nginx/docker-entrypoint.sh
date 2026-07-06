#!/bin/sh
set -e

# ── Generate .htpasswd from environment variables ───────────────────────────
# BASIC_AUTH_USER and BASIC_AUTH_PASS are required. If either is missing,
# a warning is printed and a default user "bix" with password "changeme" is used.

if [ -n "$BASIC_AUTH_USER" ] && [ -n "$BASIC_AUTH_PASS" ]; then
    htpasswd -bc /etc/nginx/.htpasswd "$BASIC_AUTH_USER" "$BASIC_AUTH_PASS"
else
    echo "WARNING: BASIC_AUTH_USER or BASIC_AUTH_PASS not set. Using default: bix / changeme"
    htpasswd -bc /etc/nginx/.htpasswd bix changeme
fi

# ── Substitute environment variables in nginx config template ───────────────
envsubst '${NGINX_SERVER_NAME}' < /etc/nginx/templates/astrology.conf.template > /etc/nginx/conf.d/default.conf

# ── Start nginx ────────────────────────────────────────────────────────────
exec nginx -g 'daemon off;'
