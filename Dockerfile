FROM debian:bookworm-slim

# Install curl and netcat
RUN apt-get update && apt-get install -y curl netcat-traditional && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Download PicoClaw binary (ARM64 or AMD64 based on build platform)
ARG TARGETARCH
RUN if [ "$TARGETARCH" = "arm64" ]; then \
      curl -L https://github.com/sipeed/picoclaw/releases/latest/download/picoclaw-linux-arm64 -o picoclaw; \
    else \
      curl -L https://github.com/sipeed/picoclaw/releases/latest/download/picoclaw-linux-amd64 -o picoclaw; \
    fi && chmod +x picoclaw

# Copy config
COPY config.json /root/.picoclaw/config.json

# Create workspace directory
RUN mkdir -p /root/.picoclaw/workspace

# Copy start script
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 8080

CMD ["./start.sh"]
