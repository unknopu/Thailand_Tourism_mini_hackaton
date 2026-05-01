#!/bin/sh
# Inject runtime environment variables into a JS config file
cat > /usr/share/nginx/html/env-config.js <<EOF
window._env_ = {
  API_BASE: "${API_BASE:-http://localhost:8000/api/v1}"
};
EOF
exec nginx -g 'daemon off;'
