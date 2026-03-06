# --- Build Stage ---
FROM node:20-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install project dependencies
COPY package*.json ./
RUN npm ci

# Copy code and build
COPY . .
RUN npm run build

# --- Servre Stage ---
FROM nginx:alpine

# Copy build artifacts to nginx public directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port (default nginx) 80
EXPOSE 80

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
