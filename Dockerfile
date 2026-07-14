FROM python:3.12-slim

# Install Node.js 22
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Build frontend
WORKDIR /app/frontend
RUN npm ci && npm run build

WORKDIR /app
RUN chmod +x entrypoint.sh

EXPOSE 7860
ENTRYPOINT ["/app/entrypoint.sh"]
