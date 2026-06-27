# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# VITE_API_URL is baked in at build time so the React bundle can reach the backend.
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# Runtime stage — nginx serves the built files.
# PORT is injected by Railway at runtime; nginx.conf uses envsubst to apply it.
FROM nginx:alpine

RUN apk add --no-cache bash

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf.template

ENV PORT=3000

EXPOSE ${PORT}

# Substitute $PORT and $API_URL into nginx config at container start
CMD ["/bin/sh", "-c", "export PORT=${PORT:-3000} API_URL=${API_URL:-} && envsubst '$PORT $API_URL' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
