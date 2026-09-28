FROM node:22-slim AS base
WORKDIR /app
COPY package.json package-lock.json ./

# --- Local development target (docker-compose.yml uses this, with source bind-mounted) ---
FROM base AS dev
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

# --- Production build target ---
FROM base AS build
RUN npm ci
COPY . .
RUN npm run build

# --- Production image: Caddy serves the build, proxies /api, and terminates TLS (Section 11) ---
FROM caddy:2-alpine AS production
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80 443
