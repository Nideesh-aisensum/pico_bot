#!/bin/bash

# Substitute environment variables into config.json
if [ -n "$NVIDIA_API_KEY" ]; then
  sed -i "s|YOUR_NEW_NVIDIA_API_KEY|$NVIDIA_API_KEY|g" /root/.picoclaw/config.json
fi
if [ -n "$TELEGRAM_TOKEN" ]; then
  sed -i "s|YOUR_TELEGRAM_BOT_TOKEN|$TELEGRAM_TOKEN|g" /root/.picoclaw/config.json
fi
if [ -n "$ALLOWED_USER_ID" ]; then
  sed -i "s|\"YOUR_NUMERIC_TELEGRAM_USER_ID\"|$ALLOWED_USER_ID|g" /root/.picoclaw/config.json
fi

# Start a simple HTTP health server on PORT (for Render keep-alive)
PORT=${PORT:-8080}

# Tiny health check server using bash + netcat
health_server() {
  while true; do
    echo -e "HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK" | nc -l -p $PORT -q 1 2>/dev/null || true
  done
}

# Start health server in background
health_server &
echo "✅ Health server started on port $PORT"

# Start PicoClaw gateway
echo "🦐 Starting PicoClaw with NVIDIA + Kimi K2.5..."
./picoclaw gateway
