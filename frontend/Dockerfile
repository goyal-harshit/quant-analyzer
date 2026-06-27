FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Production image, serve static export
FROM nginx:alpine AS runner

# Copy static export from builder
COPY --from=builder /app/out /usr/share/nginx/html

# Create minimal nginx config for SPA
RUN rm /etc/nginx/conf.d/default.conf && \
    echo 'server { listen 3000; location / { root /usr/share/nginx/html; try_files $uri /index.html; } }' > /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
