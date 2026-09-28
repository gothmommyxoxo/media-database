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

FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
