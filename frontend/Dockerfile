# ---- Build stage: compile the React app with Node ----
FROM node:25-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---- Runtime stage: serve static files with a non-root Nginx ----
# nginx-unprivileged runs as uid 101 and listens on 8080 (ports < 1024 need root).
FROM nginxinc/nginx-unprivileged:1.30-alpine
# Pull the latest Alpine security fixes at build time (Trivy flagged packages in older base images).
USER root
RUN apk upgrade --no-cache
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
USER 101
EXPOSE 8080
# Docker/Compose health status (Kubernetes uses its own probes). busybox wget ships with Alpine.
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3   CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"]
