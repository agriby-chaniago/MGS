FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
# `npm ci` (not used here): Tailwind v4's oxide/lightningcss native engine
# has optional per-platform packages (e.g. @emnapi/*, WASM fallback) that a
# lockfile generated on one host OS/libc doesn't fully enumerate for others
# — `npm ci` then refuses as "out of sync" inside this Alpine (musl)
# container even though the lockfile is otherwise correct. `npm install`
# resolves fresh against the container's actual platform instead.
RUN npm install

COPY . .

# Vite inlines import.meta.env.VITE_* at build time — this MUST be a build
# arg, not a docker-compose `environment:` var, or the static bundle ships
# pointing at the wrong (or empty) API URL. See docker-compose.yml comment.
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
