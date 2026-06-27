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

# nginx config for the static export. try_files resolves clean URLs to the
# matching .html file (e.g. /login -> /login.html) so direct hits and refreshes
# work, falling back to index.html only when nothing matches.
RUN rm /etc/nginx/conf.d/default.conf && \
    echo 'server { listen 3000; root /usr/share/nginx/html; location / { try_files $uri $uri.html $uri/ /index.html; } }' > /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
