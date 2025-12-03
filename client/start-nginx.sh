#!/bin/sh
set -e
# Use PORT environment variable or default to 8080
PORT=${PORT:-8080}
echo "Starting nginx on port $PORT..."
# Create nginx config with correct port
cat > /etc/nginx/conf.d/default.conf <<EOF
server {
  listen ${PORT};
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

  # Gzip compression
  gzip on;
  gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

  # Single Page App fallback
  location / {
    try_files \$uri /index.html;
  }
}
EOF
# Start nginx
nginx -g "daemon off;"
